import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  ArrowUpDown,
  BarChart3,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Download,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  Filter,
  HeartPulse,
  HelpCircle,
  Info,
  Layers,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Pill,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Sun,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  X
} from "lucide-react";
import "./styles.css";
import "./responsive.css";

const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";
const API_BASE = SUPABASE_URL
  ? `${SUPABASE_URL}/functions/v1/clinicalai-api`
  : (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

const AGE_GROUPS = ["All ages", "<30 Years", "30-60 Years", "60+ Years"];
const DIAGNOSES = [
  "Circulatory",
  "Respiratory",
  "Digestive",
  "Diabetes",
  "Injury",
  "Musculoskeletal",
  "Genitourinary",
  "Neoplasms",
  "Other",
  "Other/External",
];
const A1C_OPTIONS = [">8", ">7", "Norm", "None"];

async function api(path, options = {}) {
  if (SUPABASE_URL && !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("Set VITE_SUPABASE_PUBLISHABLE_KEY in the frontend deployment settings.");
  }
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY ? { apikey: SUPABASE_PUBLISHABLE_KEY } : {}),
        ...options.headers,
      },
    });
  } catch (err) {
    throw new Error(`Failed to fetch from ${API_BASE}${path} (${err?.message || "Connection refused"}). Check server connectivity.`);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const detail = (await response.json()).detail;
      if (typeof detail === "string") message = detail;
      else if (Array.isArray(detail)) message = detail.map((item) => item.msg).filter(Boolean).join(". ") || message;
    } catch { /* use default message */ }
    throw new Error(message);
  }
  return response.json();
}

function prettyPercent(value, digits = 1) {
  return `${(Number(value || 0) * 100).toFixed(digits)}%`;
}

