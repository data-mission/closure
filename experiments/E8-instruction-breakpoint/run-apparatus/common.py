"""Shared plumbing for the E8 parallel corpus driver.

Atomic writes, provenance stamping, task-file locking, JSONL append. Everything that both the
scoring workers and the generation driver need, in one place, so the crash-safety and
provenance rules (task #17 SEV-7, SEV-3/SEV-4 rulings) are implemented ONCE and identically.

Design invariants enforced here:
  - ATOMIC WRITES: every result/draw file is written to `<path>.tmp.<pid>` then os.replace()'d
    into place — a reader NEVER sees a partial file (SEV-7 #2/#3).
  - PROVENANCE: every result record carries thread_count, torch/transformers versions, hostname,
    config_hash, and the frozen-path marker (SEV-3 registration gap, SEV-4 env-corruption catch).
  - LOCK-THEN-RENAME ORDERING: a task lock is held until AFTER the atomic result rename, so two
    workers can never both pass the "no result yet" check (SEV-7 #4).

No torch import at module top — the generation driver must import this without loading the model.
CPU/offline/thread-pinning is set by the worker entrypoints, not here.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import platform
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


# --------------------------------------------------------------------------- atomic write
def atomic_write_json(path: Path, obj: object) -> None:
    """Write obj as JSON to path atomically: temp file in the same dir, fsync, os.replace.

    Same-directory temp guarantees os.replace is a rename (atomic on APFS), not a cross-device
    copy. fsync before replace so a power loss cannot leave a rename to empty bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic rename
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def append_jsonl(path: Path, obj: object) -> None:
    """Append one JSON line. Append writes ≤ PIPE_BUF are atomic; each line is flushed+fsynced.

    Used for the generation LOG (append-only, resumable). Each record is a single line so a
    crash mid-append leaves at most one torn trailing line, which the loader skips on parse error.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=True) + "\n"
    with open(path, "a") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def load_pruned(path: Path) -> "dict[str, set[int]]":
    """Load the pre-registered pruning register: {task_id: {item_index,...}}.

    Tolerates an absent path, /dev/null, and an empty file (all → no pruning). A pruning file,
    when present, is a JSON list of {task_id, item_index}. This avoids the trap of
    json.loads('') on a /dev/null default (which raises JSONDecodeError).
    """
    pruned: dict[str, set[int]] = {}
    try:
        text = path.read_text().strip()
    except (FileNotFoundError, OSError):
        return pruned
    if not text:
        return pruned
    for it in json.loads(text):
        pruned.setdefault(it["task_id"], set()).add(it["item_index"])
    return pruned


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, skipping a torn trailing line (crash-safety for append_jsonl)."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # torn trailing line from a crash mid-append; skip (and stop — it's the last line)
            break
    return rows


# --------------------------------------------------------------------------- task lock
@contextlib.contextmanager
def task_lock(lock_dir: Path, task_id: str) -> Iterator[Optional[int]]:
    """Advisory non-blocking exclusive lock on a per-task lock file.

    Yields the fd if the lock was acquired, or None if another worker holds it (caller skips the
    task). The lock releases on fd close INCLUDING crash (advisory flock semantics, PROBE-C
    confirmed on APFS). Caller MUST keep the `with` block open until AFTER the atomic result
    rename, so the "no result file yet" check and the write are mutually exclusive (SEV-7 #4).
    """
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{task_id}.lock"
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            yield None
            return
        yield fd
    finally:
        with contextlib.suppress(Exception):
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


# --------------------------------------------------------------------------- provenance
@dataclass(frozen=True)
class Provenance:
    """Environment stamp recorded on every result file (SEV-3/SEV-4 rulings).

    thread_count is the value the process actually set (not the config — thread count is NOT a
    frozen field; recording it is how a mismatched-env worker becomes detectable). versions +
    hostname catch a stale venv / different torch build / wrong machine.
    """
    thread_count: int
    torch_version: str
    transformers_version: str
    hostname: str
    python_version: str
    config_hash: str
    frozen_path: str  # marker naming the exact scoring entrypoint used

    def as_dict(self) -> dict:
        return {
            "thread_count": self.thread_count,
            "torch_version": self.torch_version,
            "transformers_version": self.transformers_version,
            "hostname": self.hostname,
            "python_version": self.python_version,
            "config_hash": self.config_hash,
            "frozen_path": self.frozen_path,
        }


def capture_provenance(thread_count: int, config_hash: str,
                       frozen_path: str = "outcomes.score(NLIScorer())") -> Provenance:
    """Snapshot the runtime environment. Imports torch/transformers lazily (scoring procs only)."""
    import torch  # noqa: PLC0415
    import transformers  # noqa: PLC0415
    return Provenance(
        thread_count=thread_count,
        torch_version=torch.__version__,
        transformers_version=transformers.__version__,
        hostname=socket.gethostname(),
        python_version=platform.python_version(),
        config_hash=config_hash,
        frozen_path=frozen_path,
    )


def set_cpu_threads(n: int) -> None:
    """Pin torch + OMP thread counts to n, deterministic CPU. Call ONCE at process start,
    BEFORE the first torch op. Every scoring process records the n it set (provenance)."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ["OMP_NUM_THREADS"] = str(n)
    import torch  # noqa: PLC0415
    torch.set_num_threads(n)
    torch.use_deterministic_algorithms(True)
