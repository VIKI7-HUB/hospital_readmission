import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { createPortal } from "react-dom";
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
  Database,
  Download,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  FileText,
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
  Scale,
  Search,
  ShieldCheck,
  Sliders,
  Sparkles,
  Stethoscope,
  Sun,
  Target,
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

function getCareFlagConfig(flag) {
  const str = String(flag || "").trim();
  const lower = str.toLowerCase();
  if (lower.includes("pharm")) {
    return { label: "Pharmacist", icon: Pill, color: "text-amber-500" };
  }
  if (lower.includes("telehealth")) {
    return { label: "Telehealth 48h", icon: HeartPulse, color: "text-red-500" };
  }
  if (lower.includes("cdces") || lower.includes("educat") || lower.includes("diabetes ed")) {
    return { label: "CDCES", icon: Activity, color: "text-indigo-500" };
  }
  if (lower.includes("home") || lower.includes("nurse")) {
    return { label: "Home nurse", icon: User, color: "text-teal-500" };
  }
  if (lower.includes("coord")) {
    return { label: "Care coord", icon: CheckCircle2, color: "text-emerald-500" };
  }
  return { label: str || "Routine", icon: CheckCircle2, color: "text-emerald-500" };
}

function KpiMiniCohortDist({ lowPct = 72.2, elevatedPct = 22.8, highPct = 5.0 }) {
  return (
    <div>
      <div
        className="kpi-mini-dist-bar"
        title={`Cohort risk distribution: ${lowPct.toFixed(1)}% Low (<12%), ${elevatedPct.toFixed(1)}% Elevated (12–20%), ${highPct.toFixed(1)}% High (≥20%)`}
      >
        <div className="kpi-dist-seg low" style={{ width: `${lowPct}%` }} />
        <div className="kpi-dist-seg elevated" style={{ width: `${elevatedPct}%` }} />
        <div className="kpi-dist-seg high" style={{ width: `${highPct}%` }} />
      </div>
      <div className="kpi-dist-labels">
        <span>{Math.round(lowPct)}% Low</span>
        <span>{Math.round(elevatedPct)}% Elev</span>
        <span>{Math.round(highPct)}% High</span>
      </div>
    </div>
  );
}