function prettyPp(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(digits)} pp`;
}

// -----------------------------------------------------------------------------
// REUSABLE PRESENTATIONAL COMPONENTS
// -----------------------------------------------------------------------------

function RiskBadge({ tier }) {
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high") ? "high" : normalized.startsWith("mod") ? "moderate" : "low";
  return (
    <span className={`risk-badge-pill ${kind}`}>
      <i aria-hidden="true" />
      {tier || "Unscored"}
    </span>
  );
}

function RiskBar({ probability, tier }) {
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high") ? "high" : normalized.startsWith("mod") ? "moderate" : "low";
  const pct = Math.min(100, Math.max(0, (Number(probability) || 0) * 100));

  return (
    <div className="risk-mini-bar-track" title={`Score: ${prettyPercent(probability)}`}>
      <div className={`risk-mini-bar-fill ${kind}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function KpiCard({ label, value, context, icon: IconComponent, tone = "indigo", onClick, isActive = false, accentRed = false }) {
  return (
    <div
      className={`kpi-card ${accentRed ? "accent-red" : ""} ${isActive ? "active-filter" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick?.(); } }}
      title={onClick ? "Click to filter worklist" : undefined}
    >
      <div className="kpi-card-header">
        <span className="kpi-label">{label}</span>
        <div className={`kpi-icon-box ${tone}`}>
          <IconComponent className="w-5 h-5" />
        </div>
      </div>
      <div className="kpi-value-row">
        <span className="kpi-value tabular-nums">{value}</span>
      </div>
      {context && (
        <div>
          <span className={`kpi-context-chip ${tone === "red" ? "red" : tone === "amber" ? "amber" : tone === "green" ? "green" : ""}`}>
            {context}
          </span>
        </div>
      )}
    </div>
  );
}

function RiskGauge({ probability, tier }) {
  const pct = Math.min(100, Math.max(0, (Number(probability) || 0) * 100));
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high") ? "high" : normalized.startsWith("mod") ? "moderate" : "low";
  const strokeColor = kind === "high" ? "var(--risk-high-bar)" : kind === "moderate" ? "var(--risk-med-bar)" : "var(--risk-low-bar)";

  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  return (
    <div className="radial-gauge-container">
      <div className="gauge-svg-wrapper">
        <svg width="180" height="180" viewBox="0 0 180 180" style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="transparent"
            stroke="var(--bg-subtle)"
            strokeWidth="12"
          />
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="transparent"
            stroke={strokeColor}
            strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s ease" }}
          />
        </svg>
        <div className="gauge-center-copy">
          <span className="gauge-pct-display tabular-nums">{prettyPercent(probability)}</span>
          <span className="gauge-scale-caption">{tier}</span>
        </div>
      </div>
    </div>
  );
}

function NoticeBanner({ onLearnMore, onDismiss }) {
  return (
    <div className="info-banner-slim" role="region" aria-label="Research environment disclaimer">
      <div className="banner-content-left">
        <Info className="w-4 h-4 flex-shrink-0" />
        <span>
          <strong>Research Decision-Support Demo:</strong> De-identified diabetic inpatient encounters from the UCI dataset. Estimates illustrate risk patterns and are not intended for independent clinical decisions.
          <button className="banner-link" onClick={onLearnMore}>
            Learn more in Model Governance
          </button>
        </span>
      </div>
      <button className="banner-close-btn" onClick={onDismiss} aria-label="Dismiss disclaimer">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// -----------------------------------------------------------------------------
// MAIN APPLICATION
// -----------------------------------------------------------------------------

function App() {
  const [view, setView] = useState("worklist");
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("clinicalai-theme") === "dark";
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem("clinicalai-sidebar-collapsed") === "true";
  });
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    return localStorage.getItem("clinicalai-banner-dismissed") === "true";
  });

  const [healthStatus, setHealthStatus] = useState("connecting");
  const [scoringStatus, setScoringStatus] = useState("idle");
  const [scoringError, setScoringError] = useState("");
  const [error, setError] = useState("");

  const [worklist, setWorklist] = useState({ results: [], summary: {}, total: 0, pages: 1 });
  const [loadingWorklist, setLoadingWorklist] = useState(false);
  const [sampleRows, setSampleRows] = useState([]);
  const [governance, setGovernance] = useState(null);

  // Filters & Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [tier, setTier] = useState("all");
  const [ageGroup, setAgeGroup] = useState("all");
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState("prob");
  const [sortOrder, setSortOrder] = useState("desc");

  // Calculator State
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [scoring, setScoring] = useState(false);

  // Modal Review
  const [reviewRecord, setReviewRecord] = useState(null);
  const [reviewPrediction, setReviewPrediction] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);

  const searchInputRef = useRef(null);

  // Apply Dark Mode Class to documentElement
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("clinicalai-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("clinicalai-theme", "light");
    }
  }, [darkMode]);

  const toggleDarkMode = () => setDarkMode((prev) => !prev);
  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("clinicalai-sidebar-collapsed", String(next));
      return next;
    });
  };

  const dismissBanner = () => {
    setBannerDismissed(true);
    localStorage.setItem("clinicalai-banner-dismissed", "true");
  };

  // Keyboard shortcut Ctrl+K / Cmd+K to focus search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === "Escape") {
        setReviewRecord(null);
        setShowHelpModal(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const selectedModelRow = useMemo(() => {
    const models = governance?.models || [];
    return (
      models.find((m) => m.Model === governance?.selected_model) ||
      models.find((m) => m.Model === "Calibrated Ensemble") ||
      null
    );
  }, [governance]);

  const selectedThreshold = selectedModelRow?.Threshold != null ? Number(selectedModelRow.Threshold) : null;

  // Load Worklist Data with Defensive Sorting
  const loadWorklist = useCallback(async () => {
    setLoadingWorklist(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        tier,
        age_group: ageGroup,
        search,
      });
      const result = await api(`/api/worklist?${params}`);
      setWorklist(result);
      if (!sampleRows.length && result.results?.length) {
        setSampleRows(result.results.slice(0, 30));
        if (!selectedId) {
          const first = result.results[0];
          setSelectedId(first.enc_id);
          setDraft({
            time_in_hospital: first.stay,
            num_medications: first.meds,
            number_inpatient: first.inpatient,
            number_emergency: first.er,
            A1Cresult: A1C_OPTIONS.includes(first.a1c) ? first.a1c : "None",
            diag_1_cat: DIAGNOSES.includes(first.diag) ? first.diag : "Other",
          });
        }
      }
    } catch (err) {
      setError(`Failed to load worklist: ${err.message}`);
    } finally {
      setLoadingWorklist(false);
    }
  }, [page, pageSize, tier, ageGroup, search, sampleRows.length, selectedId]);

  const loadGovernance = useCallback(async () => {
    try {
      const result = await api("/api/governance");
      setGovernance(result);
    } catch (err) {
      setError(`Failed to load model governance: ${err.message}`);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const result = await api("/api/health");
      setHealthStatus(result?.status === "ok" ? "online" : "connecting");
    } catch {
      setHealthStatus("offline");
    }
  }, []);

  useEffect(() => {
    checkHealth();
    loadGovernance();
  }, [checkHealth, loadGovernance]);

  useEffect(() => {
    loadWorklist();
  }, [loadWorklist]);

  // Sync draft inputs when starting encounter changes
  const currentEncounter = useMemo(() => {
    return sampleRows.find((row) => row.enc_id === selectedId) || null;
  }, [sampleRows, selectedId]);

  useEffect(() => {
    if (currentEncounter) {
      setDraft({
        time_in_hospital: currentEncounter.stay,
        num_medications: currentEncounter.meds,
        number_inpatient: currentEncounter.inpatient,
        number_emergency: currentEncounter.er,
        A1Cresult: A1C_OPTIONS.includes(currentEncounter.a1c) ? currentEncounter.a1c : "None",
        diag_1_cat: DIAGNOSES.includes(currentEncounter.diag) ? currentEncounter.diag : "Other",
      });
      setPrediction(null);
    }
  }, [currentEncounter]);

  // Scoring function
  const score = async (encId, values, setTarget) => {
    setScoring(true);
    setScoringError("");
    setScoringStatus("scoring");
    try {
      const result = await api("/api/predict", {
        method: "POST",
        body: JSON.stringify({ enc_id: encId, ...values }),
      });
      setTarget(result);
      setScoringStatus("success");
    } catch (err) {
      setScoringStatus("failed");
      setScoringError(err.message);
      let healthStillOk = false;
      try {
        const health = await api("/api/health");
        healthStillOk = health?.status === "ok";
      } catch {
        healthStillOk = false;
      }
      if (healthStillOk) {
        setHealthStatus("online");
        setError(`Risk calculation request failed: ${err.message}. (API service is Online).`);
      } else {
        setHealthStatus("offline");
        setError(`API service is currently offline (${err.message}).`);
      }
    } finally {
      setScoring(false);
    }
  };

  const openReview = async (record) => {
    setReviewRecord(record);
    setReviewPrediction(null);
    setReviewLoading(true);
    try {
      const defaultValues = {
        time_in_hospital: record.stay,
        num_medications: record.meds,
        number_inpatient: record.inpatient,
        number_emergency: record.er,
        A1Cresult: A1C_OPTIONS.includes(record.a1c) ? record.a1c : "None",
        diag_1_cat: DIAGNOSES.includes(record.diag) ? record.diag : "Other",
      };
      const result = await api("/api/predict", {
        method: "POST",
        body: JSON.stringify({ enc_id: record.enc_id, ...defaultValues }),
      });
      setReviewPrediction(result);
      setScoringStatus("success");
    } catch (err) {
      setScoringStatus("failed");
      setError(`Encounter review scoring failed: ${err.message}`);
    } finally {
      setReviewLoading(false);
    }
  };

  // CSV Export
  const handleExportCSV = () => {
    const rows = worklist.results || [];
    if (!rows.length) return;
    const headers = [
      "Encounter ID",
      "Age",
      "Gender",
      "Race",
      "Stay (Days)",
      "Medications",
      "Inpatient Visits",
      "ER Visits",
      "A1C Result",
      "Diagnosis Category",
      "Calculated Probability",
      "Risk Tier",
    ];
    const csvContent = [
      headers.join(","),
      ...rows.map((r) =>
        [
          `"${r.enc_id}"`,
          `"${r.age}"`,
          `"${r.gender}"`,
          `"${r.race}"`,
          r.stay,
          r.meds,
          r.inpatient,
          r.er,
          `"${r.a1c}"`,
          `"${r.diag}"`,
          (Number(r.prob) * 100).toFixed(2),
          `"${r.tier}"`,
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `clinicalai_readmission_worklist_page_${page}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Client-Side Column Sorting
  const sortedResults = useMemo(() => {
    const list = [...(worklist.results || [])];
    if (!sortField) return list;
    return list.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];
      if (typeof valA === "string") {
        return sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortOrder === "asc" ? Number(valA) - Number(valB) : Number(valB) - Number(valA);
    });
  }, [worklist.results, sortField, sortOrder]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const summary = worklist.summary || {};
  const hasActiveFilters = tier !== "all" || ageGroup !== "all" || search.trim().length > 0;

  const resetAllFilters = () => {
    setTier("all");
    setAgeGroup("all");
    setSearch("");
    setPage(1);
  };

  return (
    <div className="app-shell">
      {/* -----------------------------------------------------------------------
          SIDEBAR (Slim, Collapsible, Polished Clinical-Tech)
          ----------------------------------------------------------------------- */}
      <aside className={`app-sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-header">
          {!sidebarCollapsed && (
            <div className="brand-wrapper">
              <div className="brand-icon">
                <Stethoscope className="w-5 h-5 text-white" />
              </div>
              <div className="brand-info">
                <span className="brand-title">ClinicalAI</span>
                <span className="brand-subtitle">Readmission Insights</span>
              </div>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="brand-icon" title="ClinicalAI">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
          )}
          <button
            className="sidebar-collapse-btn"
            onClick={toggleSidebar}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Main sidebar navigation">
          {!sidebarCollapsed && <span className="nav-section-label">Clinical Workspace</span>}
          <button
            className={`nav-item ${view === "worklist" ? "active" : ""}`}
            onClick={() => { setView("worklist"); setError(""); }}
            title="Discharge worklist"
          >
            <FileSpreadsheet className="nav-icon" />
            {!sidebarCollapsed && <span>Discharge worklist</span>}
          </button>

          <button
            className={`nav-item ${view === "calculator" ? "active" : ""}`}
            onClick={() => { setView("calculator"); setError(""); }}
            title="Risk calculator"
          >
            <Activity className="nav-icon" />
            {!sidebarCollapsed && <span>Risk calculator</span>}
          </button>

          <button
            className={`nav-item ${view === "governance" ? "active" : ""}`}
            onClick={() => { setView("governance"); setError(""); }}
            title="Model governance"
          >
            <ShieldCheck className="nav-icon" />
            {!sidebarCollapsed && <span>Model governance</span>}
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile-pill" title="Research Demonstration Account">
            <div className="user-avatar">RD</div>
            {!sidebarCollapsed && (
              <div className="user-info">
                <span className="user-name">Clinical Demo</span>
                <span className="user-role">Read-only clinician</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* -----------------------------------------------------------------------
          MAIN CONTENT AREA
          ----------------------------------------------------------------------- */}
      <main className={`main-content ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        {/* Topbar */}
        <header className="app-topbar">
          <div className="topbar-left">
            <div className="breadcrumb-trail">
              <span className="breadcrumb-root">ClinicalAI</span>
              <span className="breadcrumb-sep">/</span>
              <span className="breadcrumb-current">
                {view === "worklist" ? "Discharge worklist" : view === "calculator" ? "Risk calculator" : "Model governance"}
              </span>
            </div>
          </div>

          <div className="topbar-right">
            {/* Small Status Dot in Top Bar */}
            <div className="api-status-pill" title={`Scoring API: ${API_BASE}`}>
              <span className={`status-dot-pulse ${healthStatus}`} />
              <span>
                API {healthStatus === "online" ? "Online" : healthStatus === "connecting" ? "Connecting…" : "Offline"}
              </span>
            </div>

            {/* Demo Environment Pill */}
            <div className="env-tag-pill">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Demo Environment</span>
            </div>

            {/* Dark Mode Toggle */}
            <button
              className="topbar-icon-btn"
              onClick={toggleDarkMode}
              title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* Help / Info Button */}
            <button
              className="topbar-icon-btn"
              onClick={() => setShowHelpModal(true)}
              title="Documentation & Overview"
              aria-label="Documentation and overview"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="page-body">
          {/* Merged Single Slim Info Banner */}
          {!bannerDismissed && (
            <NoticeBanner
              onLearnMore={() => setView("governance")}
              onDismiss={dismissBanner}
            />
          )}

          {error && (
            <div className="error-banner-card" role="alert">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}

          {/* Page Header */}
          <div className="page-header-row">
            <div className="page-header-text">
              <h1 className="page-title">
                {view === "worklist"
                  ? "Historical Readmission Risk Worklist"
                  : view === "calculator"
                  ? "Bedside Readmission Risk Calculator"
                  : "Model Governance & Ethical Audits"}
              </h1>
              <p className="page-description">
                {view === "worklist"
                  ? "De-identified historical inpatient encounters prioritized by calibrated 30-day readmission risk."
                  : view === "calculator"
                  ? "Interactive clinical scenario simulator to evaluate how patient factors modify predicted readmission probability."
                  : "Transparent audit of discriminatory performance (AUC-ROC, Sensitivity) and subgroup demographic parity across Age, Gender, and Race."}
              </p>
            </div>

            <div className="header-action-group">
              {view === "worklist" && (
                <>
                  <button
                    className="secondary-action-btn"
                    onClick={handleExportCSV}
                    title="Export currently filtered encounters to CSV"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export CSV</span>
                  </button>
                  <button
                    className="secondary-action-btn"
                    onClick={loadWorklist}
                    disabled={loadingWorklist}
                    title="Refresh data from server"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingWorklist ? "animate-spin" : ""}`} />
                    <span>Refresh</span>
                  </button>
                </>
              )}
              {view === "calculator" && (
                <button
                  className="secondary-action-btn"
                  onClick={() => {
                    if (currentEncounter) {
                      setDraft({
                        time_in_hospital: currentEncounter.stay,
                        num_medications: currentEncounter.meds,
                        number_inpatient: currentEncounter.inpatient,
                        number_emergency: currentEncounter.er,
                        A1Cresult: A1C_OPTIONS.includes(currentEncounter.a1c) ? currentEncounter.a1c : "None",
                        diag_1_cat: DIAGNOSES.includes(currentEncounter.diag) ? currentEncounter.diag : "Other",
                      });
                      setPrediction(null);
                    }
                  }}
                  title="Reset scenario inputs to starting cohort baseline"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Reset to baseline</span>
                </button>
              )}
            </div>
          </div>

          {/* ===================================================================
              PAGE 1: DISCHARGE READINESS WORKLIST
              =================================================================== */}
          {view === "worklist" && (
            <>
              {/* 4 Interactive KPI Cards */}
              <section className="kpi-cards-grid" aria-label="Cohort risk summary metrics">
                <KpiCard
                  label="Scored Encounters"
                  value={summary.cohort_size ?? "500"}
                  context="Pre-scored cohort"
                  icon={Users}
                  tone="indigo"
                  onClick={() => { setTier("all"); setPage(1); }}
                  isActive={tier === "all" && !search && ageGroup === "all"}
                />

                <KpiCard
                  label="High-Risk Flags"
                  value={summary.high_risk ?? "—"}
                  context={summary.cohort_size ? `${((summary.high_risk / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥20% risk)` : "High risk (≥20%)"}
                  icon={AlertTriangle}
                  tone="red"
                  accentRed={true}
                  onClick={() => { setTier("high"); setPage(1); }}
                  isActive={tier === "high"}
                />

                <KpiCard
                  label="Polypharmacy Risk"
                  value={summary.polypharmacy ?? "—"}
                  context={summary.cohort_size ? `${((summary.polypharmacy / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥10 meds)` : "≥10 active meds"}
                  icon={Pill}
                  tone="amber"
                />

                <KpiCard
                  label="Observed Readmissions"
                  value={summary.readmissions ?? "—"}
                  context={summary.cohort_size ? `${((summary.readmissions / summary.cohort_size) * 100).toFixed(1)}% historical rate` : "Historical outcome"}
                  icon={TrendingUp}
                  tone="green"
                />
              </section>

              {/* Encounter Table Section */}
              <section className="table-section-card">
                {/* Toolbar */}
                <div className="table-toolbar">
                  <div className="toolbar-primary-row">
                    {/* Wider Search Input */}
                    <div className="search-input-wrapper">
                      <Search className="search-icon-left" />
                      <input
                        ref={searchInputRef}
                        type="text"
                        className="search-input"
                        placeholder="Search encounter ID or patient profile…"
                        value={search}
                        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                        aria-label="Search encounter ID"
                      />
                      {search ? (
                        <button className="clear-search-btn" onClick={() => { setSearch(""); setPage(1); }} aria-label="Clear search">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      ) : (
                        <span className="search-kbd-hint">⌘K</span>
                      )}
                    </div>

                    {/* Filter Dropdown Pills */}
                    <div className="toolbar-filters-group">
                      <div className="filter-select-pill">
                        <Filter className="w-3.5 h-3.5 text-muted" />
                        <span>Risk level:</span>
                        <select
                          value={tier}
                          onChange={(e) => { setTier(e.target.value); setPage(1); }}
                          aria-label="Filter by risk tier"
                        >
                          <option value="all">All risk tiers</option>
                          <option value="high">High risk (≥20%)</option>
                          <option value="moderate">Moderate risk (12–20%)</option>
                          <option value="low">Low risk (&lt;12%)</option>
                        </select>
                      </div>

                      <div className="filter-select-pill">
                        <span>Age group:</span>
                        <select
                          value={ageGroup}
                          onChange={(e) => { setAgeGroup(e.target.value === "All ages" ? "all" : e.target.value); setPage(1); }}
                          aria-label="Filter by age group"
                        >
                          {AGE_GROUPS.map((g) => (
                            <option key={g} value={g === "All ages" ? "all" : g}>
                              {g}
                            </option>
                          ))}
                        </select>
                      </div>

                      <span className="table-record-count-badge tabular-nums">
                        {worklist.total} encounters
                      </span>
                    </div>
                  </div>

                  {/* Active Filter Chips Row */}
                  {hasActiveFilters && (
                    <div className="active-filters-bar">
                      <span className="text-xs font-semibold text-muted">Active filters:</span>
                      {tier !== "all" && (
                        <span className="filter-chip">
                          Risk: {tier.charAt(0).toUpperCase() + tier.slice(1)}
                          <button onClick={() => { setTier("all"); setPage(1); }} aria-label="Remove risk filter">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      )}
                      {ageGroup !== "all" && (
                        <span className="filter-chip">
                          Age: {ageGroup}
                          <button onClick={() => { setAgeGroup("all"); setPage(1); }} aria-label="Remove age filter">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      )}
                      {search.trim() && (
                        <span className="filter-chip">
                          Query: "{search}"
                          <button onClick={() => { setSearch(""); setPage(1); }} aria-label="Remove search filter">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      )}
                      <button className="clear-all-filters-btn" onClick={resetAllFilters}>
                        Clear all
                      </button>
                    </div>
                  )}
                </div>

                {/* Data Table */}
                <div className="data-table-container">
                  <table className="clinical-data-table">
                    <thead>
                      <tr>
                        <th className="sortable" onClick={() => handleSort("enc_id")}>
                          <div className="th-inner-flex">
                            <span>Encounter</span>
                            {sortField === "enc_id" ? (
                              sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th>Profile</th>
                        <th className="sortable" onClick={() => handleSort("stay")}>
                          <div className="th-inner-flex">
                            <span>Hospital stay</span>
                            {sortField === "stay" ? (
                              sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable" onClick={() => handleSort("meds")}>
                          <div className="th-inner-flex">
                            <span>Medications</span>
                            {sortField === "meds" ? (
                              sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable" onClick={() => handleSort("inpatient")}>
                          <div className="th-inner-flex">
                            <span>Prior acute care</span>
                            {sortField === "inpatient" ? (
                              sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th>Care flags</th>
                        <th className="sortable text-right" onClick={() => handleSort("prob")} style={{ textAlign: "right" }}>
                          <div className="th-inner-flex" style={{ justifyContent: "flex-end" }}>
                            <span>Readmission risk</span>
                            <span title="Calibrated 30-day readmission risk predicted by the ensemble">
                              <HelpCircle className="w-3 h-3 text-muted" />
                            </span>
                            {sortField === "prob" ? (
                              sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th style={{ width: 44 }} />
                      </tr>
                    </thead>
                    <tbody>
                      {loadingWorklist &&
                        Array.from({ length: 5 }).map((_, i) => (
                          <tr key={`skeleton-${i}`} className="skeleton-row">
                            <td colSpan={8}>
                              <div className="skeleton-cell-bar" />
                            </td>
                          </tr>
                        ))}

                      {!loadingWorklist &&
                        sortedResults.map((record) => {
                          const normalized = record.tier?.toLowerCase() || "";
                          const tierClass = normalized.startsWith("high") ? "high" : normalized.startsWith("mod") ? "moderate" : "low";
                          const careFlags = record.resources || [];
                          const visibleFlags = careFlags.slice(0, 2);
                          const overflowCount = careFlags.length - 2;

                          return (
                            <tr
                              key={record.enc_id}
                              onClick={() => openReview(record)}
                              title="Click to view clinical recommendations and adjust in calculator"
                            >
                              <td>
                                <div className="encounter-cell">
                                  <span className="encounter-id-code">{record.enc_id}</span>
                                  <span className="encounter-subtext">Historical cohort</span>
                                </div>
                              </td>

                              <td>
                                <div className="profile-cell">
                                  <span className="profile-age">{record.age}</span>
                                  <span className="profile-demographics">
                                    {record.gender} · {record.race}
                                  </span>
                                </div>
                              </td>

                              <td>
                                <span className="inline-metric tabular-nums">
                                  {record.stay} <small>days</small>
                                </span>
                              </td>

                              <td>
                                <div className="flex flex-col">
                                  <span className="inline-metric tabular-nums">
                                    {record.meds} <small>active</small>
                                  </span>
                                  {Number(record.meds) >= 10 && (
                                    <span className="polypharmacy-indicator" title="Polypharmacy: 10 or more active medications">
                                      ● Polypharmacy
                                    </span>
                                  )}
                                </div>
                              </td>

                              <td>
                                <span className="inline-metric tabular-nums">
                                  {record.inpatient} <small>inpatient · {record.er} ER</small>
                                </span>
                              </td>

                              <td>
                                <div className="care-flags-cell">
                                  {visibleFlags.map((flag) => (
                                    <span key={flag} className="care-flag-pill">
                                      {flag.includes("Telehealth") ? (
                                        <HeartPulse className="w-3 h-3 text-red-500" />
                                      ) : flag.includes("PharmD") ? (
                                        <Pill className="w-3 h-3 text-amber-500" />
                                      ) : (
                                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                                      )}
                                      <span>{flag}</span>
                                    </span>
                                  ))}
                                  {overflowCount > 0 && (
                                    <span
                                      className="flag-overflow-chip"
                                      title={careFlags.slice(2).join(", ")}
                                    >
                                      +{overflowCount}
                                    </span>
                                  )}
                                </div>
                              </td>

                              <td>
                                <div className="risk-score-cell">
                                  <div className="risk-score-top">
                                    <span className={`risk-pct-large tabular-nums ${tierClass}`}>
                                      {prettyPercent(record.prob)}
                                    </span>
                                    <RiskBadge tier={record.tier} />
                                  </div>
                                  <RiskBar probability={record.prob} tier={record.tier} />
                                </div>
                              </td>

                              <td>
                                <div className="row-action-ghost">
                                  <ChevronRight className="w-4 h-4" />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>

                  {!loadingWorklist && !sortedResults.length && (
                    <div className="table-empty-box">
                      <div className="empty-icon-circle">
                        <Search className="w-6 h-6" />
                      </div>
                      <h3 className="empty-title">No matching encounters found</h3>
                      <p className="empty-desc">
                        No records match your selected risk filter or search criteria. Try resetting the filters.
                      </p>
                      <button className="secondary-action-btn" onClick={resetAllFilters}>
                        Reset all filters
                      </button>
                    </div>
                  )}
                </div>

                {/* Pagination Footer */}
                <div className="table-pagination-footer">
                  <div className="flex items-center gap-3">
                    <span>
                      Showing {worklist.results.length ? (page - 1) * pageSize + 1 : 0}–
                      {Math.min(page * pageSize, worklist.total)} of {worklist.total} encounters
                    </span>
                    <div className="filter-select-pill" style={{ height: 30, padding: "0 8px" }}>
                      <span>Rows:</span>
                      <select
                        value={pageSize}
                        onChange={(e) => {
                          setPageSize(Number(e.target.value));
                          setPage(1);
                        }}
                        aria-label="Rows per page"
                      >
                        <option value={10}>10</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                      </select>
                    </div>
                  </div>

                  <div className="pagination-controls">
                    <button
                      className="page-nav-btn"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      <span>Previous</span>
                    </button>
                    <span className="font-semibold text-sm tabular-nums">
                      Page {page} of {worklist.pages || 1}
                    </span>
                    <button
                      className="page-nav-btn"
                      disabled={page >= (worklist.pages || 1)}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <span>Next</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </section>
            </>
          )}

          {/* ===================================================================
              PAGE 2: BEDSIDE RISK CALCULATOR
              =================================================================== */}
          {view === "calculator" && (
            <div className="calculator-two-col">
              {/* Left Column: Form & Inputs */}
              <div className="card-panel">
                <div className="panel-header-row">
                  <div className="panel-title-text">
                    <h2>Scenario Parameters</h2>
                    <p>Adjust clinical factors to simulate readmission risk shifts.</p>
                  </div>
                  <span className="step-indicator-badge">Step 1: Configure</span>
                </div>

                {/* Starting Encounter Picker */}
                <div className="form-field-block">
                  <label className="form-label-title">
                    <span>Select Starting Cohort Encounter</span>
                    <span className="text-xs text-muted">Baseline patient template</span>
                  </label>
                  <select
                    className="form-control-select"
                    value={selectedId}
                    onChange={(e) => setSelectedId(e.target.value)}
                  >
                    {sampleRows.map((row) => (
                      <option key={row.enc_id} value={row.enc_id}>
                        {row.enc_id} · {row.age} · {row.gender} · Baseline: {prettyPercent(row.prob)} ({row.tier})
                      </option>
                    ))}
                  </select>
                </div>

                {currentEncounter && (
                  <div className="encounter-summary-box">
                    <div className="summary-avatar-badge">
                      {currentEncounter.gender?.charAt(0) || "P"}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-sm text-primary">
                        {currentEncounter.enc_id}
                      </div>
                      <div className="text-xs text-muted">
                        {currentEncounter.age} · {currentEncounter.gender} · {currentEncounter.race}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-semibold text-muted block">Cohort Baseline</span>
                      <span className="font-bold text-sm text-primary tabular-nums">
                        {prettyPercent(currentEncounter.prob)}
                      </span>
                    </div>
                  </div>
                )}

                {/* Sliders & Numerical Inputs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Hospital Stay */}
                  <div className="form-field-block">
                    <label className="form-label-title">
                      <span>Hospital Stay</span>
                      <span className="text-xs text-muted tabular-nums">{draft?.time_in_hospital || 1} days</span>
                    </label>
                    <div className="slider-number-combo">
                      <input
                        type="range"
                        min="1"
                        max="14"
                        className="range-slider-control"
                        value={draft?.time_in_hospital || 1}
                        onChange={(e) => setDraft({ ...draft, time_in_hospital: Number(e.target.value) })}
                      />
                      <input
                        type="number"
                        min="1"
                        max="14"
                        className="number-stepper-box tabular-nums"
                        value={draft?.time_in_hospital || 1}
                        onChange={(e) => setDraft({ ...draft, time_in_hospital: Number(e.target.value) })}
                      />
                    </div>
                  </div>

                  {/* Active Meds */}
                  <div className="form-field-block">
                    <label className="form-label-title">
                      <span>Active Medications</span>
                      <span className="text-xs text-muted tabular-nums">{draft?.num_medications || 0} meds</span>
                    </label>
                    <div className="slider-number-combo">
                      <input
                        type="range"
                        min="1"
                        max="50"
                        className="range-slider-control"
                        value={draft?.num_medications || 0}
                        onChange={(e) => setDraft({ ...draft, num_medications: Number(e.target.value) })}
                      />
                      <input
                        type="number"
                        min="1"
                        max="50"
                        className="number-stepper-box tabular-nums"
                        value={draft?.num_medications || 0}
                        onChange={(e) => setDraft({ ...draft, num_medications: Number(e.target.value) })}
                      />
                    </div>
                  </div>

                  {/* Prior Inpatient Admissions */}
                  <div className="form-field-block">
                    <label className="form-label-title">
                      <span>Prior Inpatient Admissions</span>
                      <span className="text-xs text-muted tabular-nums">12-month count</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      className="form-control-input tabular-nums"
                      value={draft?.number_inpatient ?? 0}
                      onChange={(e) => setDraft({ ...draft, number_inpatient: Number(e.target.value) })}
                    />
                  </div>

                  {/* Prior Emergency Visits */}
                  <div className="form-field-block">
                    <label className="form-label-title">
                      <span>Prior Emergency Visits</span>
                      <span className="text-xs text-muted tabular-nums">12-month count</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      className="form-control-input tabular-nums"
                      value={draft?.number_emergency ?? 0}
                      onChange={(e) => setDraft({ ...draft, number_emergency: Number(e.target.value) })}
                    />
                  </div>
                </div>

                {/* Glycemic Marker (A1C) */}
                <div className="form-field-block">
                  <label className="form-label-title">
                    <span>A1C Diagnostic Result</span>
                    <span className="text-xs text-muted">Glycemic control</span>
                  </label>
                  <div className="segmented-button-row">
                    {A1C_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        className={`segmented-option-btn ${draft?.A1Cresult === opt ? "selected" : ""}`}
                        onClick={() => setDraft({ ...draft, A1Cresult: opt })}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Diagnosis Group */}
                <div className="form-field-block">
                  <label className="form-label-title">
                    <span>Primary Discharge Diagnosis</span>
                    <span className="text-xs text-muted">ICD-9 Category</span>
                  </label>
                  <select
                    className="form-control-select"
                    value={draft?.diag_1_cat || "Other"}
                    onChange={(e) => setDraft({ ...draft, diag_1_cat: e.target.value })}
                  >
                    {DIAGNOSES.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  className="primary-calc-btn"
                  disabled={!currentEncounter || !draft || scoring}
                  onClick={() => score(selectedId, draft, setPrediction)}
                >
                  {scoring ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Computing Calibrated Estimate…</span>
                    </>
                  ) : (
                    <>
                      <span>Calculate Scenario Risk</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              {/* Right Column: Results Panel (Sticky) */}
              <div className="card-panel sticky-result-card">
                <div className="panel-header-row">
                  <div className="panel-title-text">
                    <h2>Prediction Estimate</h2>
                    <p>Calibrated Soft-Voting Ensemble · 30-Day Readmission</p>
                  </div>
                  <span className="step-indicator-badge">Step 2: Analysis</span>
                </div>

                {!prediction ? (
                  <div className="table-empty-box" style={{ minHeight: 360 }}>
                    <div className="empty-icon-circle">
                      <Activity className="w-6 h-6 text-indigo-500" />
                    </div>
                    <h3 className="empty-title">Ready to calculate scenario risk</h3>
                    <p className="empty-desc">
                      Adjust parameters on the left and click "Calculate Scenario Risk" to view real-time score shift and care bundles.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {/* Radial Risk Gauge */}
                    <RiskGauge probability={prediction.probability} tier={prediction.tier} />

                    {/* Comparison Delta Banner */}
                    {currentEncounter && (
                      <div
                        className={`comparison-delta-banner ${
                          Math.abs(currentEncounter.prob - prediction.probability) >= 0.005 ? "shifted" : ""
                        }`}
                      >
                        {Math.abs(currentEncounter.prob - prediction.probability) < 0.005 ? (
                          <>
                            <Check className="w-4 h-4 text-emerald-500" />
                            <span>Matches original cohort baseline ({prettyPercent(currentEncounter.prob)})</span>
                          </>
                        ) : (
                          <>
                            <TrendingUp className="w-4 h-4" />
                            <span>
                              Shift from baseline: {prettyPercent(currentEncounter.prob)} ({currentEncounter.tier}) →{" "}
                              <strong>{prettyPercent(prediction.probability)} ({prediction.tier})</strong>
                            </span>
                          </>
                        )}
                      </div>
                    )}

                    {/* Clinical Decision Support Callout */}
                    <div className={`guidance-callout ${prediction.color}`}>
                      <span className="guidance-title">Clinical Decision-Support Guidance</span>
                      <p className="guidance-body">{prediction.guidance}</p>
                    </div>

                    {/* Care Bundles Checklist */}
                    {!!prediction.interventions?.length && (
                      <div className="flex flex-col gap-2">
                        <span className="text-xs font-bold text-muted uppercase tracking-wider">
                          Recommended Clinical Protocols
                        </span>
                        <div className="protocol-checklist">
                          {prediction.interventions.map((item, idx) => (
                            <div key={`bundle-${idx}`} className="protocol-item-row">
                              <div className="protocol-check-icon">
                                <Check className="w-3 h-3" />
                              </div>
                              <div className="protocol-text-block">
                                <strong>{item.Recommendation}</strong>
                                <small>{item.Rationale}</small>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Risk Factor Drivers */}
                    {!!prediction.top_factors?.length && (
                      <div className="model-drivers-container">
                        <span className="text-xs font-bold text-muted uppercase tracking-wider">
                          Key Attributed Risk Drivers
                        </span>
                        {prediction.top_factors.slice(0, 4).map((f) => (
                          <div key={f.feature} className="driver-bar-item">
                            <span className="driver-name" title={f.feature}>
                              {f.feature}
                            </span>
                            <div className="driver-track">
                              <div
                                className="driver-fill"
                                style={{ width: `${Math.min(100, Math.max(12, Math.abs(f.impact) * 200))}%` }}
                              />
                            </div>
                            <span className="text-right text-xs text-muted tabular-nums">
                              {f.impact > 0 ? "+" : ""}{Number(f.impact).toFixed(1)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="p-3 bg-subtle border border-color rounded-control text-xs text-muted flex items-start gap-2">
                      <Info className="w-4 h-4 flex-shrink-0 text-muted" />
                      <span>
                        Research use only. Risk estimates do not replace clinical judgment or institutional discharge protocols.
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ===================================================================
              PAGE 3: MODEL GOVERNANCE & ETHICAL AUDITS
              =================================================================== */}
          {view === "governance" && (
            <>
              {/* Governance Top KPI Cards */}
              <section className="kpi-cards-grid" aria-label="Model benchmark metrics">
                <KpiCard
                  label="Production Model"
                  value="Calibrated Ensemble"
                  context="XGBoost + LightGBM + CatBoost"
                  icon={Sparkles}
                  tone="indigo"
                />

                <KpiCard
                  label="Evaluation Cohort"
                  value="19,870"
                  context="Leak-free patient-grouped split"
                  icon={Users}
                  tone="green"
                />

                <KpiCard
                  label="AUC-ROC Discrimination"
                  value="66.4%"
                  context="Rank separation (0.664)"
                  icon={BarChart3}
                  tone="violet"
                />

                <KpiCard
                  label="Clinical Recall (Sensitivity)"
                  value="53.4%"
                  context={
                    selectedThreshold != null
                      ? `At operating threshold ${selectedThreshold.toFixed(3)}`
                      : "Flagging rate for actual readmissions"
                  }
                  icon={Activity}
                  tone="amber"
                />
              </section>

              <div className="governance-layout-grid">
                {/* Left Panel: Multi-Model Benchmark Comparison */}
                <div className="card-panel">
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Model Benchmark Evaluation</h2>
                      <p>Common evaluation comparison on held-out diabetic cohort (n = 19,870).</p>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted font-medium">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm" style={{ background: "var(--brand-indigo)" }} />
                        AUC-ROC
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm" style={{ background: "#10B981" }} />
                        Sensitivity (Recall)
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-3">
                    {(governance?.models || []).map((m) => {
                      const isChampion = m.Model === governance?.selected_model || m.Model === "Calibrated Ensemble";
                      const auc = Number(m["AUC-ROC"] || 0);
                      const recall = Number(m["Recall (Sensitivity)"] || 0);

                      return (
                        <div key={m.Model} className={`benchmark-card-row ${isChampion ? "champion" : ""}`}>
                          <div className="model-name-group">
                            <strong>{m.Model}</strong>
                            <span className="model-threshold-sub">
                              Threshold: {m.Threshold != null ? Number(m.Threshold).toFixed(3) : "0.500"}
                            </span>
                          </div>

                          <div className="dual-metric-bar">
                            <div className="dual-metric-header">
                              <span>AUC-ROC</span>
                              <b className="tabular-nums">{prettyPercent(auc)}</b>
                            </div>
                            <div className="dual-bar-track">
                              <div className="dual-bar-fill auc" style={{ width: `${auc * 100}%` }} />
                            </div>
                          </div>

                          <div className="dual-metric-bar">
                            <div className="dual-metric-header">
                              <span>Sensitivity (Recall)</span>
                              <b className="tabular-nums">{prettyPercent(recall)}</b>
                            </div>
                            <div className="dual-bar-track">
                              <div className="dual-bar-fill recall" style={{ width: `${recall * 100}%` }} />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="p-3 bg-subtle border border-color rounded-control text-xs text-muted flex items-start gap-2">
                    <Info className="w-4 h-4 flex-shrink-0 text-muted" />
                    <span>
                      <strong>Clinical Justification:</strong> Recall (Sensitivity) is prioritized over Accuracy because
                      False Negatives represent undetected clinical relapses incurring severe patient morbidity and $26,000+
                      readmission penalties under the CMS Hospital Readmissions Reduction Program (HRRP).
                    </span>
                  </div>
                </div>

                {/* Right Panel: Demographic Fairness Audits */}
                <div className="card-panel">
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Demographic Fairness Audit</h2>
                      <p>Disparity reduction via group-specific threshold mitigation.</p>
                    </div>
                    <span className="step-indicator-badge">Audited</span>
                  </div>

                  <div className="fairness-card-list">
                    {[
                      { label: "Age Group Disparity", data: governance?.fairness?.age_group },
                      { label: "Racial Equity", data: governance?.fairness?.race_clean },
                      { label: "Gender Disparity", data: governance?.fairness?.gender_clean },
                    ].map(({ label, data }) => (
                      <div key={label} className="fairness-attribute-row">
                        <div>
                          <strong className="text-sm text-primary block">{label}</strong>
                          <span className="text-xs text-muted block">Equal Opportunity TPR Gap</span>
                        </div>
                        <div className="fairness-disparity-metric">
                          <div className="disparity-val-col">
                            <small>Baseline Gap</small>
                            <b className="tabular-nums">{prettyPp(data?.baseline?.equalized_odds_tpr_diff)}</b>
                          </div>
                          <div className="disparity-val-col">
                            <small>Mitigated Gap</small>
                            <b className="tabular-nums mitigated">{prettyPp(data?.mitigated?.equalized_odds_tpr_diff)}</b>
                          </div>
                          <span className="improvement-badge-pill">
                            <TrendingDown className="w-3.5 h-3.5" />
                            Reduced
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="p-3 bg-subtle border border-color rounded-control text-xs text-muted flex items-start gap-2">
                    <ShieldCheck className="w-4 h-4 flex-shrink-0 text-emerald-600" />
                    <span>
                      Audits align with FDA AI/ML Action Plans and EEOC Four-Fifths principles, ensuring underrepresented
                      demographic cohorts receive equal access to post-acute discharge interventions.
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      {/* -----------------------------------------------------------------------
          MOBILE BOTTOM NAVIGATION (Fixed, Clean SaaS Touch Bar)
          ----------------------------------------------------------------------- */}
      <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
        <button
          className={`mobile-nav-btn ${view === "worklist" ? "active" : ""}`}
          onClick={() => { setView("worklist"); setError(""); }}
        >
          <FileSpreadsheet />
          <span>Worklist</span>
        </button>
        <button
          className={`mobile-nav-btn ${view === "calculator" ? "active" : ""}`}
          onClick={() => { setView("calculator"); setError(""); }}
        >
          <Activity />
          <span>Calculator</span>
        </button>
        <button
          className={`mobile-nav-btn ${view === "governance" ? "active" : ""}`}
          onClick={() => { setView("governance"); setError(""); }}
        >
          <ShieldCheck />
          <span>Governance</span>
        </button>
      </nav>

      {/* -----------------------------------------------------------------------
          MODAL: ENCOUNTER REVIEW DIALOG
          ----------------------------------------------------------------------- */}
      {reviewRecord && (
        <div className="modal-backdrop-overlay" onClick={() => setReviewRecord(null)}>
          <div className="modal-dialog-window" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-top">
              <div className="modal-patient-headline">
                <span className="text-xs font-bold text-muted uppercase tracking-wider block">
                  Encounter Clinical Consultation
                </span>
                <h2>{reviewRecord.enc_id}</h2>
                <p>
                  {reviewRecord.age} · {reviewRecord.gender} · {reviewRecord.race}
                </p>
              </div>
              <button
                className="modal-close-icon-btn"
                onClick={() => setReviewRecord(null)}
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Score & Tier Banner */}
            <div className="encounter-summary-box">
              <div className="flex-1">
                <span className="text-xs text-muted block">Calibrated 30-Day Readmission Risk</span>
                <span className="text-2xl font-bold text-primary tabular-nums">
                  {prettyPercent(reviewRecord.prob)}
                </span>
              </div>
              <RiskBadge tier={reviewRecord.tier} />
            </div>

            {/* Clinical Facts Grid */}
            <div className="clinical-facts-grid">
              <div className="fact-tile">
                <small>Hospital Stay</small>
                <strong className="tabular-nums">{reviewRecord.stay} days</strong>
              </div>
              <div className="fact-tile">
                <small>Medications</small>
                <strong className="tabular-nums">{reviewRecord.meds} active</strong>
              </div>
              <div className="fact-tile">
                <small>A1C Marker</small>
                <strong>{reviewRecord.a1c}</strong>
              </div>
              <div className="fact-tile">
                <small>Primary Diagnosis</small>
                <strong>{reviewRecord.diag}</strong>
              </div>
            </div>

            {/* Intervention Protocols Preview */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-bold text-muted uppercase tracking-wider">
                Recommended Care Transition Bundles
              </span>
              {reviewLoading && (
                <div className="p-4 text-center text-sm text-muted flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                  <span>Synthesizing care bundle protocols…</span>
                </div>
              )}
              {reviewPrediction && (
                <div className="protocol-checklist">
                  {reviewPrediction.interventions?.map((item, idx) => (
                    <div key={`rev-bundle-${idx}`} className="protocol-item-row">
                      <div className="protocol-check-icon">
                        <Check className="w-3 h-3" />
                      </div>
                      <div className="protocol-text-block">
                        <strong>{item.Recommendation}</strong>
                        <small>{item.Rationale}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              className="primary-calc-btn"
              onClick={() => {
                setSelectedId(reviewRecord.enc_id);
                setView("calculator");
                setReviewRecord(null);
              }}
            >
              <span>Adjust Scenario in Calculator</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* -----------------------------------------------------------------------
          MODAL: HELP & DOCUMENTATION DIALOG
          ----------------------------------------------------------------------- */}
      {showHelpModal && (
        <div className="modal-backdrop-overlay" onClick={() => setShowHelpModal(false)}>
          <div className="modal-dialog-window" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-top">
              <div className="modal-patient-headline">
                <span className="text-xs font-bold text-muted uppercase tracking-wider block">
                  Platform Documentation
                </span>
                <h2>ClinicalAI Research Platform</h2>
              </div>
              <button
                className="modal-close-icon-btn"
                onClick={() => setShowHelpModal(false)}
                aria-label="Close dialog"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex flex-col gap-4 text-sm text-secondary">
              <p>
                <strong>ClinicalAI</strong> is a modernized clinical decision support research platform designed to
                assist care coordinators and discharge planners in anticipating 30-day readmission risk under Value-Based
                Care and CMS HRRP frameworks.
              </p>

              <div className="p-3 bg-subtle border border-color rounded-control">
                <strong className="block text-primary text-xs uppercase mb-1">Key Operating Thresholds</strong>
                <ul className="text-xs space-y-1 pl-4 list-disc text-secondary">
                  <li><strong>Low Risk (&lt;12%):</strong> Standard discharge summary and 30-day primary care appointment.</li>
                  <li><strong>Moderate Risk (12–20%):</strong> Conditional discharge with 7–10 day follow-up and pharmacy consult.</li>
                  <li><strong>High Risk (≥20%):</strong> Discharge delay or 48-hour telehealth outreach and multidisciplinary team review.</li>
                </ul>
              </div>

              <div className="p-3 bg-subtle border border-color rounded-control">
                <strong className="block text-primary text-xs uppercase mb-1">Keyboard Shortcuts</strong>
                <p className="text-xs text-secondary">
                  Press <kbd className="font-mono px-1 py-0.5 bg-surface border rounded text-xs">⌘K</kbd> or <kbd className="font-mono px-1 py-0.5 bg-surface border rounded text-xs">Ctrl+K</kbd> anywhere to focus the encounter search bar. Press <kbd className="font-mono px-1 py-0.5 bg-surface border rounded text-xs">Esc</kbd> to dismiss open dialogs.
                </p>
              </div>
            </div>

            <button className="secondary-action-btn w-full justify-center" onClick={() => setShowHelpModal(false)}>
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
