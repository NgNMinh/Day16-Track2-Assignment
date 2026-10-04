#!/usr/bin/env python3
"""Benchmark fraud detection on creditcard.csv; run on the lab CPU node."""

import argparse
import hashlib
import inspect
import json
import os
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


def measure_prediction(model, frame, threshold, repeats, warmups=10):
    """Time a full sklearn predict_proba call and probability-to-label conversion."""
    def predict():
        return (model.predict_proba(frame)[:, 1] >= threshold).astype(np.int8)

    for _ in range(warmups):
        predict()
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        predict()
        samples.append(perf_counter() - start)
    return {
        "rows_per_call": len(frame),
        "repeats": repeats,
        "warmup_calls": warmups,
        "mean_ms": float(np.mean(samples) * 1000),
        "median_ms": float(np.median(samples) * 1000),
        "p95_ms": float(np.percentile(samples, 95) * 1000),
        "throughput_rows_per_second": float(len(frame) / np.mean(samples)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("creditcard.csv"))
    parser.add_argument("--output", type=Path, default=Path("benchmark_result.json"))
    parser.add_argument("--threads", type=int, default=min(2, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    if not args.data.is_file():
        parser.error(f"Dataset not found: {args.data.resolve()}")

    started_at = datetime.now(timezone.utc).isoformat()
    print(f"Host: {platform.node()} | Python {platform.python_version()} | threads={args.threads}", flush=True)
    print(f"Loading {args.data.resolve()} ...", flush=True)
    start = perf_counter()
    data = pd.read_csv(args.data)
    load_seconds = perf_counter() - start
    expected_columns = {"Time", "Amount", "Class", *(f"V{i}" for i in range(1, 29))}
    if set(data.columns) != expected_columns:
        raise ValueError("Expected Time, Amount, V1..V28 and Class columns")
    if data.isna().any().any() or not np.isfinite(data.to_numpy()).all():
        raise ValueError("Dataset contains missing or non-finite values")
    if set(data["Class"].unique()) != {0, 1}:
        raise ValueError("Class must contain both 0 and 1")

    features = data.drop(columns="Class")
    target = data["Class"].astype(np.int8)
    start = perf_counter()
    # 64% training / 16% validation / 20% test. Test labels never select parameters.
    x_train_all, x_test, y_train_all, y_test = train_test_split(
        features, target, test_size=0.20, stratify=target, random_state=42
    )
    x_train, x_valid, y_train, y_valid = train_test_split(
        x_train_all, y_train_all, test_size=0.20, stratify=y_train_all, random_state=42
    )
    split_seconds = perf_counter() - start
    if len(x_test) < 1000:
        raise ValueError("Test set must have at least 1000 rows for the batch benchmark")
    split_counts = {
        name: {"rows": len(labels), "fraud_rows": int(labels.sum())}
        for name, labels in (("train", y_train), ("validation", y_valid), ("test", y_test))
    }
    print(f"Dataset: {len(data):,} rows | {int(target.sum()):,} frauds | splits={split_counts}", flush=True)

    parameters = {
        "objective": "binary",
        "metric": "auc",
        "n_estimators": 1000,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 20,
        "reg_lambda": 1.0,
        "scale_pos_weight": float((y_train == 0).sum() / (y_train == 1).sum()),
        # Start at probability 0.5 when using large class weights to avoid
        # extreme first-step updates from the very small unweighted fraud prior.
        "boost_from_average": False,
        "random_state": 42,
        "n_jobs": args.threads,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
    }
    model = lgb.LGBMClassifier(**parameters)
    validation_arguments = (
        {"eval_X": x_valid, "eval_y": y_valid}
        if "eval_X" in inspect.signature(model.fit).parameters
        else {"eval_set": [(x_valid, y_valid)]}
    )
    print("Training LightGBM with early stopping on validation AUC ...", flush=True)
    start = perf_counter()
    model.fit(
        x_train,
        y_train,
        **validation_arguments,
        eval_metric="auc",
        callbacks=[
            lgb.early_stopping(50, first_metric_only=True, verbose=True),
            lgb.log_evaluation(100),
        ],
    )
    training_seconds = perf_counter() - start

    # Tune the classification threshold on validation data, never on the test set.
    validation_probabilities = model.predict_proba(x_valid)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_valid, validation_probabilities)
    validation_f1 = 2 * precisions[:-1] * recalls[:-1] / np.maximum(
        precisions[:-1] + recalls[:-1], np.finfo(float).eps
    )
    threshold_index = int(np.argmax(validation_f1))
    threshold = float(thresholds[threshold_index])
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= threshold).astype(np.int8)
    metrics = {
        "auc_roc": float(roc_auc_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1_score": float(f1_score(y_test, predictions, zero_division=0)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=[0, 1]).tolist(),
    }

    print("Measuring inference: 1000 single-row calls and 100 batches of 1000 rows ...", flush=True)
    single = measure_prediction(model, x_test.iloc[:1], threshold, repeats=1000)
    batch = measure_prediction(model, x_test.iloc[:1000], threshold, repeats=100)
    digest = hashlib.sha256()
    with args.data.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    result = {
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "threads": args.threads,
            "package_versions": {name: version(name) for name in ("lightgbm", "scikit-learn", "pandas", "numpy")},
        },
        "dataset": {
            "path": str(args.data.resolve()),
            "sha256": digest.hexdigest(),
            "rows": len(data),
            "features": features.shape[1],
            "fraud_rows": int(target.sum()),
            "split": split_counts,
            "split_method": "stratified random split, random_state=42",
        },
        "load_data_seconds": load_seconds,
        "split_data_seconds": split_seconds,
        "training_seconds": training_seconds,
        "best_iteration": int(model.best_iteration_),
        "model_parameters": parameters,
        "early_stopping": {"metric": "auc", "stopping_rounds": 50, "dataset": "validation"},
        "decision_threshold": threshold,
        "threshold_selection": "maximum F1 on validation data only",
        "validation_f1_at_threshold": float(validation_f1[threshold_index]),
        "test_metrics": metrics,
        "inference_latency_ms": single["median_ms"],
        "inference_throughput_rows_per_second": batch["throughput_rows_per_second"],
        "inference": {
            "method": "LGBMClassifier.predict_proba plus threshold, in-memory pandas input, perf_counter",
            "single_row": single,
            "batch_1000_rows": batch,
        },
        "limitations": "Random holdout benchmark; inference excludes disk/network I/O. Timings depend on EC2 load and CPU credits.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    rows = [
        ("Load data", f"{load_seconds:.6f} s"),
        ("Training", f"{training_seconds:.6f} s"),
        ("Best iteration", str(model.best_iteration_)),
        ("AUC-ROC", f"{metrics['auc_roc']:.6f}"),
        ("Accuracy", f"{metrics['accuracy']:.6f}"),
        ("F1-Score", f"{metrics['f1_score']:.6f}"),
        ("Precision", f"{metrics['precision']:.6f}"),
        ("Recall", f"{metrics['recall']:.6f}"),
        ("Inference latency (1 row, median)", f"{single['median_ms']:.6f} ms"),
        ("Inference throughput (1000 rows)", f"{batch['throughput_rows_per_second']:.2f} rows/s"),
        ("Inference time (1000 rows, mean)", f"{batch['mean_ms']:.6f} ms"),
    ]
    print("\nMetric                                      Result")
    print("-" * 72)
    for label, value in rows:
        print(f"{label:43s} {value}")
    print(f"Decision threshold (validation F1): {threshold:.8f}")
    print(f"Confusion matrix [[TN, FP], [FN, TP]]: {metrics['confusion_matrix']}")
    print(f"Results saved to: {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
