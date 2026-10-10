import re

css_path = 'frontend/src/styles.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update Root & Dark Theme Tokens
old_tokens_pattern = r':root\s*\{[\s\S]*?/\* Explicit Dark Theme Tokens \*/\s*\[data-theme="dark"\]\s*\{[\s\S]*?/\* Light Mode Tokens \(Toggled\) \*/\s*\[data-theme="light"\]\s*\{[\s\S]*?\}\s*\}'

new_tokens = """:root {
  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;

  /* Sizing & Scale */
  --font-xs: 12px;
  --font-sm: 13px;
  --font-base: 14px;
  --font-md: 15px;
  --font-lg: 16px;
  --font-xl: 18px;
  --font-2xl: 22px;
  --font-3xl: 28px;
  --font-4xl: 32px;

  /* Layout dimensions */
  --sidebar-width: 250px;
  --sidebar-collapsed-width: 72px;
  --topbar-height: 64px;

  /* Surfaces & Backgrounds - Premium Medical Obsidian Palette (Default Dark) */
  --bg-app: #0B0F19;
  --bg-surface: #111827;
  --bg-surface-hover: #162032;
  --bg-subtle: #131D31;
  --bg-subtle-hover: #1A2742;
  --bg-card: #111827;
  --bg-header: rgba(11, 15, 25, 0.85);
  --bg-sidebar: #0D1321;
  --bg-dialog: #111827;
  --bg-row-hover: rgba(30, 41, 59, 0.45);
  --progress-track: #1A2338;

  /* Borders */
  --border-color: rgba(255, 255, 255, 0.08);
  --border-subtle: rgba(255, 255, 255, 0.05);
  --border-hover: rgba(255, 255, 255, 0.16);
  --border-focus: #3B82F6;

  /* Text Colors (WCAG AAA / AA compliant) */
  --text-primary: #F8FAFC;
  --text-secondary: #94A3B8;
  --text-muted: #64748B;
  --text-inverse: #0B0F19;

  /* Clinical Brand Accent (Modern Medical Indigo/Cyan) */
  --accent: #3B82F6;
  --accent-hover: #60A5FA;
  --accent-light: rgba(59, 130, 246, 0.14);
  --accent-border: rgba(59, 130, 246, 0.35);
  --accent-glow: rgba(59, 130, 246, 0.25);
  --brand-indigo: #3B82F6;
  --brand-indigo-hover: #60A5FA;
  --brand-indigo-light: rgba(59, 130, 246, 0.14);
  --brand-indigo-border: rgba(59, 130, 246, 0.35);
  --brand-indigo-dark: #93C5FD;

  /* Semantic Clinical Risk Tokens */
  --risk-high-text: #FB7185;
  --risk-high-bar: #F43F5E;
  --risk-high-bg: rgba(244, 63, 94, 0.12);
  --risk-high-border: rgba(244, 63, 94, 0.32);
  --risk-high-glow: rgba(244, 63, 94, 0.22);

  --risk-med-text: #FBBF24;
  --risk-med-bar: #F59E0B;
  --risk-med-bg: rgba(245, 158, 11, 0.12);
  --risk-med-border: rgba(245, 158, 11, 0.32);
  --risk-med-glow: rgba(245, 158, 11, 0.22);

  --risk-low-text: #34D399;
  --risk-low-bar: #10B981;
  --risk-low-bg: rgba(16, 185, 129, 0.12);
  --risk-low-border: rgba(16, 185, 129, 0.32);
  --risk-low-glow: rgba(16, 185, 129, 0.22);

  /* Status Tokens */
  --status-online: #10B981;
  --status-online-bg: rgba(16, 185, 129, 0.16);
  --status-warning: #F59E0B;
  --status-warning-bg: rgba(245, 158, 11, 0.16);
  --status-danger: #F43F5E;
  --status-danger-bg: rgba(244, 63, 94, 0.16);

  /* Radii */
  --radius-sm: 6px;
  --radius-control: 8px;
  --radius-card: 16px;
  --radius-pill: 9999px;

  /* Shadows */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.45);
  --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 0 1px var(--border-color);
  --shadow-hover: 0 10px 30px -4px rgba(0, 0, 0, 0.65), 0 0 0 1px var(--border-hover);
  --shadow-modal: 0 24px 64px -12px rgba(0, 0, 0, 0.85);

  /* Transitions */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Explicit Dark Theme Tokens */
[data-theme="dark"] {
  --bg-app: #0B0F19;
  --bg-surface: #111827;
  --bg-surface-hover: #162032;
  --bg-subtle: #131D31;
  --bg-subtle-hover: #1A2742;
  --bg-card: #111827;
  --bg-header: rgba(11, 15, 25, 0.85);
  --bg-sidebar: #0D1321;
  --bg-dialog: #111827;
  --bg-row-hover: rgba(30, 41, 59, 0.45);
  --progress-track: #1A2338;

  --border-color: rgba(255, 255, 255, 0.08);
  --border-subtle: rgba(255, 255, 255, 0.05);
  --border-hover: rgba(255, 255, 255, 0.16);
  --border-focus: #3B82F6;

  --text-primary: #F8FAFC;
  --text-secondary: #94A3B8;
  --text-muted: #64748B;
  --text-inverse: #0B0F19;

  --accent: #3B82F6;
  --accent-hover: #60A5FA;
  --accent-light: rgba(59, 130, 246, 0.14);
  --accent-border: rgba(59, 130, 246, 0.35);
  --accent-glow: rgba(59, 130, 246, 0.25);
  --brand-indigo: #3B82F6;
  --brand-indigo-hover: #60A5FA;
  --brand-indigo-light: rgba(59, 130, 246, 0.14);
  --brand-indigo-border: rgba(59, 130, 246, 0.35);
  --brand-indigo-dark: #93C5FD;

  --risk-high-text: #FB7185;
  --risk-high-bar: #F43F5E;
  --risk-high-bg: rgba(244, 63, 94, 0.12);
  --risk-high-border: rgba(244, 63, 94, 0.32);
  --risk-high-glow: rgba(244, 63, 94, 0.22);

  --risk-med-text: #FBBF24;
  --risk-med-bar: #F59E0B;
  --risk-med-bg: rgba(245, 158, 11, 0.12);
  --risk-med-border: rgba(245, 158, 11, 0.32);
  --risk-med-glow: rgba(245, 158, 11, 0.22);

  --risk-low-text: #34D399;
  --risk-low-bar: #10B981;
  --risk-low-bg: rgba(16, 185, 129, 0.12);
  --risk-low-border: rgba(16, 185, 129, 0.32);
  --risk-low-glow: rgba(16, 185, 129, 0.22);

  --status-online: #10B981;
  --status-online-bg: rgba(16, 185, 129, 0.16);
  --status-warning: #F59E0B;
  --status-warning-bg: rgba(245, 158, 11, 0.16);
  --status-danger: #F43F5E;
  --status-danger-bg: rgba(244, 63, 94, 0.16);
}

/* Light Mode Tokens (Clinical Studio White) */
[data-theme="light"] {
  --bg-app: #F8FAFC;
  --bg-surface: #FFFFFF;
  --bg-surface-hover: #F1F5F9;
  --bg-subtle: #F1F5F9;
  --bg-subtle-hover: #E2E8F0;
  --bg-card: #FFFFFF;
  --bg-header: rgba(255, 255, 255, 0.9);
  --bg-sidebar: #FFFFFF;
  --bg-dialog: #FFFFFF;
  --bg-row-hover: #F8FAFC;
  --progress-track: #E2E8F0;

  --border-color: #E2E8F0;
  --border-subtle: #F1F5F9;
  --border-hover: #CBD5E1;
  --border-focus: #2563EB;

  --text-primary: #0F172A;
  --text-secondary: #334155;
  --text-muted: #64748B;
  --text-inverse: #FFFFFF;

  --accent: #2563EB;
  --accent-hover: #1D4ED8;
  --accent-light: #EFF6FF;
  --accent-border: #BFDBFE;
  --accent-glow: rgba(37, 99, 235, 0.2);
  --brand-indigo: #2563EB;
  --brand-indigo-hover: #1D4ED8;
  --brand-indigo-light: #EFF6FF;
  --brand-indigo-border: #BFDBFE;
  --brand-indigo-dark: #1E40AF;

  --risk-high-text: #E11D48;
  --risk-high-bar: #F43F5E;
  --risk-high-bg: #FFF1F2;
  --risk-high-border: #FECDD3;
  --risk-high-glow: rgba(225, 29, 72, 0.15);

  --risk-med-text: #D97706;
  --risk-med-bar: #F59E0B;
  --risk-med-bg: #FFFBEB;
  --risk-med-border: #FDE68A;
  --risk-med-glow: rgba(217, 119, 6, 0.15);

  --risk-low-text: #059669;
  --risk-low-bar: #10B981;
  --risk-low-bg: #ECFDF5;
  --risk-low-border: #A7F3D0;
  --risk-low-glow: rgba(5, 150, 105, 0.15);

  --status-online: #10B981;
  --status-online-bg: #D1FAE5;
  --status-warning: #F59E0B;
  --status-warning-bg: #FEF3C7;
  --status-danger: #E11D48;
  --status-danger-bg: #FFE4E6;

  --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.06);
  --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.05), 0 4px 12px rgba(15, 23, 42, 0.03);
  --shadow-hover: 0 8px 24px rgba(15, 23, 42, 0.08);
  --shadow-modal: 0 20px 48px -12px rgba(15, 23, 42, 0.22);
}"""

