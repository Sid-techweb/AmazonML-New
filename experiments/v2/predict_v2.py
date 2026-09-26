"""Write a coherent submission bundle from ONE verified run into cache/runs/submission_<model>/.
usage: python predict_v2.py <model_config_name> <threshold>
 * scores v2test with the model (train_v2.py scoring stage), keeps each record's best S1 (one S1 per record)
 * matching_results.tsv  = records whose best probability >= threshold, grouped by S1
 * candidate_pairs.tsv   = every (S1, record) pair the model scored (all retrieved candidates)
 * checks: matches subset of candidates, one S1 per record, every test S1 present; official validator"""
import json
import subprocess
import sys

import polars as pl

from runlib import ROOT, RUNS, Run, cache_path, mem, note, sha
from predict import write_grouped
from train import id_tables

name, T = sys.argv[1], float(sys.argv[2])
model_run = f"model_{name}"
if not (RUNS / model_run / "top3_v2test.parquet").exists():
    subprocess.run([sys.executable, "-u", "-W", "ignore", "train_v2.py", name, "v2test"], check=True)
run = Run(f"submission_{name}", {"model": model_run, "threshold": T})
top = pl.read_parquet(RUNS / model_run / "top3_v2test.parquet")
s1, q = id_tables("test")
s1_ids, q_ids = s1["entity_id"], q["entity_id"]
del s1, q
assert top["q_idx"].n_unique() == top.height, "one row per record expected"
matches = top.filter(pl.col("p1") >= T).select("s1_idx", "q_idx")
cand = pl.concat([pl.read_parquet(f, columns=["s1_idx", "q_idx"], memory_map=False) for f in sorted(cache_path("v2test_cands").glob("*.parquet"))])
missing = matches.join(cand, on=["s1_idx", "q_idx"], how="anti").height
assert missing == 0, f"{missing} matches are not candidates"
n, n_c = write_grouped(s1_ids, q_ids, cand, "candidate_entity_ids", run.path("candidate_pairs.tsv"))
del cand
n2, n_m = write_grouped(s1_ids, q_ids, matches, "matched_entity_ids", run.path("matching_results.tsv"))
assert n == n2 == len(s1_ids)
res = {"model": model_run, "threshold": T, "matched_records": matches.height, "accept_rate": matches.height / top.height,
       "s1_with_matches": n_m, "s1_rows": n, "s1_with_candidates": n_c}
v = subprocess.run([sys.executable, str(ROOT / "utils" / "validate_submission.py"), "--matching", str(run.path("matching_results.tsv")),
                    "--candidate", str(run.path("candidate_pairs.tsv")), "--test-dir", str(ROOT / "dataset" / "test")],
                   capture_output=True, text=True)
res["validator"] = "PASS" if v.returncode == 0 else v.stdout[-2000:]
res["sha_matching"] = sha(run.path("matching_results.tsv"))
res["sha_candidates"] = sha(run.path("candidate_pairs.tsv"))
run.path("bundle.json").write_text(json.dumps(res, indent=1))
run.complete("bundle", files=["matching_results.tsv", "candidate_pairs.tsv", "bundle.json"])
note(f"submission bundle {name} t={T}: {matches.height:,} matches (accept {res['accept_rate']:.4f}), validator {res['validator'][:4]}")
run.release()
print(json.dumps(res, indent=1), mem())
