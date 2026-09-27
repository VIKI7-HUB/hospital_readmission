"""
PhishTank Similarity Analysis Engine
=====================================
Compares URLs against *patterns* extracted from the PhishTank dataset.
This is NOT a URL blacklist — it is a pattern-based phishing similarity engine.

Features:
  1. Keyword Matching          (0-40 pts)
  2. Domain Structure Analysis (0-25 pts)
  3. Credential Harvesting     (0-20 pts)
  4. Urgency Indicators        (0-15 pts)
  → Total Similarity Score     (0-100)
  5. Threat Classification     (LOW / MEDIUM / HIGH)
  6. Threat Indicator Checklist
  7. Human-readable Explanation
  8. Awareness Tips
  9. Potential Impact Assessment
"""

import re
from urllib.parse import urlparse
from collections import Counter


# ────────────────────────────────────────────────────────
# PREPROCESSING — build pattern cache from PhishTank data
# ────────────────────────────────────────────────────────

def build_pattern_cache(phishtank_df):
    """
    Preprocess the PhishTank dataset to extract common phishing URL patterns.

    Steps:
      1. Extract domains from every verified URL.
      2. Tokenize each domain by hyphens and dots.
      3. Calculate keyword frequency across all domains.
      4. Compute structural statistics (avg length, hyphens, subdomains).

    Returns a dict that should be cached by the caller.
    """
    domains = []
    for url in phishtank_df["url"].dropna().astype(str):
        try:
            parsed = urlparse(url if url.startswith("http") else f"https://{url}")
            domain = parsed.netloc.lower().strip()
            if domain:
                domains.append(domain)
        except Exception:
            continue

    # Tokenize every domain
    all_tokens = []
    domain_lengths = []
    hyphen_counts = []
    subdomain_counts = []

    for domain in domains:
        tokens = re.split(r"[-.]", domain)
        tokens = [t.lower() for t in tokens if len(t) > 2 and not t.isdigit()]
        all_tokens.extend(tokens)
        domain_lengths.append(len(domain))
        hyphen_counts.append(domain.count("-"))
        subdomain_counts.append(domain.count("."))

    token_freq = Counter(all_tokens)
    top_keywords = [word for word, _ in token_freq.most_common(150)]

    total = max(len(domains), 1)
    avg_domain_length = sum(domain_lengths) / total
    avg_hyphens = sum(hyphen_counts) / total
    avg_subdomains = sum(subdomain_counts) / total

    # Curated suspicious terms observed in phishing campaigns
    suspicious_terms = {
        "verify", "secure", "update", "account", "login", "payment",
        "payroll", "wallet", "authentication", "reset", "support",
        "ledger", "recovery", "mfa", "signin", "confirm", "suspend",
        "alert", "unlock", "validate", "portal", "sso", "auth",
        "credential", "password", "bank", "security", "urgent",
        "billing", "invoice", "expire", "reactivate", "restore",
        "notification", "access", "authorize", "token", "session",
    }

    return {
        "top_keywords": top_keywords,
        "token_freq": token_freq,
        "total_domains": len(domains),
        "avg_domain_length": avg_domain_length,
        "avg_hyphens": avg_hyphens,
        "avg_subdomains": avg_subdomains,
        "suspicious_terms": suspicious_terms,
    }


# ────────────────────────────────────────────────────────
# URL EXTRACTION — pull URLs from simulation text
# ────────────────────────────────────────────────────────

def extract_urls_from_text(text):
    """
    Extract URLs from simulation text, including defanged ``hxxps://`` variants.
    """
    patterns = [
        r"hxxps?://[^\s\]\"\'>]+",
        r"https?://[^\s\]\"\'>]+",
    ]

    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)

    # Deduplicate and clean trailing punctuation
    seen = set()
    result = []
    for url in urls:
        url = url.rstrip(".,;:)'\"\\/")
        normalized = url.replace("hxxps://", "https://").replace("hxxp://", "http://")
        if normalized not in seen and len(url) > 8:
            seen.add(normalized)
            result.append(url)

    return result