# Utilities to insert
utilities_block = """
/* ==========================================================================
   ClinicalAI Essential Utility Primitives
   ========================================================================== */
.flex { display: flex !important; }
.inline-flex { display: inline-flex !important; }
.flex-1 { flex: 1 1 0% !important; }
.flex-col { flex-direction: column !important; }
.flex-wrap { flex-wrap: wrap !important; }
.flex-shrink-0 { flex-shrink: 0 !important; }
.items-center { align-items: center !important; }
.items-start { align-items: flex-start !important; }
.items-end { align-items: flex-end !important; }
.justify-between { justify-content: space-between !important; }
.justify-center { justify-content: center !important; }
.justify-end { justify-content: flex-end !important; }
.grid { display: grid !important; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)) !important; }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
@media (min-width: 768px) {
  .md\\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
}

.gap-1 { gap: 4px !important; }
.gap-1\\.5 { gap: 6px !important; }
.gap-2 { gap: 8px !important; }
.gap-3 { gap: 12px !important; }
.gap-4 { gap: 16px !important; }
.gap-5 { gap: 20px !important; }
.gap-6 { gap: 24px !important; }

.p-1 { padding: 4px !important; }
.p-2 { padding: 8px !important; }
.p-3 { padding: 12px !important; }
.p-4 { padding: 16px !important; }
.mt-1 { margin-top: 4px !important; }
.mt-2 { margin-top: 8px !important; }
.mt-3 { margin-top: 12px !important; }
.mt-4 { margin-top: 16px !important; }
.mb-2 { margin-bottom: 8px !important; }
.mb-3 { margin-bottom: 12px !important; }
.mb-4 { margin-bottom: 16px !important; }

.block { display: block !important; }
.inline { display: inline !important; }
.hidden { display: none !important; }
.w-full { width: 100% !important; }
.min-w-0 { min-width: 0 !important; }
.truncate { overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; }

.w-3 { width: 12px !important; }
.h-3 { height: 12px !important; }
.w-3\\.5 { width: 14px !important; }
.h-3\\.5 { height: 14px !important; }
.w-4 { width: 16px !important; }
.h-4 { height: 16px !important; }
.w-5 { width: 20px !important; }
.h-5 { height: 20px !important; }
.w-6 { width: 24px !important; }
.h-6 { height: 24px !important; }

.text-xs { font-size: var(--font-xs) !important; }
.text-sm { font-size: var(--font-sm) !important; }
.text-base { font-size: var(--font-base) !important; }
.text-lg { font-size: var(--font-lg) !important; }
.font-medium { font-weight: 500 !important; }
.font-semibold { font-weight: 600 !important; }
.font-bold { font-weight: 700 !important; }
.font-mono { font-family: var(--font-mono) !important; }
.text-right { text-align: right !important; }
.text-center { text-align: center !important; }
.leading-relaxed { line-height: 1.625 !important; }

.text-primary { color: var(--text-primary) !important; }
.text-secondary { color: var(--text-secondary) !important; }
.text-muted { color: var(--text-muted) !important; }
.text-white { color: #ffffff !important; }
.text-amber-400 { color: #fbbf24 !important; }
.text-amber-500 { color: #f59e0b !important; }
.text-amber-600 { color: #d97706 !important; }
.text-amber-700 { color: #b45309 !important; }
.text-emerald-500 { color: #10b981 !important; }
.text-emerald-600 { color: #059669 !important; }
.text-red-500 { color: #ef4444 !important; }
.text-red-600 { color: #dc2626 !important; }
.text-red-700 { color: #b91c1c !important; }
.text-indigo-400 { color: #818cf8 !important; }
.text-indigo-500 { color: #6366f1 !important; }
.text-indigo-600 { color: #4f46e5 !important; }
.text-teal-500 { color: #14b8a6 !important; }
.text-violet-500 { color: #8b5cf6 !important; }
"""

# Replace the tokens section
css = re.sub(old_tokens_pattern, new_tokens, css, count=1)

# Insert utility block right after Base & Resets
reset_marker = "/* ==========================================================================\n   Shell Layout"
if reset_marker in css:
    css = css.replace(reset_marker, utilities_block + "\n" + reset_marker)
else:
    # fallback
    css = utilities_block + "\n" + css

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)

print("Updated tokens and injected utility classes.")
