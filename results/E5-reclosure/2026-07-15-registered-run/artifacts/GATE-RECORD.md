# E5 run gate — the verifiable record

The registered arms run was gated by FREEZE-BEFORE-DATA, performed manually and verifiable by anyone:

| Event | Artifact | Timestamp (UTC) |
|---|---|---|
| Corpus frozen public (60 tasks) | commit `5deb8eb453394a5c88a2b34e083471d3e466eff1` on origin/main | 2026-07-15 15:11:40Z |
| Arm-B instruction frozen public | commit `379c767f9ca5f99a971f0dbbb735caf2964659c7` on origin/main | 2026-07-15 15:25:40Z |
| **First paid arm generation** | first row of `arms-log.jsonl` (task F1-0003, arm A) | **2026-07-15 15:28:29Z** |

Every generation row carries `config_hash = 6dbe47a8…` matching the committed `harness/config.sha256`
at those commits. Check: `git log --format="%H %cI" 379c767 5deb8eb` vs `head -1 arms-log.jsonl`.

Context: an OSF deposit was not used for this run; freeze-by-public-commit served as the
registration gate, per the amendment recorded in PROTOCOL.md ("Pre-registration record"). The gate was executed by hand (verify freeze → push
→ launch) rather than by the in-code gate of `run_e5.py` (committed `2acfeb5`, not used in this
run); `run_arms.py` is the driver that ran.
This record makes the manually executed gate independently verifiable.