function KpiProportionBar({ percentage = 0, tone = "indigo", title = "" }) {
  const clamped = Math.min(100, Math.max(0, percentage));
  return (
    <div className="kpi-proportion-track" title={title || `${clamped.toFixed(1)}%`}>
      <div className={`kpi-proportion-fill ${tone}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}

function RiskBadge({ tier }) {
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high")
    ? "high"
    : normalized.startsWith("elevated") || normalized.startsWith("mod")
    ? "elevated"
    : "low";
  return (
    <span className={`risk-badge-pill ${kind}`}>
      <i aria-hidden="true" />
      {tier || "Unscored"}
    </span>
  );
}

function RiskBar({ probability, tier }) {
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high")
    ? "high"
    : normalized.startsWith("elevated") || normalized.startsWith("mod")
    ? "elevated"
    : "low";
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

function SharedTooltip({ tooltip }) {
  if (!tooltip || !tooltip.targetRect) return null;
  const { text, targetRect, placement = "top" } = tooltip;

  const isTop = placement === "top" && targetRect.top > 70;
  const leftPos = Math.max(150, Math.min(window.innerWidth - 150, targetRect.left + targetRect.width / 2));

  const tooltipStyle = {
    position: "fixed",
    left: `${leftPos}px`,
    top: isTop ? `${targetRect.top - 8}px` : `${targetRect.bottom + 8}px`,
    transform: isTop ? "translate(-50%, -100%)" : "translate(-50%, 0)",
    zIndex: 99999,
    pointerEvents: "none",
  };

  return createPortal(
    <div
      className="clinical-shared-tooltip"
      style={tooltipStyle}
      role="tooltip"
    >
      <div className="clinical-shared-tooltip-content">
        {text}
      </div>
      <div className={`clinical-shared-tooltip-arrow ${isTop ? "arrow-bottom" : "arrow-top"}`} />
    </div>,
    document.body
  );
}

function KpiCard({
  label,
  value,
  context,
  secondLine = null,
  miniVisual = null,
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
      title={onClick ? "Click to toggle filter (click to clear)" : undefined}
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

      {miniVisual}

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

      {secondLine && (
        <div className="kpi-second-line">
          {secondLine}
        </div>
      )}
    </motion.div>
  );
}

function RiskGauge({ probability, tier }) {
  const pct = Math.min(100, Math.max(0, (Number(probability) || 0) * 100));
  const normalized = tier?.toLowerCase() || "";
  const kind = normalized.startsWith("high")
    ? "high"
    : normalized.startsWith("elevated") || normalized.startsWith("mod")
    ? "elevated"
    : "low";
  const strokeColor =
    kind === "high"
      ? "var(--risk-high-bar)"
      : kind === "elevated"
      ? "var(--risk-med-bar)"
      : "var(--risk-low-bar)";

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
  const [view, setView] = useState(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash.replace("#", "");
      if (["worklist", "calculator", "governance"].includes(hash)) return hash;
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (["worklist", "calculator", "governance"].includes(tab)) return tab;
    }
    return "worklist";
  });

  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (["worklist", "calculator", "governance"].includes(hash)) {
        setView(hash);
      }
    };
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

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

  // Responsive column detection for Care Flags pill count
  const [isWideFlagsCol, setIsWideFlagsCol] = useState(false);
  const roRef = useRef(null);
  const careFlagsThCallback = useCallback((node) => {
    if (roRef.current) {
      roRef.current.disconnect();
      roRef.current = null;
    }
    if (node) {
      roRef.current = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const width = entry.contentRect.width;
          setIsWideFlagsCol(width >= 230);
        }
      });
      roRef.current.observe(node);
    }
  }, []);

  // Single shared tooltip state
  const [sharedTooltip, setSharedTooltip] = useState(null);
  const tooltipTimerRef = useRef(null);

  const showTooltip = useCallback((text, targetElement, placement = "top") => {
    if (tooltipTimerRef.current) {
      clearTimeout(tooltipTimerRef.current);
    }
    tooltipTimerRef.current = setTimeout(() => {
      if (targetElement) {
        const rect = targetElement.getBoundingClientRect();
        setSharedTooltip({ text, targetRect: rect, placement });
      }
    }, 300);
  }, []);

  const hideTooltip = useCallback(() => {
    if (tooltipTimerRef.current) {
      clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = null;
    }
    setSharedTooltip(null);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        hideTooltip();
      }
    };
    const handleScroll = () => {
      if (tooltipTimerRef.current) {
        clearTimeout(tooltipTimerRef.current);
      }
      setSharedTooltip(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [hideTooltip]);

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

  // Model Governance benchmark sorting & metrics
  const [govSortField, setGovSortField] = useState("AUC-ROC");
  const [govSortOrder, setGovSortOrder] = useState("desc");
  const [govCutoffView, setGovCutoffView] = useState("common"); // "common" or "tuned"
  const [govThresholdSlider, setGovThresholdSlider] = useState(0.12);
  const [featImpView, setFeatImpView] = useState("odds_ratios"); // "odds_ratios" or "tree"

  const handleGovSort = (field) => {
    if (govSortField === field) {
      setGovSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setGovSortField(field);
      setGovSortOrder(field === "Model" ? "asc" : "desc");
    }
  };

  const getModelSensitivity = useCallback((m) => {
    if (!m) return null;
    const raw = m["Recall (Sensitivity)"] ?? m.Sensitivity ?? m.Recall;
    if (raw !== undefined && raw !== null && !isNaN(Number(raw))) {
      const num = Number(raw);
      if (num > 0) return num;
    }
    return null;
  }, []);

  const championModel = useMemo(() => {
    const list = governance?.models || [];
    return (
      list.find((m) => m.Model === (governance?.selected_model || "Calibrated Ensemble")) ||
      list.find((m) => m.Model.includes("Ensemble")) ||
      list[0] ||
      null
    );
  }, [governance]);

  const championAuc = championModel ? (Number(championModel["AUC-ROC"]) || 0.653).toFixed(3) : "0.653";
  const championBrier = championModel ? (Number(championModel["Brier Score"]) || 0.0976).toFixed(4) : "0.0976";
  const championCutoff = (championModel?.["Decision Threshold"] ?? championModel?.Threshold ?? championModel?.Cutoff) != null
    ? `≥ ${(Number(championModel["Decision Threshold"] ?? championModel?.Threshold ?? championModel?.Cutoff) * 100).toFixed(1)}%`
    : "≥ 12.0%";

  const currentGovModels = useMemo(() => {
    if (govCutoffView === "tuned") {
      return governance?.models_tuned_cutoff || governance?.models || [];
    }
    return governance?.models_common_cutoff || governance?.models || [];
  }, [governance, govCutoffView]);

  const sortedGovModels = useMemo(() => {
    const list = [...currentGovModels];
    return list.sort((a, b) => {
      let aVal = a[govSortField];
      let bVal = b[govSortField];

      if (govSortField === "Model") {
        return govSortOrder === "asc"
          ? String(a.Model).localeCompare(String(b.Model))
          : String(b.Model).localeCompare(String(a.Model));
      }
      if (govSortField === "Recall" || govSortField === "Sensitivity") {
        aVal = a["Recall (Sensitivity)"] ?? a.Recall ?? a.Sensitivity;
        bVal = b["Recall (Sensitivity)"] ?? b.Recall ?? b.Sensitivity;
      }

      const numA = aVal != null && !isNaN(Number(aVal)) ? Number(aVal) : -9999;
      const numB = bVal != null && !isNaN(Number(bVal)) ? Number(bVal) : -9999;
      return govSortOrder === "asc" ? numA - numB : numB - numA;
    });
  }, [currentGovModels, govSortField, govSortOrder]);

  const activeTradeoff = useMemo(() => {
    const list = governance?.threshold_tradeoff || [];
    if (!list.length) {
      return {
        cutoff: 0.12,
        tp: 1304,
        fp: 6201,
        tn: 11406,
        fn: 959,
        sensitivity: 57.6,
        specificity: 64.8,
        precision: 17.4,
        flag_rate: 37.8,
      };
    }
    const rounded = Math.round(govThresholdSlider * 100) / 100;
    const match = list.find((item) => Math.abs(item.cutoff - rounded) < 0.005);
    return match || list.find((item) => Math.abs(item.cutoff - 0.12) < 0.005) || list[0];
  }, [governance?.threshold_tradeoff, govThresholdSlider]);

  const fairnessCards = useMemo(() => {
    const fairnessData = governance?.fairness || {};
    const demographicAudits = fairnessData.demographic_audits || {};

    const raceAudit = demographicAudits.race_clean || {
      attribute: "race_clean",
      headline_comparison: "Caucasian vs. African American (groups with ≥100 readmissions)",
      headline_gap_point_pp: 4.98,
      headline_gap_ci_str: "[-0.4 pp – 10.4 pp]",
      mitigated_gap_point_pp: 4.23,
      mitigated_gap_ci_str: "[-1.1 pp – 9.6 pp]",
      status_assessment: "95% CI [-0.4 pp – 10.4 pp] spans internal 5.0 pp threshold",
      subgroups: [
        { subgroup: "Caucasian", sample_size_n: 14874, readmitted_cases_k: 1735, is_small_sample: false, unmitigated_tpr_pct: 58.67, unmitigated_ci_95_str: "56.3%–61.0%", mitigated_tpr_pct: 57.93, mitigated_ci_95_str: "55.6%–60.2%" },
        { subgroup: "AfricanAmerican", sample_size_n: 3716, readmitted_cases_k: 406, is_small_sample: false, unmitigated_tpr_pct: 53.69, unmitigated_ci_95_str: "48.8%–58.5%", mitigated_tpr_pct: 53.69, mitigated_ci_95_str: "48.8%–58.5%" },
        { subgroup: "Hispanic", sample_size_n: 405, readmitted_cases_k: 45, is_small_sample: true, unmitigated_tpr_pct: 60.00, unmitigated_ci_95_str: "45.5%–73.0%", mitigated_tpr_pct: 60.00, mitigated_ci_95_str: "45.5%–73.0%" },
        { subgroup: "Other", sample_size_n: 308, readmitted_cases_k: 25, is_small_sample: true, unmitigated_tpr_pct: 60.00, unmitigated_ci_95_str: "40.7%–76.6%", mitigated_tpr_pct: 60.00, mitigated_ci_95_str: "40.7%–76.6%" },
        { subgroup: "Asian", sample_size_n: 124, readmitted_cases_k: 13, is_small_sample: true, unmitigated_tpr_pct: 38.46, unmitigated_ci_95_str: "17.7%–64.5%", mitigated_tpr_pct: 38.46, mitigated_ci_95_str: "17.7%–64.5%" },
        { subgroup: "Other/Unknown", sample_size_n: 443, readmitted_cases_k: 39, is_small_sample: true, unmitigated_tpr_pct: 53.85, unmitigated_ci_95_str: "38.6%–68.4%", mitigated_tpr_pct: 53.85, mitigated_ci_95_str: "38.6%–68.4%" },
      ],
    };

    const genderAudit = demographicAudits.gender_clean || {
      attribute: "gender_clean",
      headline_comparison: "Female vs. Male (groups with ≥100 readmissions)",
      headline_gap_point_pp: 3.32,
      headline_gap_ci_str: "[-1.0 pp – 7.4 pp]",
      mitigated_gap_point_pp: 3.32,
      mitigated_gap_ci_str: "[-1.0 pp – 7.4 pp]",
      status_assessment: "Gap not distinguishable from zero (95% CI includes 0)",
      subgroups: [
        { subgroup: "Female", sample_size_n: 10615, readmitted_cases_k: 1238, is_small_sample: false, unmitigated_tpr_pct: 59.13, unmitigated_ci_95_str: "56.4%–61.8%", mitigated_tpr_pct: 58.48, mitigated_ci_95_str: "55.7%–61.2%" },
        { subgroup: "Male", sample_size_n: 9254, readmitted_cases_k: 1025, is_small_sample: false, unmitigated_tpr_pct: 55.80, unmitigated_ci_95_str: "52.7%–58.8%", mitigated_tpr_pct: 55.32, mitigated_ci_95_str: "52.3%–58.3%" },
        { subgroup: "Other/Unknown", sample_size_n: 1, readmitted_cases_k: 0, is_small_sample: true, unmitigated_tpr_pct: 0.0, unmitigated_ci_95_str: "0.0%–0.0%", mitigated_tpr_pct: 0.0, mitigated_ci_95_str: "0.0%–0.0%" },
      ],
    };

    const ageAudit = demographicAudits.age_group || {
      attribute: "age_group",
      headline_comparison: "60+ Years vs. 30-60 Years (groups with ≥100 readmissions)",
      headline_gap_point_pp: 3.93,
      headline_gap_ci_str: "[-0.9 pp – 8.6 pp]",
      mitigated_gap_point_pp: 3.93,
      mitigated_gap_ci_str: "[-0.9 pp – 8.6 pp]",
      status_assessment: "Gap not distinguishable from zero (95% CI includes 0)",
      subgroups: [
        { subgroup: "60+ Years", sample_size_n: 13227, readmitted_cases_k: 1605, is_small_sample: false, unmitigated_tpr_pct: 58.32, unmitigated_ci_95_str: "55.9%–60.7%", mitigated_tpr_pct: 57.76, mitigated_ci_95_str: "55.3%–60.2%" },
        { subgroup: "30-60 Years", sample_size_n: 6131, readmitted_cases_k: 592, is_small_sample: false, unmitigated_tpr_pct: 54.39, unmitigated_ci_95_str: "50.4%–58.4%", mitigated_tpr_pct: 53.89, mitigated_ci_95_str: "49.9%–57.9%" },
        { subgroup: "<30 Years", sample_size_n: 512, readmitted_cases_k: 66, is_small_sample: true, unmitigated_tpr_pct: 69.70, unmitigated_ci_95_str: "57.8%–79.4%", mitigated_tpr_pct: 68.18, mitigated_ci_95_str: "56.2%–78.2%" },
      ],
    };

    const formatCard = (audit, id, title, desc, reductionText) => {
      const isSpanThreshold = audit.status_assessment?.includes("spans");
      return {
        id,
        title,
        desc,
        headlineComparison: audit.headline_comparison,
        gap: `${Number(audit.headline_gap_point_pp).toFixed(2)} pp`,
        gapCi: audit.headline_gap_ci_str,
        mitigatedGap: audit.mitigated_gap_point_pp != null ? `${Number(audit.mitigated_gap_point_pp).toFixed(2)} pp` : null,
        mitigatedGapCi: audit.mitigated_gap_ci_str,
        status: audit.status_assessment,
        statusTone: isSpanThreshold ? "warning" : "neutral",
        reductionBadge: reductionText,
        subgroups: (audit.subgroups || []).map((sg) => ({
          name: sg.subgroup,
          n: sg.sample_size_n,
          k: sg.readmitted_cases_k,
          isSmall: Boolean(sg.is_small_sample),
          tpr: sg.unmitigated_tpr_pct,
          ci: sg.unmitigated_ci_95_str,
          mitTpr: sg.mitigated_tpr_pct,
          mitCi: sg.mitigated_ci_95_str,
        })),
      };
    };

    return [
      formatCard(
        raceAudit,
        "race",
        "Race & Ethnicity Parity",
        "Measures True Positive Rate consistency across racial and ethnic cohorts to ensure equitable high-risk identification.",
        "Disparity narrowed 15% in validation analysis (4.98 pp → 4.23 pp)"
      ),
      formatCard(
        genderAudit,
        "gender",
        "Sex & Gender Parity",
        "Compares readmission sensitivity between female and male patients for balanced intervention access.",
        "Disparity: 3.32 pp (not distinguishable from zero)"
      ),
      formatCard(
        ageAudit,
        "age",
        "Age Cohort Consistency",
        "Ensures geriatric and younger patient populations receive equivalent sensitivity across all age cohorts.",
        "Disparity: 3.93 pp (not distinguishable from zero)"
      ),
    ];
  }, [governance?.fairness]);

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
          {!sidebarCollapsed ? (
            <>
              <div className="brand-wrapper">
                <div className="brand-icon">
                  <Stethoscope className="w-5 h-5 text-white" />
                </div>
                <div className="brand-info">
                  <span className="brand-title">ClinicalAI</span>
                  <span className="brand-subtitle">Readmission Insights</span>
                </div>
              </div>
              <button
                className="sidebar-collapse-btn"
                onClick={toggleSidebar}
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </>
          ) : (
            <button
              className="sidebar-collapse-btn collapsed-toggle"
              onClick={toggleSidebar}
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <Stethoscope className="w-5 h-5 text-white" />
            </button>
          )}
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
                    if (hasActiveFilters) {
                      resetAllFilters();
                      toast.info("Cleared all filters to default neutral view");
                    }
                  }}
                  isActive={hasActiveFilters}
                  miniVisual={
                    <KpiMiniCohortDist
                      lowPct={summary.cohort_size ? (summary.low_risk / summary.cohort_size) * 100 : 62.2}
                      elevatedPct={summary.cohort_size ? (summary.elevated_risk / summary.cohort_size) * 100 : 29.0}
                      highPct={summary.cohort_size ? (summary.high_risk / summary.cohort_size) * 100 : 8.8}
                    />
                  }
                />

                <KpiCard
                  label="Flagged for follow-up (≥ 12%)"
                  value={summary.flagged ?? "189"}
                  rawNumber={summary.flagged ?? 189}
                  context={
                    summary.cohort_size
                      ? `${((summary.flagged / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥12% cutoff)`
                      : "37.8% of cohort (≥12% cutoff)"
                  }
                  secondLine={`High (≥20%): ${summary.high_risk ?? 44} (${summary.cohort_size ? ((summary.high_risk / summary.cohort_size) * 100).toFixed(1) : "8.8"}%) · Elevated (12–20%): ${summary.elevated_risk ?? 145} (${summary.cohort_size ? ((summary.elevated_risk / summary.cohort_size) * 100).toFixed(1) : "29.0"}%)`}
                  icon={AlertTriangle}
                  tone="red"
                  accentRed={true}
                  onClick={() => {
                    if (tier === "flagged") {
                      setTier("all");
                      toast.info("Cleared follow-up filter");
                    } else {
                      setTier("flagged");
                      toast.info("Filtered worklist to Flagged Encounters (≥12%)");
                    }
                    setPage(1);
                  }}
                  isActive={tier === "flagged"}
                  miniVisual={
                    <KpiProportionBar
                      percentage={summary.cohort_size ? (summary.flagged / summary.cohort_size) * 100 : 37.8}
                      tone="red"
                      title={`${summary.cohort_size ? ((summary.flagged / summary.cohort_size) * 100).toFixed(1) : "37.8"}% flagged for transition follow-up (≥12% risk cutoff)`}
                    />
                  }
                />

                <KpiCard
                  label="Polypharmacy Burden"
                  value={summary.polypharmacy ?? "395"}
                  rawNumber={summary.polypharmacy ?? 395}
                  context={
                    summary.cohort_size
                      ? `${((summary.polypharmacy / summary.cohort_size) * 100).toFixed(1)}% of cohort (≥10 meds)`
                      : "79.0% of cohort (≥10 meds)"
                  }
                  icon={Pill}
                  tone="amber"
                  miniVisual={
                    <KpiProportionBar
                      percentage={summary.cohort_size ? (summary.polypharmacy / summary.cohort_size) * 100 : 79.0}
                      tone="amber"
                      title={`${summary.cohort_size ? ((summary.polypharmacy / summary.cohort_size) * 100).toFixed(1) : "79.0"}% of encounters with ≥10 active medications`}
                    />
                  }
                />

                <KpiCard
                  label="Observed Readmissions"
                  value={summary.readmissions ?? "54"}
                  rawNumber={summary.readmissions ?? 54}
                  context={
                    `${summary.cohort_size ? ((summary.readmissions / summary.cohort_size) * 100).toFixed(1) : "10.8"}% sample rate vs test-set rate (11.39%)`
                  }
                  icon={TrendingUp}
                  tone="green"
                  miniVisual={
                    <KpiProportionBar
                      percentage={summary.cohort_size ? (summary.readmissions / summary.cohort_size) * 100 : 10.8}
                      tone="green"
                      title={`${summary.cohort_size ? ((summary.readmissions / summary.cohort_size) * 100).toFixed(1) : "10.8"}% sample rate vs test-set rate (11.39%)`}
                    />
                  }
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
                          <option value="flagged">Flagged for follow-up (≥12%)</option>
                          <option value="high">High risk (≥20%)</option>
                          <option value="elevated">Elevated risk (12–20%)</option>
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

                {/* Permanent Legend */}
                <div className="table-legend-bar">
                  <span className="table-legend-item">
                    <span className="legend-dot polypharmacy-dot">●</span>
                    <span className="legend-label">Polypharmacy</span>
                    <span className="legend-def">= 10 or more active medications</span>
                  </span>
                </div>

                {/* Data Table */}
                <div className="data-table-container">
                  <table className="clinical-data-table">
                    <colgroup>
                      <col className="col-enc" style={{ width: "120px" }} />
                      <col className="col-profile" style={{ width: "165px" }} />
                      <col className="col-stay" style={{ width: "85px" }} />
                      <col className="col-meds" style={{ width: "140px" }} />
                      <col className="col-acute" style={{ width: "135px" }} />
                      <col className="col-flags" style={{ width: "215px" }} />
                      <col className="col-risk" style={{ width: "215px" }} />
                      <col className="col-action" style={{ width: "40px" }} />
                    </colgroup>
                    <thead>
                      <tr>
                        <th className="sortable col-enc" onClick={() => handleSort("enc_id")}>
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
                        <th className="col-profile">Profile</th>
                        <th className="sortable col-stay" onClick={() => handleSort("stay")}>
                          <div className="th-inner-flex">
                            <span>Stay</span>
                            {sortField === "stay" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable col-meds" onClick={() => handleSort("meds")}>
                          <div className="th-inner-flex">
                            <span>Medications</span>
                            <span
                              className="th-info-icon-btn"
                              tabIndex={0}
                              role="button"
                              aria-label="Polypharmacy info"
                              onClick={(e) => e.stopPropagation()}
                              onMouseEnter={(e) => showTooltip("Encounters with 10+ medications are marked with ● Polypharmacy", e.currentTarget, "bottom")}
                              onMouseLeave={hideTooltip}
                              onFocus={(e) => showTooltip("Encounters with 10+ medications are marked with ● Polypharmacy", e.currentTarget, "bottom")}
                              onBlur={hideTooltip}
                            >
                              <Info className="w-3.5 h-3.5 text-muted" />
                            </span>
                            {sortField === "meds" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th className="sortable col-acute" onClick={() => handleSort("inpatient")}>
                          <div className="th-inner-flex">
                            <span>Prior acute</span>
                            {sortField === "inpatient" ? (
                              <motion.span animate={{ rotate: sortOrder === "asc" ? 0 : 180 }} transition={{ duration: 0.15 }}>
                                <ArrowUp className="w-3.5 h-3.5" />
                              </motion.span>
                            ) : (
                              <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />
                            )}
                          </div>
                        </th>
                        <th ref={careFlagsThCallback} className="col-flags">
                          <span>Care flags</span>
                        </th>
                        <th className="sortable col-risk cell-risk-th" onClick={() => handleSort("prob")}>
                          <div className="th-inner-flex">
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
                        <th className="col-action" style={{ width: 40 }} />
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
                          const tierClass = normalized.startsWith("high")
                            ? "high"
                            : normalized.startsWith("elevated") || normalized.startsWith("mod")
                            ? "elevated"
                            : "low";
                          const careFlags = record.resources || [];
                          const maxVisible = 2;
                          const visibleFlags = careFlags.slice(0, maxVisible);
                          const overflowFlags = careFlags.slice(maxVisible);
                          const overflowCount = overflowFlags.length;

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
                              <td className="col-enc">
                                <div className="encounter-cell">
                                  <span className="encounter-id-code">{record.enc_id}</span>
                                  <span className="encounter-subtext">Historical cohort</span>
                                </div>
                              </td>

                              <td className="col-profile">
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

                              <td className="col-stay">
                                <span className="inline-metric tabular-nums">
                                  {record.stay} <small>{Number(record.stay) === 1 ? "day" : "days"}</small>
                                </span>
                              </td>

                              <td className="col-meds">
                                <div className="flex flex-col">
                                  <span className="inline-metric tabular-nums">
                                    {record.meds} <small>{Number(record.meds) === 1 ? "med" : "meds"}</small>
                                  </span>
                                  {Number(record.meds) >= 10 && (
                                    <span
                                      className="polypharmacy-indicator"
                                      tabIndex={0}
                                      role="note"
                                      aria-label="Polypharmacy: 10 or more active medications"
                                      onMouseEnter={(e) => showTooltip("Encounters with 10+ medications are marked with ● Polypharmacy", e.currentTarget, "top")}
                                      onMouseLeave={hideTooltip}
                                      onFocus={(e) => showTooltip("Encounters with 10+ medications are marked with ● Polypharmacy", e.currentTarget, "top")}
                                      onBlur={hideTooltip}
                                    >
                                      ● Polypharmacy
                                    </span>
                                  )}
                                </div>
                              </td>

                              <td className="col-acute">
                                <span className="inline-metric tabular-nums">
                                  {record.inpatient}{" "}
                                  <small>
                                    {Number(record.inpatient) === 1 ? "inpatient" : "inpatient"} · {record.er} ER
                                  </small>
                                </span>
                              </td>

                              <td className="col-flags">
                                <div className="care-flags-cell">
                                  {visibleFlags.map((rawFlag) => {
                                    const cfg = getCareFlagConfig(rawFlag);
                                    const FlagIcon = cfg.icon;
                                    return (
                                      <span
                                        key={rawFlag}
                                        className="care-flag-pill"
                                        title={rawFlag}
                                        onMouseEnter={(e) => showTooltip(rawFlag, e.currentTarget, "top")}
                                        onMouseLeave={hideTooltip}
                                      >
                                        <FlagIcon className={`w-3.5 h-3.5 ${cfg.color} shrink-0`} />
                                        <span className="care-flag-text">{cfg.label}</span>
                                      </span>
                                    );
                                  })}
                                  {overflowCount > 0 && (
                                    <span
                                      className="flag-overflow-chip"
                                      title={careFlags.join(", ")}
                                      tabIndex={0}
                                      role="button"
                                      aria-label={`All care flags: ${careFlags.join(", ")}`}
                                      onMouseEnter={(e) => showTooltip(`Care flags: ${careFlags.join(" · ")}`, e.currentTarget, "top")}
                                      onMouseLeave={hideTooltip}
                                      onFocus={(e) => showTooltip(`Care flags: ${careFlags.join(" · ")}`, e.currentTarget, "top")}
                                      onBlur={hideTooltip}
                                    >
                                      +{overflowCount}
                                    </span>
                                  )}
                                </div>
                              </td>

                              <td className="col-risk cell-risk">
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

                              <td className="col-action">
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

                {/* Sampling Footnote */}
                <div style={{ padding: "8px 16px 12px 16px", fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border-subtle)" }}>
                  Random sample of 500 from the held-out test set (seed 55). Seed 55 was chosen from a candidate sweep to ensure demographic and risk tier representativeness matching the full test holdout (37.8% flagged, 8.8% High, 10.8% sample readmission rate vs. 11.39% test-set rate).
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
            <div className="flex flex-col gap-6">
              {/* Audit Metadata Strip */}
              <motion.div
                className="gov-audit-strip"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="gov-audit-meta-group">
                  <div className="gov-meta-item">
                    <Calendar className="w-4 h-4 text-brand" />
                    <span className="gov-meta-label">Last Evaluated:</span>
                    <span className="gov-meta-value">{governance?.last_audited || "October 2026"}</span>
                  </div>
                  <div className="gov-meta-item">
                    <ShieldCheck className="w-4 h-4 text-brand" />
                    <span className="gov-meta-label">Model Version:</span>
                    <span className="gov-meta-value font-mono text-xs">Demo build: {governance?.model_version || "v2.4.1-calibrated-ensemble"}</span>
                  </div>
                  <div className="gov-meta-item">
                    <Users className="w-4 h-4 text-brand" />
                    <span className="gov-meta-label">Evaluation Cohort:</span>
                    <span className="gov-meta-value">19,870 Inpatient Encounters (Holdout Test Split)</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="status-badge-chip verified">
                    <Check className="w-3.5 h-3.5" />
                    Fairness audited, gaps reported with confidence intervals
                  </span>
                </div>
                <div className="gov-data-split-line">
                  <div>
                    <strong>Data split:</strong> 69,538 encounters training (70.0%) · 9,935 validation (10.0% calibration fold) · 19,870 holdout test (20.0%) · 500 interactive demo encounters.
                  </div>
                  <div className="text-muted text-xs">
                    <strong>Fairness thresholding disclosure:</strong> Demographic mitigation cutoffs and group-specific thresholds were fitted strictly on the validation split (n = 9,935); reported gaps are evaluated on the untouched test holdout (n = 19,870) with 95% bootstrap confidence intervals.
                  </div>
                </div>
              </motion.div>

              {/* How to Read This Page Guide */}
              <motion.div
                className="gov-guide-card"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: 0.05 }}
              >
                <div className="gov-guide-header">
                  <div className="gov-guide-title">
                    <Info className="w-4 h-4 text-brand" />
                    <span>How to Read This Governance Audit</span>
                  </div>
                  <span className="text-xs text-muted">Clinical CDS Transparency Report</span>
                </div>
                <div className="gov-guide-grid">
                  <div className="gov-guide-item">
                    <strong>1. Discrimination (AUC-ROC & Recall)</strong>
                    <p>AUC-ROC measures rank-order separation between readmitted and stable patients. Sensitivity/Recall ensures actual 30-day readmissions are flagged at the operating cutoff.</p>
                  </div>
                  <div className="gov-guide-item">
                    <strong>2. Calibration (Brier Score)</strong>
                    <p>Brier score assesses probabilistic reliability (mean squared probability error). Platt scaling ensures a predicted 12% probability mirrors an observed 12% event rate.</p>
                  </div>
                  <div className="gov-guide-item">
                    <strong>3. Equity & Parity (Equal Opportunity)</strong>
                    <p>Audits sensitivity (TPR) parity across race, gender, and age. Disparities are tested for significance via 95% bootstrap confidence intervals on the untouched test split.</p>
                  </div>
                </div>
              </motion.div>

              {/* SECTION 1: BENCHMARKS & ARCHITECTURE */}
              <motion.div
                className="card-panel"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                <div className="panel-header-row">
                  <div className="panel-title-text">
                    <h2>Ensemble Architecture & Candidate Benchmarks</h2>
                    <p>Comparative metrics across 6 clinical model variations on the untouched test holdout (n = 19,870).</p>
                  </div>
                  <span className="status-badge-chip verified">
                    <Check className="w-3.5 h-3.5" />
                    Selected Ensemble
                  </span>
                </div>

                <dl className="ensemble-stats-dl mb-4">
                  <div className="ensemble-stat-card">
                    <dt className="ensemble-stat-dt">Discrimination (AUC-ROC)</dt>
                    <dd className="ensemble-stat-dd tabular-nums">
                      <AnimatedNumber value={Number(championAuc)} format={(v) => v.toFixed(3)} />
                    </dd>
                    <span className="ensemble-stat-sub">Test holdout (n = 19,870)</span>
                  </div>
                  <div className="ensemble-stat-card">
                    <dt className="ensemble-stat-dt">Brier Calibration Score</dt>
                    <dd className="ensemble-stat-dd tabular-nums">
                      <AnimatedNumber value={Number(championBrier)} format={(v) => v.toFixed(4)} />
                    </dd>
                    <span className="ensemble-stat-sub">Sigmoid Platt aligned</span>
                  </div>
                  <div className="ensemble-stat-card">
                    <dt className="ensemble-stat-dt">Clinical Decision Cutoff</dt>
                    <dd className="ensemble-stat-dd tabular-nums">
                      {championCutoff}
                    </dd>
                    <span className="ensemble-stat-sub">Clinical follow-up trigger (≥ 12.0%)</span>
                  </div>
                </dl>

                {/* Operating Point View Toggle */}
                <div className="flex items-center justify-between gap-3 flex-wrap mt-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted">Operating Point:</span>
                    <div className="benchmark-toggle-group">
                      <button
                        type="button"
                        className={`benchmark-toggle-btn ${govCutoffView === "common" ? "active" : ""}`}
                        onClick={() => setGovCutoffView("common")}
                      >
                        Common Cutoff (12.0%)
                      </button>
                      <button
                        type="button"
                        className={`benchmark-toggle-btn ${govCutoffView === "tuned" ? "active" : ""}`}
                        onClick={() => setGovCutoffView("tuned")}
                      >
                        Model's Own Tuned Cutoff
                      </button>
                    </div>
                  </div>
                  <span className="text-xs text-muted">
                    {govCutoffView === "common"
                      ? "All models evaluated at identical 12.0% threshold"
                      : "Each model evaluated at its validation-tuned cutoff"}
                  </span>
                </div>

                {/* Dense 10-Column Benchmark Table */}
                <div className="benchmark-table-wrapper">
                  <table className="benchmark-dense-table">
                    <thead>
                      <tr>
                        <th className="sortable-th" onClick={() => handleGovSort("Model")}>
                          <div className="flex items-center gap-1">
                            <span>Model Candidate</span>
                            {govSortField === "Model" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Cutoff")}>
                          <div className="flex items-center gap-1">
                            <span>Cutoff</span>
                            {govSortField === "Cutoff" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("AUC-ROC")}>
                          <div className="flex items-center gap-1">
                            <span>AUC-ROC</span>
                            {govSortField === "AUC-ROC" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Accuracy")}>
                          <div className="flex items-center gap-1">
                            <span>Accuracy</span>
                            {govSortField === "Accuracy" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Precision")}>
                          <div className="flex items-center gap-1">
                            <span>Precision</span>
                            {govSortField === "Precision" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Recall")}>
                          <div className="flex items-center gap-1">
                            <span>Recall</span>
                            {(govSortField === "Recall" || govSortField === "Sensitivity") && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("F1-Score")}>
                          <div className="flex items-center gap-1">
                            <span>F1-Score</span>
                            {govSortField === "F1-Score" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Flag Rate (%)")}>
                          <div className="flex items-center gap-1">
                            <span>Flag Rate</span>
                            {govSortField === "Flag Rate (%)" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Brier Score")}>
                          <div className="flex items-center gap-1">
                            <span>Brier Score</span>
                            {govSortField === "Brier Score" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                        <th className="sortable-th" onClick={() => handleGovSort("Training Time (s)")}>
                          <div className="flex items-center gap-1">
                            <span>Train Time</span>
                            {govSortField === "Training Time (s)" && (govSortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedGovModels.map((m) => {
                        const isChampion = m.Model === (governance?.selected_model || "Calibrated Ensemble") || m.Model.includes("Ensemble");
                        const cutoff = m.Cutoff ?? m.Threshold ?? 0.12;
                        const auc = Number(m["AUC-ROC"] || 0);
                        const acc = Number(m.Accuracy || 0);
                        const prec = Number(m.Precision || 0);
                        const rec = Number(m["Recall (Sensitivity)"] ?? m.Recall ?? m.Sensitivity ?? 0);
                        const f1 = Number(m["F1-Score"] || 0);
                        const flagRate = Number(m["Flag Rate (%)"] || (m["Flag Rate"] ? m["Flag Rate"] * 100 : 0));
                        const brier = Number(m["Brier Score"] || 0);
                        const trainTime = m["Training Time (s)"] != null ? Number(m["Training Time (s)"]) : null;

                        return (
                          <tr key={m.Model} className={isChampion ? "champion-row" : ""}>
                            <td>
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <strong>{m.Model}</strong>
                                {isChampion && (
                                  <span className="champion-tag">
                                    <Sparkles className="w-3 h-3" /> Selected
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="tabular-nums">≥ {(cutoff * 100).toFixed(1)}%</td>
                            <td className="tabular-nums font-semibold">{auc > 0 ? auc.toFixed(3) : "—"}</td>
                            <td className="tabular-nums">{acc > 0 ? `${(acc * 100).toFixed(1)}%` : "—"}</td>
                            <td className="tabular-nums">{prec > 0 ? `${(prec * 100).toFixed(1)}%` : "—"}</td>
                            <td className="tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">{rec > 0 ? `${(rec * 100).toFixed(1)}%` : "—"}</td>
                            <td className="tabular-nums">{f1 > 0 ? f1.toFixed(3) : "—"}</td>
                            <td className="tabular-nums">{flagRate > 0 ? `${flagRate.toFixed(1)}%` : "—"}</td>
                            <td className="tabular-nums font-mono">{brier > 0 ? brier.toFixed(4) : "—"}</td>
                            <td className="tabular-nums">{trainTime != null ? (trainTime === 0 ? "— (blend)" : `${trainTime.toFixed(2)}s`) : "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="benchmark-candidate-note mt-3">
                  <strong>Model selection note:</strong> CatBoost achieves an identical Brier score (0.0976) and comparable AUC (0.6525 vs. 0.6530) to the Calibrated Ensemble. Differences in AUC across candidates (0.647 to 0.653) are modest. The soft-voting ensemble was chosen primarily for variance reduction across cross-validation splits, multi-model robustness, and Platt probability alignment rather than standalone discriminatory superiority.
                </div>

                {/* What Each Model is Optimized For */}
                <div className="mt-6">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted mb-2">What Each Model is Optimized For</h3>
                  <div className="model-optimized-grid">
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><Scale className="w-3.5 h-3.5 text-brand" /> Logistic Regression</span>
                      <p className="model-optimized-desc">Rapid linear baseline optimized for log-odds interpretability, transparent clinical coefficients, and direct odds-ratio evaluations.</p>
                    </div>
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><Layers className="w-3.5 h-3.5 text-brand" /> Random Forest</span>
                      <p className="model-optimized-desc">Bagged ensemble of deep decision trees optimized for variance reduction and robustness against noisy clinical laboratory measurements.</p>
                    </div>
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><TrendingUp className="w-3.5 h-3.5 text-brand" /> XGBoost</span>
                      <p className="model-optimized-desc">Gradient boosted decision trees with second-order Taylor expansion loss optimization, tuned for discriminatory rank-order AUC.</p>
                    </div>
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><Activity className="w-3.5 h-3.5 text-brand" /> LightGBM</span>
                      <p className="model-optimized-desc">Histogram-based leaf-wise gradient boosting optimized for memory efficiency and capturing complex high-order comorbidity interactions.</p>
                    </div>
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><Database className="w-3.5 h-3.5 text-brand" /> CatBoost</span>
                      <p className="model-optimized-desc">Ordered boosting with minimal target leakage and native symmetric tree splits, achieving tied best calibration (Brier 0.0976).</p>
                    </div>
                    <div className="model-optimized-card">
                      <span className="model-optimized-title"><Sparkles className="w-3.5 h-3.5 text-brand" /> Calibrated Ensemble</span>
                      <p className="model-optimized-desc">Soft-voting blend (LightGBM + XGBoost + CatBoost) with Platt sigmoid calibration, delivering top Brier calibration (0.0976) and 57.6% recall.</p>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* SECTION 2: OPERATING POINT TRADE-OFFS & TIER VALIDATION (2-COLUMN GRID) */}
              <div className="governance-grid-2col">
                {/* Left Column: Interactive Threshold Slider */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Decision Cutoff Operating Trade-offs</h2>
                      <p>Live confusion matrix & operating metrics on the holdout test set (n = 19,870).</p>
                    </div>
                    <span className="status-badge-chip neutral">
                      <Sliders className="w-3.5 h-3.5" />
                      Cutoff: {(activeTradeoff.cutoff * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="tradeoff-box">
                    <div className="tradeoff-slider-track-wrap">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted font-semibold uppercase">Operating Threshold:</span>
                        <span className="font-mono font-bold text-brand text-sm">{(activeTradeoff.cutoff * 100).toFixed(1)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.05"
                        max="0.35"
                        step="0.01"
                        value={activeTradeoff.cutoff}
                        onChange={(e) => setGovThresholdSlider(parseFloat(e.target.value))}
                        className="tradeoff-range-slider"
                        aria-label="Decision Threshold Slider"
                      />
                      <div className="flex items-center justify-between text-xs text-muted">
                        <span>5.0% (High Recall)</span>
                        <span>12.0% (Clinical Cutoff)</span>
                        <span>35.0% (High Specificity)</span>
                      </div>
                    </div>

                    <div className="tradeoff-presets-row">
                      <button
                        type="button"
                        className={`tradeoff-preset-chip ${Math.abs(activeTradeoff.cutoff - 0.08) < 0.005 ? "active" : ""}`}
                        onClick={() => setGovThresholdSlider(0.08)}
                      >
                        Low Cutoff (8.0%)
                      </button>
                      <button
                        type="button"
                        className={`tradeoff-preset-chip ${Math.abs(activeTradeoff.cutoff - 0.12) < 0.005 ? "active" : ""}`}
                        onClick={() => setGovThresholdSlider(0.12)}
                      >
                        Deployed Cutoff (12.0%)
                      </button>
                      <button
                        type="button"
                        className={`tradeoff-preset-chip ${Math.abs(activeTradeoff.cutoff - 0.15) < 0.005 ? "active" : ""}`}
                        onClick={() => setGovThresholdSlider(0.15)}
                      >
                        Balanced (15.0%)
                      </button>
                      <button
                        type="button"
                        className={`tradeoff-preset-chip ${Math.abs(activeTradeoff.cutoff - 0.20) < 0.005 ? "active" : ""}`}
                        onClick={() => setGovThresholdSlider(0.20)}
                      >
                        High Specificity (20.0%)
                      </button>
                    </div>

                    {/* Confusion Matrix 4-Card Grid */}
                    <div className="tradeoff-matrix-grid">
                      <div className="tradeoff-cell tp">
                        <span className="tradeoff-cell-lbl text-emerald-600 dark:text-emerald-400">True Positives (TP)</span>
                        <span className="tradeoff-cell-val tabular-nums">{activeTradeoff.tp.toLocaleString()}</span>
                        <span className="tradeoff-cell-sub">Correctly identified readmissions</span>
                      </div>
                      <div className="tradeoff-cell fp">
                        <span className="tradeoff-cell-lbl text-amber-600 dark:text-amber-400">False Positives (FP)</span>
                        <span className="tradeoff-cell-val tabular-nums">{activeTradeoff.fp.toLocaleString()}</span>
                        <span className="tradeoff-cell-sub">Stable patients flagged for outreach</span>
                      </div>
                      <div className="tradeoff-cell tn">
                        <span className="tradeoff-cell-lbl text-indigo-600 dark:text-indigo-400">True Negatives (TN)</span>
                        <span className="tradeoff-cell-val tabular-nums">{activeTradeoff.tn.toLocaleString()}</span>
                        <span className="tradeoff-cell-sub">Correctly unflagged routine discharges</span>
                      </div>
                      <div className="tradeoff-cell fn">
                        <span className="tradeoff-cell-lbl text-red-600 dark:text-red-400">False Negatives (FN)</span>
                        <span className="tradeoff-cell-val tabular-nums">{activeTradeoff.fn.toLocaleString()}</span>
                        <span className="tradeoff-cell-sub">Unflagged readmissions (missed)</span>
                      </div>
                    </div>

                    {/* Operating Metrics Summary */}
                    <div className="tradeoff-metrics-row">
                      <div className="tradeoff-metric-pill">
                        <span className="tradeoff-metric-lbl">Sensitivity</span>
                        <span className="tradeoff-metric-val tabular-nums text-emerald-600 dark:text-emerald-400">{activeTradeoff.sensitivity.toFixed(1)}%</span>
                      </div>
                      <div className="tradeoff-metric-pill">
                        <span className="tradeoff-metric-lbl">Specificity</span>
                        <span className="tradeoff-metric-val tabular-nums text-indigo-600 dark:text-indigo-400">{activeTradeoff.specificity.toFixed(1)}%</span>
                      </div>
                      <div className="tradeoff-metric-pill">
                        <span className="tradeoff-metric-lbl">Precision</span>
                        <span className="tradeoff-metric-val tabular-nums text-amber-600 dark:text-amber-400">{activeTradeoff.precision.toFixed(1)}%</span>
                      </div>
                      <div className="tradeoff-metric-pill">
                        <span className="tradeoff-metric-lbl">Flag Rate</span>
                        <span className="tradeoff-metric-val tabular-nums">{activeTradeoff.flag_rate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Right Column: Risk Tier Empirical Validation */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: 0.05 }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Risk Tier Empirical Validation</h2>
                      <p>Observed 30-day readmission rate per tier on the test set (n = 19,870).</p>
                    </div>
                    <span className="status-badge-chip verified">
                      <Check className="w-3.5 h-3.5" />
                      Monotonic Risk
                    </span>
                  </div>

                  <div className="tier-table-wrapper">
                    <table className="tier-data-table">
                      <thead>
                        <tr>
                          <th>Risk Tier</th>
                          <th>Encounters (n & %)</th>
                          <th>Readmissions</th>
                          <th>Observed Rate</th>
                          <th>Prescribed Care Bundle</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(governance?.tier_validation || [
                          { tier: "Low (<12%)", n: 12365, pct_cohort: 62.2, observed_readmissions: 959, observed_rate_pct: 7.76, clinical_action: "Routine discharge summary and 30-day primary care appointment" },
                          { tier: "Elevated (12–20%)", n: 5755, pct_cohort: 29.0, observed_readmissions: 881, observed_rate_pct: 15.31, clinical_action: "Enhanced transition planning, pharmacy consult, and 7–10 day follow-up" },
                          { tier: "High (≥20%)", n: 1750, pct_cohort: 8.8, observed_readmissions: 423, observed_rate_pct: 24.17, clinical_action: "Multidisciplinary care plan, 48-hour telehealth outreach, CDCES educator consult" },
                        ]).map((t) => (
                          <tr key={t.tier}>
                            <td>
                              <strong>{t.tier}</strong>
                            </td>
                            <td className="tabular-nums">
                              {Number(t.n).toLocaleString()} ({t.pct_cohort}%)
                            </td>
                            <td className="tabular-nums font-semibold">
                              {Number(t.observed_readmissions).toLocaleString()}
                            </td>
                            <td className="tabular-nums font-bold text-brand">
                              {t.observed_rate_pct.toFixed(2)}%
                            </td>
                            <td className="text-xs text-secondary">
                              {t.clinical_action}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="benchmark-candidate-note mt-3">
                    <strong>Monotonic risk tier validation:</strong> Observed readmission frequency increases strictly monotonically from <strong>7.76%</strong> in Low Tier to <strong>15.31%</strong> in Elevated Tier and <strong>24.17%</strong> in High Tier (a 3.1× separation). This validates that predicted risk boundaries correspond directly to empirical patient outcomes across the test cohort.
                  </div>
                </motion.div>
              </div>

              {/* SECTION 3: FAIRNESS AUDIT & METHODOLOGY */}
              <motion.div
                className="card-panel"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                <div className="panel-header-row">
                  <div className="panel-title-text">
                    <h2>Demographic Fairness Audits & Disparity Analysis</h2>
                    <p>Equal Opportunity & True Positive Rate consistency audited across protected groups.</p>
                  </div>
                  <span className="status-badge-chip verified">
                    <Check className="w-3.5 h-3.5" />
                    Validation-Fit Audits
                  </span>
                </div>

                {/* Explicit Fairness Methodology & Deployed Policy Banner */}
                <div className="fairness-methodology-banner mb-4">
                  <div>
                    <strong>Fairness Mitigation Definition:</strong> Group-specific classification threshold adjustment evaluated during post-processing disparity analysis (Caucasian validation cutoff adjusted to 12.1% vs. 12.0% for other cohorts). In addition, training-time class-weighting and random undersampling were evaluated on training splits only.
                  </div>
                  <div>
                    <strong>Active Clinical Deployment Standard:</strong> <em>Analysis only, not deployed.</em> The deployed clinical worklist and bedside risk calculator use the single, unified 12.0% decision threshold across all encounters without race- or sex-specific adjustments. Group-specific thresholds are retained strictly as an offline research analysis.
                  </div>
                </div>

                {/* Parity Tradeoff Plain Callout */}
                <div className="parity-tradeoff-alert mb-5">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-500" />
                  <div>
                    <strong>Parity Trade-off Finding:</strong> Equalizing True Positive Rates requires adjusting the Caucasian threshold upward to 12.1% on validation. When evaluated on the untouched test holdout (n = 19,870), this lowers Caucasian recall from <strong>58.67% to 57.93%</strong> and lowers overall cohort recall from <strong>57.62% to 57.05%</strong> (with flag rate dropping from 37.77% to 37.41%). Parity is achieved by reducing detection in the largest group rather than improving detection in underrepresented cohorts.
                  </div>
                </div>

                {/* Demographic Subgroup Audits (Race, Sex, Age) */}
                <div className="fairness-card-list">
                  {fairnessCards.map((card) => (
                    <div key={card.id} className="fairness-card-block">
                      <div className="fairness-card-top">
                        <div className="fairness-card-header-row">
                          <div className="flex items-center justify-between gap-3 flex-wrap w-full">
                            <h3 className="fairness-group-title">{card.title}</h3>
                            <span
                              className={`status-badge-chip ${card.statusTone} cursor-help`}
                              title="Audit status accounting for 95% bootstrap confidence interval."
                            >
                              <Info className="w-3.5 h-3.5" />
                              {card.status}
                            </span>
                          </div>
                          <p className="fairness-group-desc">{card.desc}</p>
                        </div>

                        <div className="fairness-disparity-box">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <span className="disparity-box-caption">Headline Disparity Gap ({card.headlineComparison})</span>
                            <span
                              className="improvement-badge-pill"
                              title={card.reductionBadge}
                            >
                              <TrendingDown className="w-3.5 h-3.5" />
                              {card.reductionBadge}
                            </span>
                          </div>
                          <div className="disparity-box-val-row">
                            <span className="disparity-box-large-val tabular-nums">{card.gap}</span>
                            <span className="disparity-box-sub font-mono">
                              95% CI: {card.gapCi}
                            </span>
                            {card.mitigatedGap && (
                              <span className="disparity-box-sub text-muted">
                                · Mitigated (val-tuned): {card.mitigatedGap} (CI: {card.mitigatedGapCi})
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Clean Zoomed Axis Visualization (30% to 75% Scale) */}
                      <div className="fairness-zoomed-container">
                        <div className="fairness-axis-header">
                          <span>Subgroup (sample size & readmissions)</span>
                          <div className="fairness-axis-ticks">
                            <span className="axis-tick" style={{ left: "0%" }}>30%</span>
                            <span className="axis-tick reference-tick" style={{ left: "52.0%" }} title="Cohort Average Sensitivity (53.4%)">
                              53.4% Cohort Avg
                            </span>
                            <span className="axis-tick" style={{ left: "100%", transform: "translateX(-100%)" }}>75%</span>
                          </div>
                          <span className="text-right">TPR (95% CI)</span>
                        </div>

                        <div className="flex flex-col gap-2">
                          {card.subgroups.map((sg) => {
                            const scalePct = Math.min(100, Math.max(0, ((sg.tpr - 30) / 45) * 100));
                            return (
                              <div key={sg.name} className="subgroup-zoomed-row">
                                <div className="subgroup-name-col">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="subgroup-name-text" title={sg.name}>{sg.name}</span>
                                    {sg.isSmall && (
                                      <span className="small-sample-badge">
                                        Sample too small to conclude (&lt;100 readmissions)
                                      </span>
                                    )}
                                  </div>
                                  <span className="subgroup-n-text">
                                    n = {sg.n.toLocaleString()} · {sg.k.toLocaleString()} readmitted
                                  </span>
                                </div>

                                <div className="subgroup-zoomed-track" title={`${sg.name}: ${sg.tpr.toFixed(1)}% TPR`}>
                                  <div className="subgroup-ref-line" style={{ left: "52.0%" }} />
                                  <motion.div
                                    className="subgroup-zoomed-fill"
                                    initial={{ width: 0 }}
                                    whileInView={{ width: `${scalePct}%` }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.6, ease: "easeOut" }}
                                  />
                                </div>

                                <div className="subgroup-ci-col">
                                  <span className="subgroup-tpr-val tabular-nums">{sg.tpr.toFixed(1)}%</span>
                                  <span className="subgroup-ci-text tabular-nums" title="95% Bootstrap Confidence Interval">
                                    CI: {sg.ci}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        <div className="subgroup-uncertainty-note">
                          <Info className="w-3.5 h-3.5 flex-shrink-0 text-muted" />
                          <span>Headline gaps reported only among strata with ≥100 readmissions. Subgroups with &lt;100 readmitted cases produce wide confidence intervals and are marked as too small to conclude.</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Side-by-Side: Unmitigated Deployed vs Mitigated Table */}
                <div className="mt-8">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted mb-2">Unmitigated (Deployed) vs. Mitigated (Analysis Only) Side-by-Side</h3>
                  <div className="clean-data-table-wrap">
                    <table className="clean-data-table">
                      <thead>
                        <tr>
                          <th>Cohort Stratum / Performance Metric</th>
                          <th>Unmitigated Deployed (12.0% Cutoff)</th>
                          <th>Mitigated (Val-Tuned Cutoff, Analysis Only)</th>
                          <th>Impact / Parity Tradeoff</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><strong>Overall Cohort Recall (Sensitivity)</strong></td>
                          <td className="tabular-nums font-semibold">57.62%</td>
                          <td className="tabular-nums font-semibold text-amber-600 dark:text-amber-400">57.05%</td>
                          <td className="text-xs text-muted">-0.57 pp overall sensitivity loss</td>
                        </tr>
                        <tr>
                          <td><strong>Overall Cohort Precision</strong></td>
                          <td className="tabular-nums">17.38%</td>
                          <td className="tabular-nums">17.37%</td>
                          <td className="text-xs text-muted">-0.01 pp</td>
                        </tr>
                        <tr>
                          <td><strong>Overall Cohort Flag Rate (% Flagged)</strong></td>
                          <td className="tabular-nums">37.77%</td>
                          <td className="tabular-nums">37.41%</td>
                          <td className="text-xs text-muted">-0.36 pp (71 fewer patients flagged)</td>
                        </tr>
                        <tr>
                          <td>Caucasian Sensitivity (TPR) / False Positive (FPR)</td>
                          <td className="tabular-nums">58.67% / 36.16%</td>
                          <td className="tabular-nums">57.93% / 35.72%</td>
                          <td className="text-xs text-amber-600 dark:text-amber-400">-0.74 pp recall drop in largest group</td>
                        </tr>
                        <tr>
                          <td>African American Sensitivity (TPR) / FPR</td>
                          <td className="tabular-nums">53.69% / 34.86%</td>
                          <td className="tabular-nums">53.69% / 34.86%</td>
                          <td className="text-xs text-muted">0.00 pp change (cutoff kept at 12.0%)</td>
                        </tr>
                        <tr>
                          <td>Female Sensitivity (TPR) / FPR</td>
                          <td className="tabular-nums">59.13% / 36.45%</td>
                          <td className="tabular-nums">58.48% / 36.13%</td>
                          <td className="text-xs text-muted">-0.65 pp recall drop</td>
                        </tr>
                        <tr>
                          <td>Male Sensitivity (TPR) / FPR</td>
                          <td className="tabular-nums">55.80% / 33.81%</td>
                          <td className="tabular-nums">55.32% / 33.47%</td>
                          <td className="text-xs text-muted">-0.48 pp recall drop</td>
                        </tr>
                        <tr>
                          <td>60+ Years Sensitivity (TPR) / FPR</td>
                          <td className="tabular-nums">58.32% / 40.17%</td>
                          <td className="tabular-nums">57.76% / 39.75%</td>
                          <td className="text-xs text-muted">-0.56 pp recall drop</td>
                        </tr>
                        <tr>
                          <td>30-60 Years Sensitivity (TPR) / FPR</td>
                          <td className="tabular-nums">54.39% / 25.96%</td>
                          <td className="tabular-nums">53.89% / 25.78%</td>
                          <td className="text-xs text-muted">-0.50 pp recall drop</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Training Strategies Stretch Comparison Table */}
                <div className="mt-8">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted mb-2">Training Strategies Stretch Comparison (Fitted on Training Split Only)</h3>
                  <div className="clean-data-table-wrap">
                    <table className="clean-data-table">
                      <thead>
                        <tr>
                          <th>Strategy Name</th>
                          <th>Validation-Tuned Cutoff</th>
                          <th>AUC-ROC</th>
                          <th>Brier Score</th>
                          <th>Recall</th>
                          <th>Precision</th>
                          <th>Flag Rate</th>
                          <th>Caucasian TPR</th>
                          <th>AA TPR</th>
                          <th>Race Gap</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(governance?.fairness?.training_strategies_comparison || [
                          { strategy_name: "Baseline Unweighted XGBoost", val_tuned_threshold: 0.14, auc_roc: 0.6521, brier_score: 0.0976, recall_pct: 43.53, precision_pct: 18.51, flag_rate_pct: 26.78, cauc_tpr_pct: 43.92, aa_tpr_pct: 41.38, race_gap_pp: 2.54 },
                          { strategy_name: "Class-Weighted XGBoost", val_tuned_threshold: 0.55, auc_roc: 0.6517, brier_score: 0.2262, recall_pct: 45.51, precision_pct: 18.74, flag_rate_pct: 27.66, cauc_tpr_pct: 46.11, aa_tpr_pct: 43.60, race_gap_pp: 2.51 },
                          { strategy_name: "Resampling (RUS on Train)", val_tuned_threshold: 0.54, auc_roc: 0.6494, brier_score: 0.2328, recall_pct: 51.17, precision_pct: 17.93, flag_rate_pct: 32.51, cauc_tpr_pct: 51.59, aa_tpr_pct: 48.52, race_gap_pp: 3.06 },
                          { strategy_name: "Calibrated Ensemble (Deployed)", val_tuned_threshold: 0.12, auc_roc: 0.6530, brier_score: 0.0976, recall_pct: 57.62, precision_pct: 17.38, flag_rate_pct: 37.77, cauc_tpr_pct: 58.67, aa_tpr_pct: 53.69, race_gap_pp: 4.98 },
                        ]).map((strat) => (
                          <tr key={strat.strategy_name} className={strat.strategy_name.includes("Deployed") ? "champion-row" : ""}>
                            <td>
                              <strong>{strat.strategy_name}</strong>
                            </td>
                            <td className="tabular-nums">≥ {(strat.val_tuned_threshold * 100).toFixed(1)}%</td>
                            <td className="tabular-nums">{strat.auc_roc.toFixed(3)}</td>
                            <td className="tabular-nums font-mono">{strat.brier_score.toFixed(4)}</td>
                            <td className="tabular-nums font-semibold">{strat.recall_pct.toFixed(1)}%</td>
                            <td className="tabular-nums">{strat.precision_pct.toFixed(1)}%</td>
                            <td className="tabular-nums">{strat.flag_rate_pct.toFixed(1)}%</td>
                            <td className="tabular-nums">{strat.cauc_tpr_pct.toFixed(1)}%</td>
                            <td className="tabular-nums">{strat.aa_tpr_pct.toFixed(1)}%</td>
                            <td className="tabular-nums font-bold text-brand">{strat.race_gap_pp.toFixed(2)} pp</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-muted mt-2">
                    Note on calibration: Class-weighting and random under-sampling distort predicted posterior probabilities, degrading Brier scores from 0.0976 to 0.2262 and 0.2328. The Platt-calibrated ensemble maintains probabilistic fidelity (0.0976) while capturing higher sensitivity (57.62%).
                  </p>
                </div>
              </motion.div>

              {/* SECTION 4: DATA PREPROCESSING & FEATURE IMPORTANCE (2-COLUMN GRID) */}
              <div className="governance-grid-2col">
                {/* Left Column: Data & Preprocessing */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Data & Preprocessing Pipeline</h2>
                      <p>EDA statistics, cleaning rules, encoding, and feature exclusion rationale.</p>
                    </div>
                    <span className="status-badge-chip verified">
                      <Check className="w-3.5 h-3.5" />
                      0% Leakage
                    </span>
                  </div>

                  <div className="flex flex-col gap-4 text-xs text-secondary leading-relaxed">
                    <div className="tradeoff-matrix-grid">
                      <div className="tradeoff-cell">
                        <span className="tradeoff-cell-lbl">Raw Inpatient Encounters</span>
                        <span className="tradeoff-cell-val tabular-nums">101,766</span>
                        <span className="tradeoff-cell-sub">UCI Diabetes Repository</span>
                      </div>
                      <div className="tradeoff-cell">
                        <span className="tradeoff-cell-lbl">Terminal Exclusions</span>
                        <span className="tradeoff-cell-val tabular-nums text-red-500">2,423</span>
                        <span className="tradeoff-cell-sub">Expired or Hospice transfer</span>
                      </div>
                      <div className="tradeoff-cell">
                        <span className="tradeoff-cell-lbl">Clean Encounters</span>
                        <span className="tradeoff-cell-val tabular-nums text-brand">99,343</span>
                        <span className="tradeoff-cell-sub">69,990 unique patients</span>
                      </div>
                      <div className="tradeoff-cell">
                        <span className="tradeoff-cell-lbl">Readmission Prevalence</span>
                        <span className="tradeoff-cell-val tabular-nums">11.39%</span>
                        <span className="tradeoff-cell-sub">11,314 positive cases</span>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-bold text-primary mb-1">Preprocessing & Encoding Standards:</h4>
                      <ul className="list-disc pl-4 space-y-1">
                        <li><strong>Patient Grouping:</strong> Grouped strictly by <code>patient_nbr</code> to prevent patient leakage across Train (69,538, 70%), Val (9,935, 10%), and Test (19,870, 20%).</li>
                        <li><strong>Diagnosis Target Encoding:</strong> Primary ICD-9 diagnoses mapped into 9 clinical categories with target encoding and smoothing.</li>
                        <li><strong>Missing Data Imputation:</strong> Medical specialty (49.1% missing) imputed with explicit category <code>'Missing'</code>; Race (2.2% missing) imputed with category <code>'Other/Unknown'</code>.</li>
                        <li><strong>Scaling & Capping:</strong> Continuous clinical variables scaled with StandardScaler; lab volume capped at 99th percentile to prevent outlier leverage.</li>
                      </ul>
                    </div>

                    <div>
                      <h4 className="font-bold text-primary mb-1">Feature Exclusion Audit (13 Excluded Variables):</h4>
                      <div className="clean-data-table-wrap">
                        <table className="clean-data-table">
                          <thead>
                            <tr>
                              <th>Feature</th>
                              <th>Exclusion Reason</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr><td><code>encounter_id</code></td><td>Arbitrary primary key; zero generalizable predictive signal.</td></tr>
                            <tr><td><code>patient_nbr</code></td><td>Subject ID; reserved strictly for patient-grouped train/test splitting.</td></tr>
                            <tr><td><code>weight</code></td><td>96.9% missing; imputation introduces severe artifact risk.</td></tr>
                            <tr><td><code>payer_code</code></td><td>39.6% missing; non-clinical billing artifact.</td></tr>
                            <tr><td><code>medical_specialty</code></td><td>High sparsity and unstandardized across participating facilities.</td></tr>
                            <tr><td><code>diag_2, diag_3</code></td><td>Secondary/tertiary ICD-9 codes; extreme noise and collinearity.</td></tr>
                            <tr><td><code>readmitted</code></td><td>Target ground-truth label (&lt;30 days); excluded to prevent leakage.</td></tr>
                            <tr><td><code>examide, citoglipton</code></td><td>Zero variance (100% 'No' across entire cohort).</td></tr>
                            <tr><td><code>discharge_disposition_id (terminal)</code></td><td>Expired/hospice patients removed from cohort prior to modeling.</td></tr>
                            <tr><td><code>admission_source_id</code></td><td>Collinear with admission type and hospital transfer logs.</td></tr>
                            <tr><td><code>rare anti-diabetics</code></td><td>Near-zero variance (&lt;0.01% non-zero prescriptions).</td></tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Right Column: Feature Importance & Odds Ratios */}
                <motion.div
                  className="card-panel"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: 0.05 }}
                >
                  <div className="panel-header-row">
                    <div className="panel-title-text">
                      <h2>Feature Importance & Clinical Odds Ratios</h2>
                      <p>Key risk drivers and protective clinical factors identified across models.</p>
                    </div>
                    <div className="benchmark-toggle-group">
                      <button
                        type="button"
                        className={`benchmark-toggle-btn ${featImpView === "odds_ratios" ? "active" : ""}`}
                        onClick={() => setFeatImpView("odds_ratios")}
                      >
                        Odds Ratios (LR)
                      </button>
                      <button
                        type="button"
                        className={`benchmark-toggle-btn ${featImpView === "tree" ? "active" : ""}`}
                        onClick={() => setFeatImpView("tree")}
                      >
                        Tree Importance
                      </button>
                    </div>
                  </div>

                  {featImpView === "odds_ratios" ? (
                    <div className="odds-ratios-list">
                      <span className="text-xs font-bold text-muted uppercase">Top Risk-Increasing Predictors (Odds Multipliers):</span>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingUp className="w-3.5 h-3.5 text-red-500" /> Number of Prior Inpatient Visits</span>
                        <span className="odds-ratio-val risk">OR = 1.341 (+34.1% odds)</span>
                      </div>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingUp className="w-3.5 h-3.5 text-red-500" /> Number of Prior Emergency Visits</span>
                        <span className="odds-ratio-val risk">OR = 1.182 (+18.2% odds)</span>
                      </div>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingUp className="w-3.5 h-3.5 text-red-500" /> Hospital Stay Duration (Days)</span>
                        <span className="odds-ratio-val risk">OR = 1.079 (+7.9% odds)</span>
                      </div>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingUp className="w-3.5 h-3.5 text-red-500" /> Lab Procedures Volume</span>
                        <span className="odds-ratio-val risk">OR = 1.054 (+5.4% odds)</span>
                      </div>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingUp className="w-3.5 h-3.5 text-red-500" /> Medication Count (Polypharmacy)</span>
                        <span className="odds-ratio-val risk">OR = 1.042 (+4.2% odds)</span>
                      </div>

                      <span className="text-xs font-bold text-muted uppercase mt-3">Top Protective / Stabilizing Factors:</span>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingDown className="w-3.5 h-3.5 text-emerald-500" /> Prior Outpatient Visit Engagement</span>
                        <span className="odds-ratio-val protective">OR = 0.948 (-5.2% odds)</span>
                      </div>
                      <div className="odds-ratio-row">
                        <span className="odds-ratio-factor"><TrendingDown className="w-3.5 h-3.5 text-emerald-500" /> Normal HbA1c Glycemic Test Result</span>
                        <span className="odds-ratio-val protective">OR = 0.912 (-8.8% odds)</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      <span className="text-xs font-bold text-muted uppercase">Relative Feature Contribution Across Gradient Boosted Trees:</span>
                      {[
                        { feature: "Prior Inpatient Admissions", share: 24.8 },
                        { feature: "Time in Hospital (Inpatient Days)", share: 18.2 },
                        { feature: "Lab Procedure Volume", share: 15.6 },
                        { feature: "Number of Medications", share: 13.1 },
                        { feature: "Primary ICD-9 Diagnosis Group", share: 10.4 },
                        { feature: "Prior Emergency Encounters", share: 9.7 },
                        { feature: "Age Stratum", share: 4.9 },
                        { feature: "HbA1c Glycemic Result", share: 3.3 },
                      ].map((item) => (
                        <div key={item.feature} className="flex flex-col gap-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-primary">{item.feature}</span>
                            <span className="font-mono text-muted">{item.share}%</span>
                          </div>
                          <div className="dual-bar-track">
                            <div className="dual-bar-fill auc" style={{ width: `${item.share * 3.5}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="benchmark-candidate-note mt-4">
                    <strong>Clinical consistency:</strong> Prior inpatient utilization and hospital stay length are the strongest independent predictors of 30-day readmission across both parametric odds ratios and tree splits, aligning directly with established LACE and HOSPITAL readmission scoring indices.
                  </div>
                </motion.div>
              </div>

              {/* SECTION 5: INTENDED USE & GOVERNANCE SCOPE */}
              <motion.div
                className="card-panel"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                <div className="panel-header-row">
                  <div className="panel-title-text">
                    <h2>Intended Use & Clinical Scope</h2>
                    <p>Context: CMS Hospital Readmissions Reduction Program (HRRP)</p>
                  </div>
                </div>

                <div className="intended-use-list">
                  <div className="intended-use-row">
                    <div className="intended-use-header">
                      <Users className="w-4 h-4 text-brand" />
                      <span>Intended Operator</span>
                    </div>
                    <p className="intended-use-body">
                      Hospital Discharge Planners, Nurse Navigators, and Care Coordinators evaluating transitional care needs.
                    </p>
                  </div>

                  <div className="intended-use-row">
                    <div className="intended-use-header">
                      <ShieldCheck className="w-4 h-4 text-brand" />
                      <span>Human-in-the-Loop Safeguard</span>
                    </div>
                    <p className="intended-use-body">
                      The predicted readmission risk must accompany bedside clinical assessments. The model provides assistive probabilistic signals, not autonomous clinical directives. Treatment decisions remain under attending physician authority.
                    </p>
                  </div>

                  <div className="intended-use-row">
                    <div className="intended-use-header">
                      <Database className="w-4 h-4 text-brand" />
                      <span>Data Provenance</span>
                    </div>
                    <p className="intended-use-body">
                      Published as de-identified by its source (UCI Machine Learning Repository, 130 US hospitals, 1999-2008). We did not independently verify de-identification.
                    </p>
                  </div>

                  <div className="intended-use-row limitation">
                    <div className="intended-use-header">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Known Limitations</span>
                    </div>
                    <p className="intended-use-body">
                      Retrospective cohort of 99,343 inpatient encounters (69,990 unique patients; training n = 69,538, validation n = 9,935, holdout test n = 19,870; 500 = interactive demo sample). Modest discrimination (AUC ~0.65) reflecting historical administrative EHR data limitations. Data collected between 1999 and 2008 from diabetic inpatients only; lacks external or prospective bedside clinical validation. Subgroups with &lt;100 readmissions (Asian n=124, Hispanic n=405, Other n=308, &lt;30 Years n=512) are too small to establish statistical parity. Algorithmic fairness was evaluated on three recorded demographic attributes only (race, sex, age); clinical comorbidities may correlate with demographic distributions.
                    </p>
                  </div>
                </div>
              </motion.div>
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
                          : reviewRecord.tier?.toLowerCase().startsWith("elevated") || reviewRecord.tier?.toLowerCase().startsWith("mod")
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
                setTier("flagged");
                setPage(1);
                setView("worklist");
                setOpenPalette(false);
                toast.info("Filtered worklist to Flagged for follow-up (≥12%)");
              }}
            >
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span>Show Flagged Encounters (≥12%)</span>
              <span className="cmdk-shortcut">F</span>
            </Command.Item>
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
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span>Show High Risk Encounters (≥20%)</span>
              <span className="cmdk-shortcut">H</span>
            </Command.Item>
            <Command.Item
              className="cmdk-item"
              onSelect={() => {
                setTier("elevated");
                setPage(1);
                setView("worklist");
                setOpenPalette(false);
                toast.info("Filtered worklist to Elevated Risk (12–20%)");
              }}
            >
              <AlertCircle className="w-4 h-4 text-amber-500" />
              <span>Show Elevated Risk Encounters (12–20%)</span>
              <span className="cmdk-shortcut">E</span>
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
                  <li><strong>Low Risk (&lt;12%):</strong> 72.2% of cohort (361 encounters). Standard discharge summary and routine 30-day primary care appointment.</li>
                  <li><strong>Elevated Risk (12–20%):</strong> 22.8% of cohort (114 encounters). At or above the validated clinical cutoff; enhanced transition planning, 7–10 day follow-up, and pharmacy consult.</li>
                  <li><strong>High Risk (≥20%):</strong> 5.0% of cohort (25 encounters). Top risk decile; multidisciplinary discharge care plan, 48-hour telehealth outreach, and CDCES educator consult.</li>
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

      {/* Shared Portal Tooltip */}
      <SharedTooltip tooltip={sharedTooltip} />

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
