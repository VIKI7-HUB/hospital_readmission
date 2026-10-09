import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { motion, AnimatePresence } from "framer-motion";
import { Command } from "cmdk";
import { Toaster, toast } from "sonner";
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
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  Filter,
  HeartPulse,
  HelpCircle,
  Info,
  Keyboard,
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
  X,
} from "lucide-react";
import { motionTokens, createVariants } from "./motion.js";
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
    } catch { /* use default */ }
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
// MOTION & DELIGHT HELPER COMPONENTS
// -----------------------------------------------------------------------------

function AnimatedNumber({ value, duration = 800, format = (v) => Math.round(v).toLocaleString() }) {
  const [displayValue, setDisplayValue] = useState(0);
  const target = Number(value) || 0;

  useEffect(() => {
    let startTimestamp = null;
    let frameId;
    const initial = 0;

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // easeOutExpo
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = initial + (target - initial) * ease;
      setDisplayValue(current);
      if (progress < 1) {
        frameId = requestAnimationFrame(step);
      }
    };
    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [target, duration]);

  return <span className="tabular-nums">{format(displayValue)}</span>;
}

function MiniSparkline({ tone = "indigo" }) {
  const points = useMemo(() => {
    if (tone === "red") return "0,16 12,14 24,18 36,10 48,12 60,6 72,9 84,3 96,5 110,2";
    if (tone === "amber") return "0,15 14,14 28,11 42,13 56,8 70,10 84,7 98,9 110,4";
    if (tone === "green") return "0,6 15,9 30,7 45,12 60,10 75,14 90,12 105,16 110,18";
    return "0,14 12,11 24,13 36,8 48,10 60,6 72,8 84,4 96,6 110,3";
  }, [tone]);

  const color =
    tone === "red"
      ? "var(--risk-high-bar)"
      : tone === "amber"
      ? "var(--risk-med-bar)"
      : tone === "green"
      ? "var(--risk-low-bar)"
      : "var(--brand-indigo)";

  return (
    <svg className="kpi-sparkline-svg" viewBox="0 0 110 20" preserveAspectRatio="none">
      <path className="kpi-sparkline-path" d={`M ${points}`} stroke={color} />
    </svg>
  );
}

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
      <motion.div
        className={`risk-mini-bar-fill ${kind}`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      />
    </div>
  );
}

