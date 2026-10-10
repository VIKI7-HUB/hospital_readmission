from __future__ import annotations


def pretty(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()


def describe_risk(
    contribs: list[tuple[str, str, float]], labels: dict | None = None, top: int = 3
) -> str:
    """contribs: (feature, display_value, log_odds_contribution). Returns one fixed-template sentence."""
    labels = labels or {}
    ordered = sorted(contribs, key=lambda c: c[2], reverse=True)
    up = [c for c in ordered if c[2] > 0][:top]
    down = [c for c in reversed(ordered) if c[2] < 0][:top]

    def fmt(items):
        return "; ".join(f"{labels.get(f, pretty(f))} ({v})" for f, v, _ in items)

    parts = []
    if up:
        parts.append(f"Higher risk mainly because of: {fmt(up)}.")
    else:
        parts.append("No feature pushes the risk above the average patient.")
    if down:
        parts.append(f"Lower risk because of: {fmt(down)}.")
    return " ".join(parts)
