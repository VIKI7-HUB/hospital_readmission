"""
Script for Item 4: Reproducibility verification.
Runs run_pipeline.py, records exact runtime, and checks that every metric matches run 1 identically.
"""

import os
import shutil
import subprocess
import time

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")

run1_csv = os.path.join(MODELS_DIR, "model_comparison_results.csv")
backup_csv = os.path.join(MODELS_DIR, "model_comparison_run1.csv")

if not os.path.exists(backup_csv):
    shutil.copyfile(run1_csv, backup_csv)

print("=" * 80)
print("STARTING RUN 2 OF run_pipeline.py TO VERIFY COMPLETE DETERMINISM")
print("=" * 80)

t0 = time.time()
python_exe = os.path.join(BASE_DIR, ".venv311", "Scripts", "python.exe")
result = subprocess.run([python_exe, "run_pipeline.py"], cwd=BASE_DIR, capture_output=True, text=True, check=False)
elapsed = time.time() - t0

print(f"\n[+] Pipeline Run 2 finished in: {elapsed:.2f} seconds (Exit Code: {result.returncode})")
assert result.returncode == 0, f"Run 2 failed with output:\n{result.stderr}"

# Compare Run 1 and Run 2 metrics
df1 = pd.read_csv(backup_csv)
df2 = pd.read_csv(run1_csv)

print("\n--- METRICS COMPARISON (RUN 1 vs RUN 2) ---")
metric_cols = [
    "Model", "Decision Threshold", "AUC-ROC", "PR-AUC", "Accuracy",
    "Precision", "Recall (Sensitivity)", "F1-Score", "Brier Score",
    "True Positives (TP)", "False Positives (FP)", "True Negatives (TN)", "False Negatives (FN)"
]

mismatches = 0
for col in metric_cols:
    if col in ["Model"]:
        continue
    diff = np.abs(df1[col] - df2[col]).max()
    print(f"  • {col:25s}: Max difference across models = {diff}")
    if diff > 1e-6:
        mismatches += 1

print("\n" + "=" * 80)
if mismatches == 0:
    print("[+] REPRODUCIBILITY CONFIRMED: 100% IDENTICAL METRICS ACROSS RUN 1 AND RUN 2!")
    print(f"[+] Run 2 execution time: {elapsed:.2f} seconds.")
else:
    print(f"[-] Mismatch found: {mismatches} metrics diverged.")
print("=" * 80)
