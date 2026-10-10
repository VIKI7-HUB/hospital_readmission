import re

css_path = 'frontend/src/styles.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Enhance info-banner-slim
old_banner = r'\.info-banner-slim\s*\{[\s\S]*?\}\s*\[data-theme="dark"\]\s*\.info-banner-slim\s*\{[\s\S]*?\}'
new_banner = """.info-banner-slim {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 16px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.22);
  border-radius: 12px;
  color: #93C5FD;
  font-size: var(--font-sm);
  line-height: 1.45;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.06);
}

[data-theme="light"] .info-banner-slim {
  background: #EFF6FF;
  border-color: #BFDBFE;
  color: #1E40AF;
  box-shadow: 0 2px 10px rgba(37, 99, 235, 0.05);
}"""
css = re.sub(old_banner, new_banner, css, count=1)

# 2. Add styles for encounter-summary-box additions
summary_box_additions = """
.encounter-summary-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  margin-top: 10px;
}

.summary-patient-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-enc-id {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.summary-enc-details {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.summary-baseline-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 8px;
}

.summary-baseline-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.summary-baseline-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--brand-indigo);
}
"""

if ".summary-patient-meta" not in css:
    css = css.replace(".encounter-summary-box {", summary_box_additions + "\n/* Original encounter summary */\n.old-encounter-summary-box {", 1)

# 3. Add styles for drawer-action-chip additions
chip_styles = """
.drawer-action-chip {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.drawer-action-chip:hover {
  background: var(--bg-subtle-hover);
  border-color: var(--border-hover);
}

.drawer-action-chip.checked {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.35);
}

.drawer-action-content {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
}

.drawer-action-title {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.35;
  margin: 0;
}

.drawer-action-desc {
  font-size: var(--font-xs);
  color: var(--text-secondary);
  line-height: 1.45;
  margin: 0;
}
"""

if ".drawer-action-content" not in css:
    css = css.replace(".drawer-action-chip {", chip_styles + "\n/* Original chip */\n.old-drawer-action-chip {", 1)

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)

print("Enhanced component styles in styles.css successfully.")