# ────────────────────────────────────────────────────────
# CORE ANALYSIS — score a URL against learned patterns
# ────────────────────────────────────────────────────────

def analyze_url(url, pattern_cache):
    """
    Analyse a single URL against phishing patterns learned from PhishTank.

    Returns a result dict containing:
      - total_score (0-100)
      - risk_level (LOW / MEDIUM / HIGH)
      - breakdown dict (keyword, structure, credential, urgency scores)
      - matched_keywords, structure_flags, threat_indicators
      - explanation (human-readable)
      - potential_impacts, awareness_tips
    """
    # Normalise defanged URLs
    clean_url = url.replace("hxxps://", "https://").replace("hxxp://", "http://")
    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url

    try:
        parsed = urlparse(clean_url)
        domain = parsed.netloc.lower().strip()
        path = parsed.path.lower().strip()
    except Exception:
        domain = clean_url.lower()
        path = ""

    full_text = domain + path

    # Tokenize
    tokens = re.split(r"[-./]", full_text)
    tokens = [t.lower() for t in tokens if len(t) > 2 and not t.isdigit()]

    suspicious_terms = pattern_cache["suspicious_terms"]
    top_phish_kw = set(pattern_cache["top_keywords"][:80])

    # ── FEATURE 1: Keyword Matching (0-40) ───────────────
    matched_suspicious = [t for t in tokens if t in suspicious_terms]
    matched_phish = [t for t in tokens if t in top_phish_kw]
    all_matched = sorted(set(matched_suspicious + matched_phish))

    keyword_score = min(40, len(all_matched) * 11)

    # ── FEATURE 2: Domain Structure Analysis (0-25) ──────
    structure_score = 0
    structure_flags = []

    hyphen_count = domain.count("-")
    if hyphen_count >= 3:
        structure_score += 12
        structure_flags.append(f"Excessive hyphens ({hyphen_count})")
    elif hyphen_count >= 1:
        structure_score += 6
        structure_flags.append(f"Hyphenated domain ({hyphen_count})")

    if len(domain) > 35:
        structure_score += 8
        structure_flags.append(f"Very long domain ({len(domain)} chars)")
    elif len(domain) > 22:
        structure_score += 4
        structure_flags.append(f"Long domain ({len(domain)} chars)")

    dot_count = domain.count(".")
    if dot_count >= 4:
        structure_score += 7
        structure_flags.append(f"Deep subdomain nesting ({dot_count} levels)")
    elif dot_count >= 3:
        structure_score += 4
        structure_flags.append(f"Multiple subdomains ({dot_count} levels)")

    risky_tlds = {
        ".net", ".xyz", ".tk", ".ml", ".ga", ".cf", ".gq",
        ".top", ".buzz", ".club", ".info", ".site", ".online",
        ".click", ".link", ".work", ".icu",
    }
    for tld in risky_tlds:
        if domain.endswith(tld):
            structure_score += 5
            structure_flags.append(f"Suspicious TLD ({tld})")
            break

    structure_score = min(25, structure_score)

    # ── Credential Harvesting Indicators (0-20) ──────────
    cred_terms = {
        "login", "signin", "password", "credential", "sso",
        "auth", "verify", "confirm", "account", "token", "session",
    }
    cred_matches = [t for t in tokens if t in cred_terms]
    cred_score = min(20, len(cred_matches) * 7)

    login_paths = ["/login", "/signin", "/auth", "/verify", "/account", "/secure"]
    for lp in login_paths:
        if lp in path:
            cred_score = min(20, cred_score + 5)
            if "login-path" not in cred_matches:
                cred_matches.append("login-path")
            break

    # ── Urgency Indicators (0-15) ────────────────────────
    urgency_terms = {
        "urgent", "immediate", "suspend", "alert", "action",
        "required", "update", "reset", "expire", "lock",
        "reactivate", "restore", "revoke",
    }
    urgency_matches = [t for t in tokens if t in urgency_terms]
    urgency_score = min(15, len(urgency_matches) * 6)

    # ── FEATURE 3: Total Similarity Score (0-100) ────────
    total_score = min(100, keyword_score + structure_score + cred_score + urgency_score)

    # ── FEATURE 4: Threat Classification ─────────────────
    if total_score >= 61:
        risk_level = "HIGH"
        risk_color = "#ef4444"
    elif total_score >= 31:
        risk_level = "MEDIUM"
        risk_color = "#f59e0b"
    else:
        risk_level = "LOW"
        risk_color = "#10b981"

    # ── FEATURE 6: Threat Indicators ─────────────────────
    threat_indicators = {}
    if all_matched:
        threat_indicators["Suspicious URL Keywords"] = True
    if cred_matches:
        threat_indicators["Credential Harvesting"] = True
    if urgency_matches:
        threat_indicators["Urgency Manipulation"] = True

    authority_terms = {
        "admin", "cfo", "ceo", "hr", "portal", "corporate",
        "company", "director", "manager", "executive", "official",
    }
    if any(t in tokens for t in authority_terms):
        threat_indicators["Authority Impersonation"] = True
    if structure_flags:
        threat_indicators["Suspicious Domain Structure"] = True

    social_terms = {"team", "colleague", "employee", "staff", "department", "helpdesk"}
    if any(t in tokens for t in social_terms):
        threat_indicators["Social Pressure"] = True

    # ── FEATURE 5: Explanation ───────────────────────────
    explanation_parts = []
    if all_matched:
        kw_list = ", ".join(f"<b>{k}</b>" for k in all_matched)
        explanation_parts.append(
            f"The URL contains terms commonly found in verified phishing URLs: {kw_list}."
        )
    if structure_flags:
        explanation_parts.append(
            f"Domain structure analysis flagged: {'; '.join(structure_flags)}."
        )
    if cred_matches:
        clean_cred = [c for c in cred_matches if c != "login-path"]
        if clean_cred:
            explanation_parts.append(
                f"Credential harvesting indicators: {', '.join(clean_cred)}."
            )
    if urgency_matches:
        explanation_parts.append(
            f"Urgency-related terms detected: {', '.join(urgency_matches)}."
        )
    explanation_parts.append(
        "This pattern is frequently observed in phishing campaigns from the PhishTank dataset."
    )

    # Potential impacts
    impacts = []
    if cred_matches:
        impacts.extend(["Credential Theft", "Unauthorized Access"])
    financial_terms = {"payment", "payroll", "bank", "wire", "invoice", "billing"}
    if any(t in tokens for t in financial_terms):
        impacts.append("Financial Fraud")
    identity_terms = {"account", "identity", "personal", "profile"}
    if any(t in tokens for t in identity_terms):
        impacts.append("Identity Fraud")
    if not impacts:
        impacts = ["Data Exposure", "Phishing Risk"]

    # ── FEATURE 8: Awareness tips ────────────────────────
    awareness_tips = [f'URLs containing "{kw}"' for kw in all_matched[:5]]
    if len(all_matched) >= 3:
        awareness_tips.append("Long domains with multiple trust-related keywords")
    if cred_matches:
        awareness_tips.append("Requests for credentials via suspicious portals")
    if urgency_matches:
        awareness_tips.append("URLs with urgency-inducing language")

    return {
        "url": url,
        "domain": domain,
        "total_score": total_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "breakdown": {
            "Keyword Similarity": keyword_score,
            "Domain Structure Risk": structure_score,
            "Credential Harvesting Indicators": cred_score,
            "Urgency Indicators": urgency_score,
        },
        "matched_keywords": all_matched,
        "structure_flags": structure_flags,
        "threat_indicators": threat_indicators,
        "explanation": " ".join(explanation_parts),
        "potential_impacts": list(set(impacts)),
        "awareness_tips": awareness_tips,
    }