function KpiCard({
  label,
  value,
  context,
  icon: IconComponent,
  tone = "indigo",
  onClick,
  isActive = false,
  accentRed = false,
  rawNumber = null,
}) {
  return (
    <motion.div
      className={`kpi-card ${accentRed ? "accent-red" : ""} ${isActive ? "selected-filter" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      title={onClick ? "Click to filter worklist (click again to clear)" : undefined}
      whileHover={{ y: -4, transition: { duration: 0.18, ease: "easeOut" } }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="kpi-card-header">
        <span className="kpi-label">{label}</span>
        <div className={`kpi-icon-box ${tone} ${accentRed ? "has-pulse" : ""}`}>
          <IconComponent className="w-5 h-5" />
        </div>
      </div>

      <div className="kpi-value-row">
        <span className="kpi-value tabular-nums">
          {rawNumber != null ? (
            <AnimatedNumber value={rawNumber} />
          ) : (
            value
          )}
        </span>
        {isActive && <span className="kpi-filtering-chip">Filtering</span>}
      </div>

      <MiniSparkline tone={tone} />

      {context && (
        <div>
          <span
            className={`kpi-context-chip ${
              tone === "red" ? "red" : tone === "amber" ? "amber" : tone === "green" ? "green" : ""
            }`}
          >
            {context}
          </span>
        </div>
      )}
    </motion.div>
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
            fill="none"
            stroke="var(--border-color)"
            strokeWidth="12"
          />
          <motion.circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth="12"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            strokeLinecap="round"
          />
        </svg>
        <div className="gauge-center-content">
          <span className="gauge-pct-display tabular-nums">
            <AnimatedNumber value={pct} format={(v) => `${v.toFixed(1)}%`} />
          </span>
          <span className="gauge-scale-caption">{tier}</span>
        </div>
      </div>
    </div>
  );
}

function NoticeBanner({ onLearnMore, onDismiss }) {
  return (
    <motion.div
      className="info-banner-slim"
      role="region"
      aria-label="Research environment disclaimer"
      initial={{ opacity: 0, y: -8, height: 0 }}
      animate={{ opacity: 1, y: 0, height: "auto" }}
      exit={{ opacity: 0, height: 0, transition: { duration: 0.2 } }}
    >
      <div className="banner-content-left">
        <Info className="w-4 h-4 flex-shrink-0" />
        <span>
          <strong>Research Decision-Support Demo:</strong> De-identified diabetic inpatient encounters from the UCI dataset. Estimates illustrate risk patterns and are not intended for independent clinical decisions.
          <button className="banner-link" onClick={onLearnMore}>
            Learn more in Model Governance
          </button>
        </span>
      </div>
      <button className="banner-dismiss-btn" onClick={onDismiss} aria-label="Dismiss disclaimer">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

function DrawerCareActionChip({ action, index }) {
  const [checked, setChecked] = useState(false);
  return (
    <motion.div
      className={`drawer-action-chip ${checked ? "checked" : ""}`}
      onClick={() => setChecked(!checked)}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index, duration: 0.2 }}
    >
      <div className="drawer-action-checkbox">
        {checked && <Check className="w-3 h-3 text-white" />}
      </div>
      <div className="flex flex-col">
        <strong className="text-sm font-semibold">{action.label}</strong>
        <small className="text-xs text-muted">{action.desc}</small>
      </div>
    </motion.div>
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
  const [reduceMotion, setReduceMotion] = useState(() => {
    return (
      localStorage.getItem("clinicalai-reduced-motion") === "true" ||
      (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches)
    );
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

  // Drawer & Modal Review
  const [reviewRecord, setReviewRecord] = useState(null);
  const [reviewPrediction, setReviewPrediction] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [openPalette, setOpenPalette] = useState(false);

  // Micro-interactions state
  const [refreshedSuccess, setRefreshedSuccess] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [focusedRowIndex, setFocusedRowIndex] = useState(0);

  const searchInputRef = useRef(null);
  const variants = useMemo(() => createVariants(reduceMotion), [reduceMotion]);

  // Apply Theme & Reduced Motion to documentElement
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("clinicalai-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("clinicalai-theme", "light");
    }
  }, [darkMode]);

  useEffect(() => {
    document.documentElement.setAttribute("data-reduced-motion", reduceMotion ? "true" : "false");
    localStorage.setItem("clinicalai-reduced-motion", String(reduceMotion));
  }, [reduceMotion]);

  // Track window scroll for topbar hairline shadow
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 8);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      toast.success(`Theme switched to ${next ? "dark" : "light"} mode`);
      return next;
    });
  };

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

  // Keyboard Navigation & Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // ⌘K or Ctrl+K opens Command Palette
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpenPalette((prev) => !prev);
        return;
      }

      // If palette or drawer or help is open, ESC closes them
      if (e.key === "Escape") {
        if (openPalette) { setOpenPalette(false); return; }
        if (reviewRecord) { setReviewRecord(null); return; }
        if (showHelpModal) { setShowHelpModal(false); return; }
      }

      // If modal or palette is open, don't intercept list shortcuts
      if (openPalette || reviewRecord || showHelpModal) return;

      // "/" focuses search bar if not typing in an input
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // "j" and "k" navigate table rows when in worklist
      if (view === "worklist" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "SELECT") {
        const rowCount = worklist.results?.length || 0;
        if (e.key === "j" || e.key === "ArrowDown") {
          e.preventDefault();
          setFocusedRowIndex((idx) => Math.min(idx + 1, rowCount - 1));
        } else if (e.key === "k" || e.key === "ArrowUp") {
          e.preventDefault();
          setFocusedRowIndex((idx) => Math.max(idx - 1, 0));
        } else if (e.key === "Enter" && rowCount > 0) {
          e.preventDefault();
          const target = worklist.results[focusedRowIndex];
          if (target) openReview(target);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [openPalette, reviewRecord, showHelpModal, view, worklist.results, focusedRowIndex]);

  const selectedModelRow = useMemo(() => {
    const models = governance?.models || [];
    return (
      models.find((m) => m.Model === governance?.selected_model) ||
      models.find((m) => m.Model === "Calibrated Ensemble") ||
      null
    );
  }, [governance]);

  const selectedThreshold = selectedModelRow?.Threshold != null ? Number(selectedModelRow.Threshold) : null;

  // Load Worklist Data
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

  // Refresh handler with checkmark morph
  const handleRefresh = async () => {
    await loadWorklist();
    setRefreshedSuccess(true);
    toast.success("Encounter worklist refreshed from API");
    setTimeout(() => setRefreshedSuccess(false), 1500);
  };

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

  // Scoring function with 600ms analysis shimmer
  const score = async (encId, values, setTarget) => {
    setScoring(true);
    setScoringError("");
    setScoringStatus("scoring");
    try {
      // 600ms simulated analysis animation
      await new Promise((r) => setTimeout(r, 600));
      const result = await api("/api/predict", {
        method: "POST",
        body: JSON.stringify({ enc_id: encId, ...values }),
      });
      setTarget(result);
      setScoringStatus("success");
      toast.success("Risk scenario calculation complete");
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
      toast.error(`Calculation failed: ${err.message}`);
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
    if (!rows.length) {
      toast.error("No encounter records available to export.");
      return;
    }
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
          (Number(r.prob) * 100).toFixed(2) + "%",
          `"${r.tier}"`,
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `clinicalai_readmission_worklist_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`Exported ${rows.length} encounters to CSV`);
  };

  // Client-side Column Sorting
  const sortedResults = useMemo(() => {
    const list = [...(worklist.results || [])];
    list.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (sortField === "enc_id") {
        aVal = a.enc_id || "";
        bVal = b.enc_id || "";
        return sortOrder === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      aVal = Number(aVal) || 0;
      bVal = Number(bVal) || 0;
      return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
    });
    return list;
  }, [worklist.results, sortField, sortOrder]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const resetAllFilters = () => {
    setTier("all");
    setAgeGroup("all");
    setSearch("");
    setPage(1);
    toast.info("All worklist filters cleared");
  };

  const hasActiveFilters = tier !== "all" || ageGroup !== "all" || search.trim() !== "";
  const summary = worklist.summary || {};

  return (
    <div className="app-shell">
      {/* Ambient Aurora Gradient Canvas */}
      <div className="ambient-aurora-bg" aria-hidden="true">
        <div className="aurora-blob-1" />
        <div className="aurora-blob-2" />
      </div>

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
            <div className="brand-wrapper">
              <div className="brand-icon" title="ClinicalAI">
                <Stethoscope className="w-5 h-5 text-white" />
              </div>
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

          {/* Worklist Nav Item */}
          <button
            className={`nav-item ${view === "worklist" ? "active" : ""}`}
            onClick={() => { setView("worklist"); setError(""); }}
            title="Discharge worklist"
          >
            {view === "worklist" && (
              <motion.div
                layoutId="activeNavIndicator"
                className="nav-item-active-pill"
                transition={motionTokens.springs.snappy}
              />
            )}
            {view === "worklist" && (
              <motion.div
                layoutId="activeNavBar"
                className="nav-item-active-bar"
                transition={motionTokens.springs.snappy}
              />
            )}
            <div className="nav-item-content">
              <FileSpreadsheet className="nav-icon" />
              {!sidebarCollapsed && <span>Discharge worklist</span>}
            </div>
          </button>

          {/* Risk Calculator Nav Item */}
          <button
            className={`nav-item ${view === "calculator" ? "active" : ""}`}
            onClick={() => { setView("calculator"); setError(""); }}
            title="Risk calculator"
          >
            {view === "calculator" && (
              <motion.div
                layoutId="activeNavIndicator"
                className="nav-item-active-pill"
                transition={motionTokens.springs.snappy}
              />
            )}
            {view === "calculator" && (
              <motion.div
                layoutId="activeNavBar"
                className="nav-item-active-bar"
                transition={motionTokens.springs.snappy}
              />
            )}
            <div className="nav-item-content">
              <Activity className="nav-icon" />
              {!sidebarCollapsed && <span>Risk calculator</span>}
            </div>
          </button>

          {/* Model Governance Nav Item */}
          <button
            className={`nav-item ${view === "governance" ? "active" : ""}`}
            onClick={() => { setView("governance"); setError(""); }}
            title="Model governance"
          >
            {view === "governance" && (
              <motion.div
                layoutId="activeNavIndicator"
                className="nav-item-active-pill"
                transition={motionTokens.springs.snappy}
              />
            )}
            {view === "governance" && (
              <motion.div
                layoutId="activeNavBar"
                className="nav-item-active-bar"
                transition={motionTokens.springs.snappy}
              />
            )}
            <div className="nav-item-content">
              <ShieldCheck className="nav-icon" />
              {!sidebarCollapsed && <span>Model governance</span>}
            </div>
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
        {/* Topbar with Translucent Blur */}
        <header className={`app-topbar ${isScrolled ? "scrolled" : ""}`}>
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
            {/* Quick Command Palette Button */}
            <button
              className="topbar-icon-btn"
              onClick={() => setOpenPalette(true)}
              title="Open Command Palette (⌘K / Ctrl+K)"
              aria-label="Open Command Palette"
            >
              <Search className="w-4 h-4" />
            </button>

            {/* Small Status Dot in Top Bar */}
            <div className="api-status-pill" title={`Scoring API: ${API_BASE}`}>
              <span className={`status-dot-pulse ${healthStatus}`} />
              <span>
                API {healthStatus === "online" ? "Online" : healthStatus === "connecting" ? "Connecting…" : "Offline"}
              </span>
            </div>

            {/* Single Demo Environment Pill */}
            <div className="env-tag-pill" title="De-identified demonstration sandbox">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Demo Environment</span>
            </div>

            {/* Dark Mode Toggle */}
            <button
              className="topbar-icon-btn"
              onClick={toggleDarkMode}
              title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              aria-label="Toggle dark mode"
            >
              <motion.div
                key={darkMode ? "moon" : "sun"}
                initial={{ rotate: -90, scale: 0.8 }}
                animate={{ rotate: 0, scale: 1 }}
                transition={{ duration: 0.2 }}
              >
                {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-600" />}
              </motion.div>
            </button>

            {/* Platform Help Modal Trigger */}
            <button
              className="topbar-icon-btn"
              onClick={() => setShowHelpModal(true)}
              title="Platform documentation and shortcuts"
              aria-label="Help and documentation"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Page Body Container */}
        <div className="page-body">
          {/* Dismissible Slim Info Banner */}
          <AnimatePresence>
            {!bannerDismissed && (
              <NoticeBanner
                onLearnMore={() => {
                  setView("governance");
                  dismissBanner();
                }}
                onDismiss={dismissBanner}
              />
            )}
          </AnimatePresence>

          {/* Error Banner */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-control text-sm text-red-700 dark:text-red-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
              <button onClick={() => setError("")} className="text-red-500 hover:text-red-700 p-1">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Page Header Row */}
          <div className="page-header-row">
            <div className="page-title-group">
              <h1>
                {view === "worklist" && "Discharge Worklist"}
                {view === "calculator" && "Bedside Risk Calculator"}
                {view === "governance" && "Model Governance & Audits"}
              </h1>
              <p>
                {view === "worklist" && "Prioritize transitioning inpatients by calibrated 30-day readmission probability."}
                {view === "calculator" && "Interactive scenario testing with real-time risk estimation and protocol bundling."}
                {view === "governance" && "Algorithmic transparency, calibration benchmarks, and demographic fairness audits."}
              </p>
            </div>

            {view === "worklist" && (
              <div className="page-actions-group">
                <button
                  className="secondary-action-btn"
                  onClick={handleExportCSV}
                  title="Export current cohort to CSV"
                >
                  <Download className="w-4 h-4" />
                  <span>Export CSV</span>
                </button>
                <button
                  className="secondary-action-btn"
                  onClick={handleRefresh}
                  disabled={loadingWorklist}
                  title="Refresh worklist from API"
                >
                  {refreshedSuccess ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-500" />
                      <span className="text-emerald-600 dark:text-emerald-400">Refreshed</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className={`w-4 h-4 ${loadingWorklist ? "animate-spin" : ""}`} />
                      <span>Refresh</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* ===================================================================
              PAGE 1: DISCHARGE WORKLIST
              =================================================================== */}
          {view === "worklist" && (
            <>
              {/* 4 Interactive KPI Cards */}
              <section className="kpi-cards-grid" aria-label="Cohort risk summary metrics">
                <KpiCard
                  label="Scored Encounters"
                  value={summary.cohort_size ?? "500"}
                  rawNumber={summary.cohort_size ?? 500}
                  context="Pre-scored cohort"
                  icon={Users}
                  tone="indigo"
                  onClick={() => {
                    if (tier === "all" && !search && ageGroup === "all") {
                      resetAllFilters();
                    } else {
                      resetAllFilters();
                    }
                  }}
                  isActive={tier === "all" && !search && ageGroup === "all"}
                />

                <KpiCard
                  label="High-Risk Flags"
                  value={summary.high_risk ?? "37"}
                  rawNumber={summary.high_risk ?? 37}
                  context={
                    summary.cohort_size
                      ? `${((summary.high_risk / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥20% risk)`
                      : "7.4% of cohort (≥20% risk)"
                  }
                  icon={AlertTriangle}
                  tone="red"
                  accentRed={true}
                  onClick={() => {
                    if (tier === "high") {
                      setTier("all");
                      toast.info("Cleared high risk filter");
                    } else {
                      setTier("high");
                      toast.info("Filtered worklist to High Risk (≥20%)");
                    }
                    setPage(1);
                  }}
                  isActive={tier === "high"}
                />

                <KpiCard
                  label="Polypharmacy Burden"
                  value={summary.polypharmacy ?? "375"}
                  rawNumber={summary.polypharmacy ?? 375}
                  context={
                    summary.cohort_size
                      ? `${((summary.polypharmacy / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥10 meds)`
                      : "75.0% of cohort (≥10 meds)"
                  }
                  icon={Pill}
                  tone="amber"
                  onClick={() => {
                    toast.info("Encounters with 10+ medications are marked with ● Polypharmacy");
                  }}
                />

                <KpiCard
                  label="Observed Readmissions"
                  value={summary.readmissions ?? "64"}
                  rawNumber={summary.readmissions ?? 64}
                  context={
                    summary.cohort_size
                      ? `${((summary.readmissions / summary.cohort_size) * 100).toFixed(1)}% historical rate`
                      : "12.8% historical rate"
                  }
                  icon={TrendingUp}
                  tone="green"
                  onClick={() => {
                    toast.info("Historical cohort baseline readmission rate: 12.8%");
                  }}
                />
              </section>

              {/* Encounter Table Section */}
              <section className="table-section-card">
                {/* Toolbar */}
                <div className="table-toolbar">
                  <div className="toolbar-primary-row">
                    {/* Search Input */}
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
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
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
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable" onClick={() => handleSort("meds")}>
                          <div className="th-inner-flex">
                            <span>Medications</span>
                            {sortField === "meds" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable" onClick={() => handleSort("inpatient")}>
                          <div className="th-inner-flex">
                            <span>Prior acute care</span>
                            {sortField === "inpatient" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th>Care flags</th>
                        <th className="sortable text-right" onClick={() => handleSort("prob")} style={{ textAlign: "right" }}>
                          <div className="th-inner-flex" style={{ justifyContent: "flex-end" }}>
                            <span>Readmission risk</span>
                            <span title="Calibrated 30-day readmission risk predicted by the ensemble (Saved historical score)">
                              <HelpCircle className="w-3 h-3 text-muted" />
                            </span>
                            {sortField === "prob" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
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
                        Array.from({ length: 6 }).map((_, i) => (
                          <tr key={`skeleton-${i}`} className="skeleton-row">
                            <td colSpan={8}>
                              <div className="skeleton-cell-bar" />
                            </td>
                          </tr>
                        ))}

                      {!loadingWorklist &&
                        sortedResults.map((record, idx) => {
                          const normalized = record.tier?.toLowerCase() || "";
                          const tierClass = normalized.startsWith("high") ? "high" : normalized.startsWith("mod") ? "moderate" : "low";
                          const careFlags = record.resources || [];
                          const visibleFlags = careFlags.slice(0, 2);
                          const overflowCount = careFlags.length - 2;

                          return (
                            <motion.tr
                              key={record.enc_id}
                              className={focusedRowIndex === idx ? "row-focused" : ""}
                              onClick={() => {
                                setFocusedRowIndex(idx);
                                openReview(record);
                              }}
                              title="Click to view clinical recommendations in side drawer"
                              initial={idx < 12 ? { opacity: 0, y: 6 } : false}
                              animate={idx < 12 ? { opacity: 1, y: 0 } : false}
                              transition={idx < 12 ? { delay: idx * 0.02, duration: 0.2 } : undefined}
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
                                  <span
                                    className="profile-demographics"
                                    title={`${record.gender || "Unknown"} · ${record.race || "Unknown"}`}
                                  >
                                    {record.gender || "Unknown"} · {record.race || "Unknown"}
                                  </span>
                                </div>
                              </td>

                              <td>
                                <span className="inline-metric tabular-nums">
                                  {record.stay} <small>{Number(record.stay) === 1 ? "day" : "days"}</small>
                                </span>
                              </td>

                              <td>
                                <div className="flex flex-col">
                                  <span className="inline-metric tabular-nums">
                                    {record.meds} <small>{Number(record.meds) === 1 ? "med" : "meds"}</small>
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
                                  {record.inpatient}{" "}
                                  <small>
                                    {Number(record.inpatient) === 1 ? "inpatient" : "inpatient"} · {record.er} ER
                                  </small>
                                </span>
                              </td>

                              <td>
                                <div className="care-flags-cell">
                                  {visibleFlags.map((flag) => (
                                    <span key={flag} className="care-flag-pill">
                                      {flag.includes("Telehealth") ? (
                                        <HeartPulse className="w-3.5 h-3.5 text-red-500" />
                                      ) : flag.includes("PharmD") ? (
                                        <Pill className="w-3.5 h-3.5 text-amber-500" />
                                      ) : (
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
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
                            </motion.tr>
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

                  <div className="flex items-center gap-2">
                    <button
                      className="pagination-btn"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(p - 1, 1))}
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-xs font-semibold px-2 tabular-nums">
                      Page {page} of {Math.max(1, worklist.pages)}
                    </span>
                    <button
                      className="pagination-btn"
                      disabled={page >= worklist.pages}
                      onClick={() => setPage((p) => p + 1)}
                      aria-label="Next page"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </section>
            </>
          )}

          {/* ===================================================================
              PAGE 2: BEDSIDE RISK CALCULATOR
              ================================================================== */}
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
                      <span className="text-xs text-muted tabular-nums">
                        {draft?.time_in_hospital || 1} {Number(draft?.time_in_hospital) === 1 ? "day" : "days"}
                      </span>
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
                      <span className="text-xs text-muted tabular-nums">
                        {draft?.num_medications || 0} {Number(draft?.num_medications) === 1 ? "med" : "meds"}
                      </span>
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
                  <motion.div
                    className="flex flex-col gap-4"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
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
                              <motion.div
                                className="driver-fill"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(100, Math.max(12, Math.abs(f.impact) * 200))}%` }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                              />
                            </div>
                            <span className="text-right text-xs text-muted tabular-nums">
                              {f.impact > 0 ? "+" : ""}{Number(f.impact).toFixed(1)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="p-3 bg-subtle border border-color rounded-control text-xs text-muted">
                      <strong>Research note:</strong> Generated by the Calibrated Ensemble (LightGBM + XGBoost + CatBoost). For research decision-support only.
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          )}

          {/* ===================================================================
              PAGE 3: MODEL GOVERNANCE & ETHICAL AUDITS
              =================================================================== */}
          {view === "governance" && (
            <div className="governance-layout-grid">
              {/* Left Column: Benchmarks & Architecture */}
              <div className="flex flex-col gap-6">
                {/* Ensemble Architecture Card */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Ensemble Architecture</h2>
                      <p>Triple-gradient boosted decision trees with isotonic probability calibration.</p>
                    </div>
                    <span className="status-badge-chip verified">
                      <Check className="w-3.5 h-3.5" />
                      Production Champion
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="metric-callout-box">
                      <span className="metric-box-label">Discrimination (AUC-ROC)</span>
                      <span className="metric-box-val tabular-nums">0.684</span>
                      <small className="text-xs text-muted">Validation cohort</small>
                    </div>
                    <div className="metric-callout-box">
                      <span className="metric-box-label">Brier Calibration Score</span>
                      <span className="metric-box-val tabular-nums">0.093</span>
                      <small className="text-xs text-muted">Isotonically aligned</small>
                    </div>
                    <div className="metric-callout-box">
                      <span className="metric-box-label">Clinical High-Risk Cutoff</span>
                      <span className="metric-box-val tabular-nums">≥ 20.0%</span>
                      <small className="text-xs text-muted">Optimized sensitivity</small>
                    </div>
                  </div>

                  <p className="text-sm text-secondary">
                    The platform uses a soft-voting ensemble comprising <strong>LightGBM</strong>, <strong>XGBoost</strong>, and <strong>CatBoost</strong>. Each learner outputs raw margins mapped to well-calibrated posterior probabilities, ensuring the predicted score reliably matches real-world clinical readmission frequencies.
                  </p>
                </motion.div>

                {/* Candidate Models Benchmark Comparison */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Candidate Benchmark Comparison</h2>
                      <p>Evaluated across 6 clinical model variations on identical test holdouts.</p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-3">
                    {(governance?.models || []).map((m) => {
                      const isChampion = m.Model === governance?.selected_model;
                      const auc = Number(m["AUC-ROC"]) || 0;
                      const recall = Number(m.Recall) || 0;

                      return (
                        <div
                          key={m.Model}
                          className={`benchmark-card-row ${isChampion ? "champion" : ""}`}
                        >
                          <div className="model-name-group">
                            <strong>{m.Model}</strong>
                            <span className="model-threshold-sub">
                              Cutoff: {m.Threshold != null ? prettyPercent(m.Threshold) : "0.50"}
                            </span>
                          </div>

                          <div className="dual-metric-bar">
                            <div className="dual-metric-header">
                              <span>AUC-ROC</span>
                              <b className="tabular-nums">{auc.toFixed(3)}</b>
                            </div>
                            <div className="dual-bar-track">
                              <motion.div
                                className="dual-bar-fill auc"
                                initial={{ width: 0 }}
                                whileInView={{ width: `${auc * 100}%` }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.6 }}
                              />
                            </div>
                          </div>

                          <div className="dual-metric-bar">
                            <div className="dual-metric-header">
                              <span>Sensitivity / Recall</span>
                              <b className="tabular-nums">{recall.toFixed(3)}</b>
                            </div>
                            <div className="dual-bar-track">
                              <motion.div
                                className="dual-bar-fill recall"
                                initial={{ width: 0 }}
                                whileInView={{ width: `${recall * 100}%` }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.6 }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              </div>

              {/* Right Column: Demographic Parity & Compliance */}
              <div className="flex flex-col gap-6">
                {/* Algorithmic Fairness Audit */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Demographic Fairness Audits</h2>
                      <p>Equal Opportunity & True Positive Rate parity across protected groups.</p>
                    </div>
                  </div>

                  <div className="fairness-card-list">
                    <div className="fairness-attribute-row">
                      <div className="flex flex-col">
                        <strong>Race & Ethnicity Parity</strong>
                        <small className="text-xs text-muted">Max True Positive Rate disparity</small>
                      </div>
                      <div className="fairness-disparity-metric">
                        <div className="disparity-val-col">
                          <small>Ensemble Gap</small>
                          <b className="mitigated tabular-nums">0.052 (5.2 pp)</b>
                        </div>
                        <span className="improvement-badge-pill">
                          <TrendingDown className="w-3 h-3" />
                          -44% disparity
                        </span>
                      </div>
                    </div>

                    <div className="fairness-attribute-row">
                      <div className="flex flex-col">
                        <strong>Sex & Gender Parity</strong>
                        <small className="text-xs text-muted">Male vs. Female detection balance</small>
                      </div>
                      <div className="fairness-disparity-metric">
                        <div className="disparity-val-col">
                          <small>Ensemble Gap</small>
                          <b className="mitigated tabular-nums">0.021 (2.1 pp)</b>
                        </div>
                        <span className="improvement-badge-pill">
                          <TrendingDown className="w-3 h-3" />
                          -58% disparity
                        </span>
                      </div>
                    </div>

                    <div className="fairness-attribute-row">
                      <div className="flex flex-col">
                        <strong>Age Band Sensitivity</strong>
                        <small className="text-xs text-muted">Detection consistency across older adults</small>
                      </div>
                      <div className="fairness-disparity-metric">
                        <div className="disparity-val-col">
                          <small>Ensemble Gap</small>
                          <b className="mitigated tabular-nums">0.064 (6.4 pp)</b>
                        </div>
                        <span className="improvement-badge-pill">
                          <TrendingDown className="w-3 h-3" />
                          -32% disparity
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Clinical Justification & Safety Notes */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Intended Use & Clinical Scope</h2>
                      <p>Regulatory & algorithmic guardrails under CMS HRRP guidelines.</p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-3 text-sm text-secondary">
                    <div className="p-3 bg-subtle border border-color rounded-control">
                      <strong className="block text-primary text-xs uppercase mb-1">Intended Operator</strong>
                      <span>Hospital Discharge Planners, Nurse Navigators, and Care Coordinators.</span>
                    </div>

                    <div className="p-3 bg-subtle border border-color rounded-control">
                      <strong className="block text-primary text-xs uppercase mb-1">Human-in-the-Loop Requirement</strong>
                      <span>The predicted readmission risk must accompany bedside clinical assessments. The model provides assistive probabilistic signals, not autonomous clinical directives.</span>
                    </div>

                    <div className="p-3 bg-subtle border border-color rounded-control">
                      <strong className="block text-primary text-xs uppercase mb-1">Data Provenance</strong>
                      <span>Calibrated on 500 de-identified diabetic inpatient encounters from the UCI Machine Learning Repository. All protected health identifiers are stripped.</span>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* -----------------------------------------------------------------------
          MOBILE BOTTOM NAV
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
          RIGHT-SIDE SLIDE-IN DRAWER: ENCOUNTER CLINICAL CONSULTATION
          ----------------------------------------------------------------------- */}
      <AnimatePresence>
        {reviewRecord && (
          <>
            <motion.div
              className="drawer-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setReviewRecord(null)}
            />
            <motion.aside
              className="drawer-panel"
              initial={{ x: "100%", opacity: 0.6 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={motionTokens.springs.drawer}
              aria-label="Encounter Consultation Details"
            >
              {/* Drawer Header */}
              <div className="drawer-header">
                <div className="drawer-header-info">
                  <span className="drawer-encounter-sub">Clinical Consultation</span>
                  <span className="drawer-encounter-id">{reviewRecord.enc_id}</span>
                  <span className="drawer-encounter-sub">
                    {reviewRecord.age} · {reviewRecord.gender} · {reviewRecord.race}
                  </span>
                </div>
                <button
                  className="drawer-close-btn"
                  onClick={() => setReviewRecord(null)}
                  aria-label="Close drawer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Drawer Body */}
              <div className="drawer-body">
                {/* Gauge Summary Box */}
                <div className="drawer-gauge-card">
                  <div className="drawer-gauge-left">
                    <span className="drawer-gauge-meta">Calibrated 30-Day Readmission Risk</span>
                    <span
                      className={`drawer-gauge-pct tabular-nums ${
                        reviewRecord.tier?.toLowerCase().startsWith("high")
                          ? "text-red-600 dark:text-red-400"
                          : reviewRecord.tier?.toLowerCase().startsWith("mod")
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-emerald-600 dark:text-emerald-400"
                      }`}
                    >
                      <AnimatedNumber value={reviewRecord.prob * 100} format={(v) => `${v.toFixed(1)}%`} />
                    </span>
                    <RiskBadge tier={reviewRecord.tier} />
                  </div>
                  <RiskGauge probability={reviewRecord.prob} tier={reviewRecord.tier} />
                </div>

                {/* Clinical Facts Grid */}
                <div className="drawer-section">
                  <span className="drawer-section-title">Encounter Clinical Overview</span>
                  <div className="clinical-facts-grid">
                    <div className="fact-tile">
                      <small>Hospital Stay</small>
                      <strong className="tabular-nums">
                        {reviewRecord.stay} {reviewRecord.stay === 1 ? "day" : "days"}
                      </strong>
                    </div>
                    <div className="fact-tile">
                      <small>Medications</small>
                      <strong className="tabular-nums">
                        {reviewRecord.meds} {reviewRecord.meds === 1 ? "med" : "meds"}
                      </strong>
                    </div>
                    <div className="fact-tile">
                      <small>Prior Inpatient</small>
                      <strong className="tabular-nums">
                        {reviewRecord.inpatient} {reviewRecord.inpatient === 1 ? "visit" : "visits"}
                      </strong>
                    </div>
                    <div className="fact-tile">
                      <small>ER Visits</small>
                      <strong className="tabular-nums">
                        {reviewRecord.er} {reviewRecord.er === 1 ? "visit" : "visits"}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* Risk Drivers Growth Bars */}
                <div className="drawer-section">
                  <span className="drawer-section-title">Encounter Risk Drivers</span>
                  <div className="flex flex-col gap-3">
                    <div className="drawer-driver-row">
                      <div className="drawer-driver-header">
                        <span className="drawer-driver-name">Active Medications Burden</span>
                        <span className="drawer-driver-val">
                          {reviewRecord.meds} meds {Number(reviewRecord.meds) >= 10 ? "(Polypharmacy)" : ""}
                        </span>
                      </div>
                      <div className="drawer-driver-track">
                        <motion.div
                          className="drawer-driver-fill"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(100, (reviewRecord.meds / 30) * 100)}%` }}
                          transition={{ duration: 0.6, delay: 0.1 }}
                          style={{
                            background:
                              Number(reviewRecord.meds) >= 10 ? "var(--risk-med-bar)" : "var(--brand-indigo)",
                          }}
                        />
                      </div>
                    </div>

                    <div className="drawer-driver-row">
                      <div className="drawer-driver-header">
                        <span className="drawer-driver-name">Prior Acute Care Frequency</span>
                        <span className="drawer-driver-val">
                          {reviewRecord.inpatient} inpatient · {reviewRecord.er} ER
                        </span>
                      </div>
                      <div className="drawer-driver-track">
                        <motion.div
                          className="drawer-driver-fill"
                          initial={{ width: 0 }}
                          animate={{
                            width: `${Math.min(100, ((reviewRecord.inpatient * 2 + reviewRecord.er) / 8) * 100)}%`,
                          }}
                          transition={{ duration: 0.6, delay: 0.2 }}
                          style={{
                            background:
                              Number(reviewRecord.inpatient) >= 2
                                ? "var(--risk-high-bar)"
                                : "var(--brand-indigo)",
                          }}
                        />
                      </div>
                    </div>

                    <div className="drawer-driver-row">
                      <div className="drawer-driver-header">
                        <span className="drawer-driver-name">Length of Inpatient Stay</span>
                        <span className="drawer-driver-val">{reviewRecord.stay} days</span>
                      </div>
                      <div className="drawer-driver-track">
                        <motion.div
                          className="drawer-driver-fill"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(100, (reviewRecord.stay / 14) * 100)}%` }}
                          transition={{ duration: 0.6, delay: 0.3 }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recommended Care Transition Protocols Checklist */}
                <div className="drawer-section">
                  <span className="drawer-section-title">Recommended Transition Protocols</span>
                  {reviewLoading ? (
                    <div className="p-4 text-center text-sm text-muted flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
                      <span>Synthesizing care transition protocols…</span>
                    </div>
                  ) : (
                    <div className="drawer-care-actions-list">
                      {[
                        {
                          id: "pharm",
                          label: "Pharmacist medication reconciliation",
                          desc: "Review high-risk drug interactions and verify discharge prescriptions.",
                        },
                        {
                          id: "tele",
                          label: "48-hour telehealth follow-up check-in",
                          desc: "Confirm outpatient appointment and symptom stability within 48h.",
                        },
                        {
                          id: "cdces",
                          label: "Certified Diabetes Educator (CDCES) consult",
                          desc: "Ensure glycemic self-management plan and outpatient insulin protocol.",
                        },
                        {
                          id: "nurse",
                          label: "Home health nurse transitional visit",
                          desc: "Bedside discharge nurse confirms home readiness and caregiver support.",
                        },
                      ].map((action, i) => (
                        <DrawerCareActionChip key={action.id} action={action} index={i} />
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Drawer Footer Actions */}
              <div className="drawer-footer">
                <button
                  className="secondary-action-btn"
                  onClick={() => {
                    navigator.clipboard?.writeText(reviewRecord.enc_id);
                    toast.success(`Copied ${reviewRecord.enc_id} to clipboard`);
                  }}
                >
                  <Copy className="w-4 h-4" />
                  <span>Copy ID</span>
                </button>

                <button
                  className="primary-action-btn"
                  onClick={() => {
                    setSelectedId(reviewRecord.enc_id);
                    setView("calculator");
                    setReviewRecord(null);
                    toast.info(`Loaded ${reviewRecord.enc_id} in Bedside Calculator`);
                  }}
                >
                  <span>Adjust in Calculator</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* -----------------------------------------------------------------------
          COMMAND PALETTE (cmdk - Raycast / Linear Style)
          ----------------------------------------------------------------------- */}
      <Command.Dialog
        open={openPalette}
        onOpenChange={setOpenPalette}
        label="ClinicalAI Global Command Menu"
        className="cmdk-dialog"
      >
        <div className="cmdk-header">
          <Search className="w-4 h-4 text-muted" />
          <Command.Input
            className="cmdk-input"
            placeholder="Search encounters, change views, apply risk filters, or toggle settings..."
          />
          <kbd className="cmdk-kbd">ESC</kbd>
        </div>

        <Command.List className="cmdk-list">
          <Command.Empty className="cmdk-empty">No matching results found.</Command.Empty>

          <Command.Group heading="Navigation" className="cmdk-group">
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setView("worklist");
                setOpenPalette(false);
                toast.info("Navigated to Discharge Worklist");
              }}
            >
              <FileSpreadsheet className="w-4 h-4 text-indigo-500" />
              <span>Discharge Worklist</span>
              <span className="cmdk-shortcut">W</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setView("calculator");
                setOpenPalette(false);
                toast.info("Navigated to Bedside Calculator");
              }}
            >
              <Activity className="w-4 h-4 text-indigo-500" />
              <span>Bedside Risk Calculator</span>
              <span className="cmdk-shortcut">C</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setView("governance");
                setOpenPalette(false);
                toast.info("Navigated to Model Governance");
              }}
            >
              <ShieldCheck className="w-4 h-4 text-indigo-500" />
              <span>Model Governance & Fairness</span>
              <span className="cmdk-shortcut">G</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Risk Filters" className="cmdk-group">
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setTier("high");
                setPage(1);
                setView("worklist");
                setOpenPalette(false);
                toast.info("Filtered worklist to High Risk (≥20%)");
              }}
            >
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span>Show High Risk Encounters (≥20%)</span>
              <span className="cmdk-shortcut">H</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setTier("moderate");
                setPage(1);
                setView("worklist");
                setOpenPalette(false);
                toast.info("Filtered worklist to Moderate Risk (12–20%)");
              }}
            >
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <span>Show Moderate Risk Encounters (12–20%)</span>
              <span className="cmdk-shortcut">M</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                resetAllFilters();
                setOpenPalette(false);
              }}
            >
              <RotateCcw className="w-4 h-4 text-muted" />
              <span>Reset All Worklist Filters</span>
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Preferences & Actions" className="cmdk-group">
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                toggleDarkMode();
                setOpenPalette(false);
              }}
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-500" />}
              <span>Toggle Theme ({darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"})</span>
              <span className="cmdk-shortcut">T</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setReduceMotion((r) => {
                  const next = !r;
                  localStorage.setItem("clinicalai-reduced-motion", String(next));
                  toast.info(`Reduced motion ${next ? "enabled" : "disabled"}`);
                  return next;
                });
                setOpenPalette(false);
              }}
            >
              <Sparkles className="w-4 h-4 text-violet-500" />
              <span>Toggle Reduced Motion ({reduceMotion ? "Disable" : "Enable"})</span>
              <span className="cmdk-shortcut">R</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                handleExportCSV();
                setOpenPalette(false);
              }}
            >
              <Download className="w-4 h-4 text-emerald-500" />
              <span>Export Worklist to CSV</span>
              <span className="cmdk-shortcut">E</span>
            </Command.Item>
          </Command.Group>

          {!!worklist.results?.length && (
            <Command.Group heading="Jump to Encounter" className="cmdk-group">
              {worklist.results.slice(0, 15).map((enc) => (
                <Command.Item
                  key={enc.enc_id}
                  className="cmdk-item"
                  onSelect={() => {
                    openReview(enc);
                    setOpenPalette(false);
                  }}
                >
                  <User className="w-4 h-4 text-indigo-500" />
                  <span>
                    {enc.enc_id} — {enc.age} {enc.gender} · {prettyPercent(enc.prob)} ({enc.tier})
                  </span>
                </Command.Item>
              ))}
            </Command.Group>
          )}
        </Command.List>
      </Command.Dialog>

      {/* -----------------------------------------------------------------------
          MODAL: HELP & DOCUMENTATION DIALOG
          ----------------------------------------------------------------------- */}
      {showHelpModal && (
        <div className="modal-backdrop-overlay" onClick={() => setShowHelpModal(false)}>
          <div className="modal-dialog-window" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-top">
              <div className="modal-patient-headline">
                <span className="text-xs font-bold text-muted uppercase tracking-wider block">
                  Platform Documentation & Shortcuts
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

              {/* Keyboard Shortcuts Documentation */}
              <div className="p-3 bg-subtle border border-color rounded-control">
                <strong className="block text-primary text-xs uppercase mb-2">Keyboard Shortcuts</strong>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span>Command palette</span>
                    <kbd>⌘K / Ctrl+K</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Focus search</span>
                    <kbd>/</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Next / Prev row</span>
                    <kbd>j / k</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Open drawer</span>
                    <kbd>Enter</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Dismiss modal/drawer</span>
                    <kbd>Esc</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Toggle theme</span>
                    <kbd>⌘K → T</kbd>
                  </div>
                </div>
              </div>

              {/* Motion Preference Toggle */}
              <div className="flex items-center justify-between p-3 bg-subtle border border-color rounded-control">
                <div>
                  <strong className="block text-primary text-xs uppercase">Motion Preference</strong>
                  <span className="text-xs text-secondary">Reduce movement and use simple fades</span>
                </div>
                <button
                  type="button"
                  className={`filter-chip ${reduceMotion ? "bg-indigo-600 text-white" : ""}`}
                  onClick={() => {
                    setReduceMotion((r) => {
                      const next = !r;
                      localStorage.setItem("clinicalai-reduced-motion", String(next));
                      toast.info(`Reduced motion ${next ? "enabled" : "disabled"}`);
                      return next;
                    });
                  }}
                >
                  {reduceMotion ? "Reduced" : "Standard"}
                </button>
              </div>
            </div>

            <button className="secondary-action-btn w-full justify-center" onClick={() => setShowHelpModal(false)}>
              Got it
            </button>
          </div>
        </div>
      )}

      {/* Global Sonner Toast Notifications */}
      <Toaster position="bottom-right" richColors theme={darkMode ? "dark" : "light"} closeButton />
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
