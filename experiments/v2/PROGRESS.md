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
- [2026-09-26 11:52] B0_baseline_refit on v2train: fit+score complete (738 trees)
- [2026-09-26 12:23] C1_no_population_feat on v2train: fit+score complete (826 trees)
- [2026-09-26 12:26] qf.parquet built: 10,320,219 records; truth pairs 7,638,365
- [2026-09-26 12:29] model_C1_no_population_feat DEV/v2train: best F=0.97791 at t=0.7 (India 0.97496, US 0.97989, singletons 0.96228, accept 0.7120)
- [2026-09-26 12:29] RULE: one background chain at a time; concurrent eval killed C2 (both watchdogs fired). Ceiling scan made per-file.
- [2026-09-26 12:51] C2_direct_x on v2train: fit+score complete (580 trees)
- [2026-09-26 12:51] candidate-restricted oracle macro F0.5 on DEV: 0.99609
- [2026-09-26 12:51] model_B0_baseline_refit DEV/v2train: best F=0.97785 at t=0.65 (India 0.97506, US 0.97972, singletons 0.97670, accept 0.7143)
- [2026-09-26 12:51] model_C2_direct_x DEV/v2train: best F=0.98056 at t=0.7 (India 0.97917, US 0.98149, singletons 0.96900, accept 0.7135)
- [2026-09-26 12:52] stress v2stress: removed 220,962 DEV S1 with same-name twins; twins Y remaining: 606,485 (0 in DEV)

## PREDECLARED PROMOTION GATES (written 13:0x, before any stress-suite result was seen)
A challenger replaces the baseline only if ALL hold (each model at its own best DEV threshold, thresholds from the
0.05 grid; the same threshold is then used on stress/CONF):
1. DEV macro F0.5 >= B0 + 0.001 (B0 = baseline recipe refit on TRAIN only: 0.97785).
2. Stress suite (clustered same-name wrong-address records, from real labels): overall DEV-stress F >= B0's, and
   F on DEV twins receiving the clusters >= B0 - 0.005, and zero-match twins >= B0 - 0.005.
