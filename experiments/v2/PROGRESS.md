# v2 progress log (durable; read this first after any crash)

Branch: `v2-direct-evidence`. Artifacts: `cache/runs/<run_id>/` (each has manifest.json with stage status + checksums).

## Verified facts (start of v2)
- BASELINE (leaderboard ~0.97x): `cache/experiments/BASELINE_BEST/matching_results.tsv` sha256 d6fbfeed69e3…; model `lgbm_model.txt` b6448bea9c14…; dict 2a6f14eb2a6e…; candidates 168dd4fde9c2…; code = git 0f49019.
- `output/matching_results.tsv` is ALREADY the baseline (same sha d6fbfeed…) — safe default in place.
- FAILED run E10 (leaderboard 0.933): `cache/experiments/SUBMISSION_E10/matching_results.tsv` sha256 9506e15a43b6…; committed in git 551ef93.
- Candidates: 10 per S2/S3 record; `candidate_pairs.tsv` unchanged between runs.

## Policy
- No sibling / cluster-agreement features in any production decision (v1 failure). Features must be direct S1<->record evidence and invariant to duplicating other records.
- New split: TRAIN = S1 id%5 in {2,3,4}; DEV = id%5==0 (old fold B, heavily used); CONF = id%5==1 (confirmation, opened once at the end).

## Log
- [2026-09-26 10:46] v2 Indic dictionary from TRAIN fold only: 526 entries (v1 fold-A dict: 526; overlap 526)
- [2026-09-26 10:50] v2train candidates ready: 103,202,190 pairs
- [2026-09-26 10:57] v2test candidates ready: 99,695,890 pairs
- [2026-09-26 10:57] v2 candidates verified identical to v1 for train and test (so v1 base feature files are reused by copy)
- [2026-09-26 11:21] watchdog aborted featx+B0 when run in parallel (big patch file); rule: heavy jobs strictly sequential; both resumable
- [2026-09-26 11:25] featx v2train: 43 files done
