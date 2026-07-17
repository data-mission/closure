"""E8 generation driver — concurrent, rate-limit-bound, resumable, atomic.

Feeds the scoring queue: for each (probe task, arm) it generates one Arm-B row via the FROZEN
generation path (generate_row over make_provider()), and appends it to the generation LOG
(append-only JSONL, the same shape the scorer reads). Concurrency without touching the frozen
request: the frozen provider callable is SYNC (providers.make_provider, reads ANTHROPIC_API_KEY
at call time, model-identity + schema guards in generate_row) — we run N of them in a bounded
ThreadPoolExecutor. Generation is network-bound, so threads give real concurrency; the exact
frozen request construction and guards are reused verbatim (no re-implementation of the API call).

Rate limiting: a token-bucket caps submissions/sec so we ride the API rate limit without tripping
it; SDK/transport errors and 429s are retried with capped exponential backoff, then logged as an
error row (never crash the run — matches run_arms.py's ProviderError handling).

API KEY: read from env inside the frozen provider on each call; NEVER hardcoded, NEVER logged,
NEVER written to any artifact. This driver does not read or print the key at all.

DRY-RUN: --dry-run replaces the provider with a deterministic FAKE generator (no network, no key)
so the manager can verify the full plumbing (queue → scorer → oracle) end-to-end at zero spend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
import sys  # noqa: E402
sys.path.insert(0, str(DRIVER))
from common import append_jsonl, load_jsonl  # noqa: E402


# --------------------------------------------------------------------------- rate limiter
class TokenBucket:
    """Simple thread-safe token bucket: capacity tokens, refilled rate/sec."""
    def __init__(self, rate: float, capacity: float | None = None):
        self.rate = rate
        self.capacity = capacity if capacity is not None else max(1.0, rate)
        self.tokens = self.capacity
        self.ts = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.ts) * self.rate)
                self.ts = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait = (1.0 - self.tokens) / self.rate
            time.sleep(min(wait, 1.0))


# --------------------------------------------------------------------------- prompt building
# Prompt construction (per-axis correction/assumption state + fail-loud instruction) lives in the
# shared axis_prompt module so the generation driver AND the filter build prompts identically.
from axis_prompt import build_prompt  # noqa: E402,F401  (re-exported for callers/tests)


# --------------------------------------------------------------------------- fake provider (dry-run)
def make_fake_provider(model_pin: str):
    """Deterministic fake: emits a schema-valid Output echoing the prompt, reports the pinned
    model so the identity guard passes. No network, no key. For end-to-end plumbing verification."""
    class _Resp:
        def __init__(self, output, model):
            self.output = output
            self.model = model

    def generate(prompt: str):
        h = hashlib.sha256(prompt.encode()).hexdigest()
        # 2 claims citing sources 0 and 1, plus a conclusion — schema-valid, deterministic.
        output = {
            "claims": [
                {"id": 0, "text": f"Synthetic claim A [{h[:8]}]", "source_ids": [0]},
                {"id": 1, "text": f"Synthetic claim B [{h[8:16]}]", "source_ids": [1]},
            ],
            "conclusion": f"Synthetic conclusion [{h[16:24]}].",
        }
        return _Resp(output, model_pin)
    return generate


# --------------------------------------------------------------------------- one generation
def generate_one(provider, task: dict, arm: str, prompt: str, config_hash: str,
                 max_retries: int, backoff_base: float) -> dict:
    """Frozen generate_row with retry on transient ProviderError. Returns a LOG row (ok or error)."""
    from closure_harness.generate import generate_row, ModelIdentityError
    from closure_harness.providers import ProviderError

    prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
    attempt = 0
    while True:
        try:
            row = generate_row(provider, prompt)  # FROZEN: identity guard + schema validation
            return {
                "task_id": task["task_id"], "arm": arm, "prompt_sha256": prompt_sha,
                "output": {"claims": [{"id": c.id, "text": c.text,
                                       "source_ids": list(c.source_ids)} for c in row.output.claims],
                           "conclusion": row.output.conclusion},
                "reported_model": row.reported_model, "config_hash": config_hash,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        except ModelIdentityError:
            raise  # a spoofed/misrouted model HALTS — never retried, never logged as a soft error
        except ProviderError as e:
            attempt += 1
            if attempt > max_retries:
                return {"task_id": task["task_id"], "arm": arm, "error": str(e)[:300],
                        "config_hash": config_hash,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            time.sleep(backoff_base * (2 ** (attempt - 1)))


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 async generation driver (rate-limit bound)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--arms", default="B")
    ap.add_argument("--template", type=Path, required=True,
                    help="prompt template file with {documents} and {question}")
    ap.add_argument("--arm-b-instruction", type=Path, required=True)
    ap.add_argument("--concurrency", type=int, default=4, help="runs on E-cores; network-bound")
    ap.add_argument("--rate", type=float, default=2.0, help="submissions/sec (ride the rate limit)")
    ap.add_argument("--max-retries", type=int, default=5)
    ap.add_argument("--backoff-base", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true", help="fake generator, no network, no key")
    ap.add_argument("--allow-unpinned-instruction", action="store_true",
                    help="skip the ARM-B hash pin (local template tests ONLY, never registered)")
    args = ap.parse_args()

    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    template = args.template.read_text()

    # STARTUP ASSERTION (registration-critical): the frozen ARM-B instruction is pinned by content
    # hash in PHASE0 §5. Verify the FILE bytes hash to the pin at load time so a wrong/edited
    # instruction can NEVER enter a registered run. Cheap, permanent, fail-loud.
    ARMB_PINNED_SHA256 = "f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c"
    armb_bytes = args.arm_b_instruction.read_bytes()
    armb_sha = hashlib.sha256(armb_bytes).hexdigest()
    if armb_sha != ARMB_PINNED_SHA256 and not args.allow_unpinned_instruction:
        raise SystemExit(
            f"ARM-B instruction hash mismatch: file {args.arm_b_instruction} sha256={armb_sha}, "
            f"pin={ARMB_PINNED_SHA256}. Refusing to generate under an unpinned instruction "
            "(would void the registered run). Pass --allow-unpinned-instruction only for local "
            "template experiments, never for a registered run."
        )
    arm_b = " ".join(l[2:].strip() for l in armb_bytes.decode().splitlines()
                     if l.startswith("> "))
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]

    # resume: skip (task, arm) already banked clean
    done = set()
    for r in load_jsonl(args.gen_log):
        if r.get("config_hash") == CH and not r.get("error"):
            done.add((r["task_id"], r["arm"]))
    todo = [(t, a) for t in tasks for a in arms if (t["task_id"], a) not in done]
    print(f"[gen] {len(todo)} generations to do ({len(done)} banked), "
          f"dry_run={args.dry_run}, concurrency={args.concurrency}, rate={args.rate}/s", flush=True)

    if args.dry_run:
        provider = make_fake_provider(CONFIG.generation.model_pin)
    else:
        from closure_harness.providers import make_provider
        provider = make_provider()  # reads ANTHROPIC_API_KEY at call time, never logged

    bucket = TokenBucket(args.rate)
    log_lock = threading.Lock()

    def worker(item):
        task, arm = item
        prompt = build_prompt(task, arm, arm_b, template)
        bucket.acquire()
        row = generate_one(provider, task, arm, prompt, CH,
                           args.max_retries, args.backoff_base)
        with log_lock:  # serialize appends (append is atomic but keep ordering clean)
            append_jsonl(args.gen_log, row)
        return (task["task_id"], arm, "error" in row)

    n_ok = n_err = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(worker, it) for it in todo]
        for fut in as_completed(futs):
            tid, arm, is_err = fut.result()
            n_err += is_err
            n_ok += (not is_err)
            if (n_ok + n_err) % 20 == 0:
                print(f"[gen]   {n_ok+n_err}/{len(todo)} (ok={n_ok} err={n_err})", flush=True)
    print(f"[gen] DONE ok={n_ok} err={n_err}", flush=True)


if __name__ == "__main__":
    main()