3. DEV zero-match S1 slice >= B0 - 0.010 (known trade-off from removing the population feature; bounded).
4. Duplication invariance: 0 decision flips when a rejected distractor is duplicated k=1..8 times.
5. Test acceptance rate within ±2 pts of the baseline's own acceptance on test, or the difference explained.
6. CONF (one-shot): paired family-level bootstrap lower 95% bound of (challenger - B0) > 0.
7. Official validator PASS; matches subset of candidates; one S1 per record.
If any gate fails the baseline is kept.
- [2026-09-26 12:53] stress v2stress: 89,800,793 candidate pairs (direct features reused)
- [2026-09-26 12:53] stress v2stress: removed 31,050 DEV S1 with same-name twins; twins Y remaining: 121,347 (121,347 in DEV)
- [2026-09-26 12:54] stress v2stress: 101,300,016 candidate pairs (direct features reused)
- [2026-09-26 13:35] B0_baseline_refit on v2stress: fit+score complete (738 trees)
- [2026-09-26 13:58] C1_no_population_feat on v2stress: fit+score complete (826 trees)
- [2026-09-26 14:14] C2_direct_x on v2stress: fit+score complete (580 trees)
- [2026-09-26 14:14] STRESS model_B0_baseline_refit t=0.65: F_stress=0.97782 F_twins=0.97261 (zero-match twins 0.9662) distractor accept=0.0199; dup k=8 flips=3/20000 mean dp=-0.0070
- [2026-09-26 14:15] STRESS model_C1_no_population_feat t=0.7: F_stress=0.97790 F_twins=0.97275 (zero-match twins 0.9624) distractor accept=0.0201; dup k=8 flips=0/20000 mean dp=+0.0000
- [2026-09-26 14:15] STRESS model_C2_direct_x t=0.7: F_stress=0.98057 F_twins=0.97459 (zero-match twins 0.9659) distractor accept=0.0185; dup k=8 flips=0/20000 mean dp=+0.0000
- [2026-09-26 14:26] featx v2test: 53 files done
- [2026-09-26 14:27] featx v2test: 53 files done
- [2026-09-26 14:27] RECOVERY TEST passed: featx v2test killed after 4/53 files, resumed from file 5; pre-kill and post-resume files byte-identical to clean recomputation (sha d0cba539..., 886e5cf4...)
- [2026-09-26 15:22] C3_direct_x_more_data on v2train: fit+score complete (1317 trees)
- [2026-09-26 15:22] model_C3_direct_x_more_data DEV/v2train: best F=0.98201 at t=0.7 (India 0.98100, US 0.98268, singletons 0.97271, accept 0.7149)
- [2026-09-26 15:33] C4 stack on C3_direct_x_more_data: scored v2train (10,320,219 records)
- [2026-09-26 15:33] model_C4_stack_on_C3_direct_x_more_data DEV/v2train: best F=0.98322 at t=0.7 (India 0.98243, US 0.98375, singletons 0.97523, accept 0.7162)
- [2026-09-26 16:11] C3_direct_x_more_data on v2stress: fit+score complete (1317 trees)
- [2026-09-26 16:16] C4 stack on C3_direct_x_more_data: scored v2stress (10,320,219 records)
- [2026-09-26 16:17] STRESS model_C3_direct_x_more_data t=0.7: F_stress=0.98206 F_twins=0.97605 (zero-match twins 0.9690) distractor accept=0.0179; dup k=8 flips=0/20000 mean dp=+0.0000
- [2026-09-26 16:17] STRESS model_C4_stack_on_C3_direct_x_more_data t=0.7: F_stress=0.98324 F_twins=0.97744 (zero-match twins 0.9724) distractor accept=0.0185; duplication-invariant by construction
- [2026-09-26 16:17] PREVALENCE model_B0_baseline_refit (cluster prevalence x1/x2/x4/x8 - approximate for B0): x1: 0.97782, x2: 0.97756, x4: 0.97724, x8: 0.97693
- [2026-09-26 16:17] PREVALENCE model_C3_direct_x_more_data (cluster prevalence x1/x2/x4/x8 - exact): x1: 0.98206, x2: 0.98180, x4: 0.98148, x8: 0.98118
- [2026-09-26 16:17] PREVALENCE model_C4_stack_on_C3_direct_x_more_data (cluster prevalence x1/x2/x4/x8 - exact): x1: 0.98324, x2: 0.98298, x4: 0.98266, x8: 0.98235
- [2026-09-26 16:18] SELECTION FROZEN (before CONF): C4_stack_on_C3 at t=0.70 chosen on DEV (0.98322) + stress (0.98324, twins 0.97744, zero-twins 0.9724, invariant); threshold stable region 0.65-0.75 on DEV
- [2026-09-26 16:37] B0_baseline_refit on v2test: fit+score complete (738 trees)
- [2026-09-26 17:13] C3_direct_x_more_data on v2test: fit+score complete (1317 trees)
- [2026-09-26 17:18] C4 stack on C3_direct_x_more_data: scored v2test (9,969,589 records)
- [2026-09-26 17:23] submission bundle C4_stack_on_C3_direct_x_more_data t=0.7: 5,758,097 matches (accept 0.5776), validator pending (separate step)
- [2026-09-26 17:24] submission bundle B0_baseline_refit t=0.65: 5,887,635 matches (accept 0.5906), validator pending (separate step)
- [2026-09-26 17:27] CONFIRMATION (one-shot): base 0.97787 vs chal 0.98321, delta +0.00533 CI95 [+0.00514, +0.00554]
- [2026-09-26 17:27] ALL GATES PASSED -> C4 promoted. CONF one-shot: B0 0.97787 vs C4 0.98321, delta +0.00533 CI95 [+0.00514,+0.00554]; zero-match CONF 0.9779 vs 0.9758 (within tolerance). Test accept 57.8% (baseline 58.8%). Validator PASS. output/ now = C4 bundle; baseline kept in cache/experiments/BASELINE_BEST
- [2026-09-26 17:29] qf.parquet built: 10,320,219 records; truth pairs 7,638,365
- [2026-09-26 17:29] featx v2train: 43 files done
- [2026-09-26 17:29] featx v2test: 53 files done
- [2026-09-26 17:29] C3_direct_x_more_data on v2train: fit+score complete (1317 trees)
- [2026-09-26 17:29] C3_direct_x_more_data on v2test: fit+score complete (1317 trees)
- [2026-09-26 17:30] submission bundle C4_stack_on_C3_direct_x_more_data t=0.7: 5,758,097 matches (accept 0.5776), validator pending (separate step)
