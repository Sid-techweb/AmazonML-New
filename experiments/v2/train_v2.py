"""v2 pairwise model: fit on TRAIN-fold records only, score every candidate pair, keep top-3 per record.
usage: python train_v2.py <config_name>
Every config uses only direct record<->S1 evidence (plus the baseline's own features for B0)."""
import json
import sys
import time

import lightgbm as lgb
import numpy as np
import polars as pl

from runlib import Run, cache_path, mem, note
from features import FEATURES

XCOLS = ["nm_wcov_q", "nm_wcov_s", "nm_qonly_idf_max", "nm_sonly_idf_max", "nm_shared_idf",
         "ad_wcov_q", "ad_qonly_idf_max", "ad_qonly_n_rare", "ad_shared_idf",
         "prem_eq", "prem_in_s", "s_prem_in_q", "q_nums_subset", "prem_close", "raw_name_eq", "raw_addr_eq"]
NO_POP = [f for f in FEATURES if f != "s1_rank1_deg"]  # s1_rank1_deg counts other records -> population dependent
CONFIGS = {
    "B0_baseline_refit": dict(feats=FEATURES, frac=0.10, leaves=255, extra=False),
    "C1_no_population_feat": dict(feats=NO_POP, frac=0.10, leaves=255, extra=False),
    "C2_direct_x": dict(feats=NO_POP + XCOLS, frac=0.10, leaves=255, extra=True),
    "C3_direct_x_more_data": dict(feats=NO_POP + XCOLS, frac=0.25, leaves=255, extra=True),
}
SEED = 42
name = sys.argv[1]
cfg = CONFIGS[name]
split = sys.argv[2] if len(sys.argv) > 2 else "v2train"   # model is always FIT on v2train; other splits are scored only
run = Run(f"model_{name}", cfg, code_files=[__file__])
FEATS = cfg["feats"]
def dirs(sp):
    return cache_path(f"{sp}_feats"), cache_path(f"{sp}_featx")


feat_dir, x_dir = dirs("v2train")
files = sorted(feat_dir.glob("*.parquet"))


def frame(f, x_dir=x_dir):
    d = pl.read_parquet(f, columns=["q_idx", "s1_idx"] + [c for c in FEATS if c not in XCOLS])
    if cfg["extra"]:
        d = d.join(pl.read_parquet(x_dir / f.name), on=["q_idx", "s1_idx"], how="left")
    return d


if not run.done("fit"):
    split_s1 = pl.read_parquet(cache_path("runs") / "v2_data" / "split_s1.parquet")
    gt = (pl.read_parquet(cache_path("train_ground_truth.parquet")).filter(pl.col("matched_entity_ids") != "")
          .with_columns(pl.col("matched_entity_ids").str.split(",")).explode("matched_entity_ids"))
    q = pl.concat([pl.read_parquet(cache_path(f"train_{s}.parquet"), columns=["entity_id"]) for s in ("source2", "source3")]).with_row_index("q_idx")
    lab = (gt.join(split_s1.select("s1_idx", "entity_id"), left_on="source1_entity_id", right_on="entity_id")
             .join(q, left_on="matched_entity_ids", right_on="entity_id").select("q_idx", pl.col("s1_idx").alias("true_s1")))
    top1 = pl.scan_parquet(str(cache_path("v2train_cands") / "*.parquet")).filter(pl.col("rank") == 1).select("q_idx", pl.col("s1_idx").alias("top1")).collect()
    qf = (top1.join(lab, on="q_idx", how="full", coalesce=True).with_columns(pl.coalesce("true_s1", "top1").alias("g"))
          .join(split_s1.select(pl.col("s1_idx").alias("g"), "fold"), on="g", how="left").select("q_idx", "true_s1", "fold"))
    del q, gt, top1
    keep_tr = (pl.col("fold") == "TRAIN") & ((pl.col("q_idx").hash(SEED) % 1000) < int(cfg["frac"] * 1000))
    keep_es = (pl.col("fold") == "TRAIN") & ~keep_tr & ((pl.col("q_idx").hash(SEED + 1) % 1000) < 15)
    # count, then fill preallocated arrays
    n_tr = n_es = 0
    for f in files:
        d = pl.read_parquet(f, columns=["q_idx"]).join(qf, on="q_idx", how="left")
        n_tr += d.filter(keep_tr).height; n_es += d.filter(keep_es).height
    Xa = np.empty((n_tr, len(FEATS)), np.float32); ya = np.empty(n_tr, np.float32)
    Xe = np.empty((n_es, len(FEATS)), np.float32); ye = np.empty(n_es, np.float32)
    ia = ie = 0
    for f in files:
        d = frame(f).join(qf, on="q_idx", how="left").with_columns((pl.col("s1_idx") == pl.col("true_s1")).fill_null(False).alias("y"))
        a, b = d.filter(keep_tr), d.filter(keep_es)
        Xa[ia:ia + a.height] = a.select(FEATS).to_numpy(); ya[ia:ia + a.height] = a["y"].to_numpy(); ia += a.height
        Xe[ie:ie + b.height] = b.select(FEATS).to_numpy(); ye[ie:ie + b.height] = b["y"].to_numpy(); ie += b.height
    print(f"train rows {n_tr:,} (pos {ya.mean():.3f}) es rows {n_es:,}", mem(), flush=True)
    params = dict(objective="binary", learning_rate=0.05, num_leaves=cfg["leaves"], min_data_in_leaf=200, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, max_bin=255, num_threads=16, seed=SEED, verbose=-1)
    t0 = time.time()
    m = lgb.train(params, lgb.Dataset(Xa, ya, feature_name=FEATS, free_raw_data=True), 3000,
                  valid_sets=[lgb.Dataset(Xe, ye)], callbacks=[lgb.early_stopping(50), lgb.log_evaluation(250)])
    del Xa, ya, Xe, ye
    m.save_model(str(run.path("model.txt")))
    imp = sorted(zip(FEATS, m.feature_importance("gain")), key=lambda t: -t[1])[:15]
    run.complete("fit", files=["model.txt"], best_iter=m.best_iteration, fit_sec=round(time.time() - t0),
                 top_features=[(k, round(float(v))) for k, v in imp])
    print("fit done", m.best_iteration, imp[:8], flush=True)

if not run.done(f"score_{split}"):
    m = lgb.Booster(model_file=str(run.path("model.txt")))
    parts = []
    sf, sx = dirs(split)
    for f in sorted(sf.glob("*.parquet")):
        d = frame(f, sx)
        p = m.predict(d.select(FEATS).to_numpy(), num_threads=16).astype(np.float32)
        s = d.select("q_idx", "s1_idx").with_columns(pl.Series("p", p))
        parts.append(s.sort(["q_idx", "p"], descending=[False, True]).group_by("q_idx", maintain_order=True).agg(
            pl.col("s1_idx").head(3).alias("s"), pl.col("p").head(3).alias("pp")))
    top = pl.concat(parts).with_columns(
        pl.col("s").list.get(0).alias("s1_idx"), pl.col("pp").list.get(0).alias("p1"),
        pl.col("s").list.get(1, null_on_oob=True).alias("s1_2"), pl.col("pp").list.get(1, null_on_oob=True).fill_null(0.0).alias("p2"),
        pl.col("pp").list.get(2, null_on_oob=True).fill_null(0.0).alias("p3")).drop("s", "pp")
    run.write_parquet(top, f"top3_{split}.parquet")
    run.complete(f"score_{split}", files=[f"top3_{split}.parquet"])
note(f"{name} on {split}: fit+score complete ({run.m['stages']['fit'].get('best_iter')} trees)")
run.release()
