"""
Consistency & Stale Text Scanner for Step 7.
Scans all text, code, and markdown files in the repository for stale or prohibited terms.
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", ".venv311", "__pycache__", ".pytest_cache", "dist"
}

TARGET_PATTERNS = {
    "0.664": re.compile(r"0\.664"),
    "0.684": re.compile(r"0\.684"),
    "isotonic": re.compile(r"isotonic", re.IGNORECASE),
    "active medications": re.compile(r"active medications", re.IGNORECASE),
    "ICD-10": re.compile(r"ICD-10", re.IGNORECASE),
    "HIPAA Safe Harbor": re.compile(r"HIPAA Safe Harbor", re.IGNORECASE),
    "500 encounters as training": re.compile(r"500 (patient )?encounters (used )?as (the )?training", re.IGNORECASE),
    "LaTeX math ($)": re.compile(r"(?<!\\)\$[^$\n]+\$"),
    "TODO": re.compile(r"\bTODO\b"),
}

# Only scan console.log in frontend src code
CONSOLE_LOG_PATTERN = re.compile(r"console\.log\(")

results = {k: [] for k in TARGET_PATTERNS}
results["console.log"] = []

scanned_files = 0

for root, dirs, files in os.walk(BASE_DIR):
    # Prune excluded directories
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for file in files:
        if file.endswith((".py", ".jsx", ".js", ".md", ".json", ".html", ".css", ".txt")):
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, BASE_DIR)
            
            # Skip binary artifacts or audit script itself
            if "verify_repo_consistency_and_stale_text.py" in rel_path:
                continue
            
            scanned_files += 1
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line_idx, line in enumerate(lines, 1):
                    for term, pat in TARGET_PATTERNS.items():
                        # If LaTeX, skip dollar signs in bash commands, currency ($0.12), or regex strings
                        if term == "LaTeX math ($)":
                            if file.endswith(".md"):
                                # Check if it looks like LaTeX math e.g. $N=19,870$
                                m = re.search(r"\$[a-zA-Z0-9_\^\+\-\= ,\\/]+\$", line)
                                if m and not line.strip().startswith("$") and not any(c in line for c in ["npm", "pip", "python", "git", "curl"]):
                                    results[term].append((rel_path, line_idx, line.strip()))
                            continue
                        if pat.search(line):
                            results[term].append((rel_path, line_idx, line.strip()))
                    if "frontend\\src" in rel_path or "frontend/src" in rel_path:
                        if CONSOLE_LOG_PATTERN.search(line):
                            results["console.log"].append((rel_path, line_idx, line.strip()))
            except Exception as e:
                pass

print(f"Scanned {scanned_files} files across repository.")
total_issues = 0
for term, hits in results.items():
    print(f"\n--- Pattern: '{term}' (Matches: {len(hits)}) ---")
    for file, line_num, snippet in hits[:10]:
        print(f"  [{file}:{line_num}] {snippet[:100]}")
    if len(hits) > 10:
        print(f"  ... and {len(hits) - 10} more matches")
    total_issues += len(hits)

print("\n" + "=" * 80)
print(f"TOTAL OCCURRENCES DETECTED: {total_issues}")
print("=" * 80)
