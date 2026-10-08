import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./responsive.css";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const AGE_GROUPS = ["All ages", "<30 Years", "30-60 Years", "60+ Years"];
const DIAGNOSES = ["Circulatory", "Respiratory", "Digestive", "Diabetes", "Injury", "Musculoskeletal", "Genitourinary", "Neoplasms", "Other"];
const A1C_OPTIONS = [">8", ">7", "Norm", "None"];

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const detail = (await response.json()).detail;
      if (typeof detail === "string") message = detail;
      else if (Array.isArray(detail)) message = detail.map((item) => item.msg).filter(Boolean).join(". ") || message;
    } catch { /* keep status message */ }
    throw new Error(message);
  }
  return response.json();
}

function prettyPercent(value, digits = 1) {
  return `${(Number(value || 0) * 100).toFixed(digits)}%`;
}

function Icon({ children, className = "" }) {
  return <span aria-hidden="true" className={`icon ${className}`}>{children}</span>;
}

function RiskBadge({ tier }) {
  const kind = tier?.toLowerCase().startsWith("high") ? "high" : tier?.toLowerCase().startsWith("moderate") ? "moderate" : "low";
  return <span className={`risk-badge ${kind}`}><i />{tier || "Unscored"}</span>;
}

function MetricCard({ label, value, detail, tone = "blue", icon }) {
  return <article className="metric-card">
    <div className={`metric-icon ${tone}`}><Icon>{icon}</Icon></div>
    <div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
  </article>;
}

function Notice({ children, compact = false }) {
  return <div className={`notice ${compact ? "compact" : ""}`}><Icon>!</Icon><span>{children}</span></div>;
}

function App() {
  const [view, setView] = useState("worklist");
  const [status, setStatus] = useState("connecting");
  const [error, setError] = useState("");
  const [worklist, setWorklist] = useState({ results: [], summary: {}, total: 0, pages: 1 });
  const [sampleRows, setSampleRows] = useState([]);
  const [governance, setGovernance] = useState(null);
  const [page, setPage] = useState(1);
  const [tier, setTier] = useState("all");
  const [ageGroup, setAgeGroup] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [reviewRecord, setReviewRecord] = useState(null);
  const [reviewPrediction, setReviewPrediction] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  const loadWorklist = useCallback(async () => {
    const params = new URLSearchParams({ page: String(page), page_size: "25", tier, age_group: ageGroup, search });
    const result = await api(`/api/worklist?${params}`);
    setWorklist(result);
  }, [page, tier, ageGroup, search]);

  useEffect(() => {
    let alive = true;
    Promise.all([
      api("/api/health"),
      api("/api/worklist?page=1&page_size=25"),
      api("/api/worklist?page=1&page_size=500"),
      api("/api/governance"),
    ]).then(([health, firstPage, cohort, audit]) => {
      if (!alive) return;
      setStatus(health.status === "ok" ? "online" : "offline");
      setWorklist(firstPage);
      setSampleRows(cohort.results);
      setGovernance(audit);
      setSelectedId(cohort.results[0]?.enc_id || "");
      setError("");
    }).catch((err) => {
      if (!alive) return;
      setStatus("offline");
      setError(err.message || "Could not connect to the scoring service.");
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (status !== "online") return;
    let alive = true;
    const timer = window.setTimeout(() => {
      loadWorklist().catch((err) => alive && setError(err.message));
    }, 180);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [loadWorklist, status]);

  const currentEncounter = useMemo(
    () => sampleRows.find((row) => row.enc_id === selectedId) || null,
    [sampleRows, selectedId],
  );

  useEffect(() => {
    if (!currentEncounter) return;
    setDraft({
      time_in_hospital: currentEncounter.stay,
      num_medications: currentEncounter.meds,
      number_inpatient: currentEncounter.inpatient,
      number_emergency: currentEncounter.er,
      A1Cresult: A1C_OPTIONS.includes(currentEncounter.a1c) ? currentEncounter.a1c : "None",
      diag_1_cat: DIAGNOSES.includes(currentEncounter.diag) ? currentEncounter.diag : "Other",
    });
    setPrediction(null);
  }, [currentEncounter]);

  const score = async (encId, values, setter) => {
    setter(null);
    setScoring(true);
    try {
      setter(await api("/api/predict", { method: "POST", body: JSON.stringify({ enc_id: encId, ...values }) }));
    } catch (err) {
      setError(err.message || "Risk scoring failed.");
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
      const result = await api("/api/predict", { method: "POST", body: JSON.stringify({ enc_id: record.enc_id, ...defaultValues }) });
      setReviewPrediction(result);
    } catch (err) {
      setError(err.message || "Could not load the encounter review.");
    } finally {
      setReviewLoading(false);
    }
  };

  const changeView = (next) => { setView(next); setError(""); };
  const summary = worklist.summary || {};

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><span>+</span></div><div><strong>ClinicalAI</strong><small>READMISSION INSIGHTS</small></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="nav-list" aria-label="Main navigation">
        <button className={view === "worklist" ? "active" : ""} onClick={() => changeView("worklist")}><Icon>▤</Icon>Discharge worklist</button>
        <button className={view === "calculator" ? "active" : ""} onClick={() => changeView("calculator")}><Icon>⌁</Icon>Risk calculator</button>
        <button className={view === "governance" ? "active" : ""} onClick={() => changeView("governance")}><Icon>◫</Icon>Model governance</button>
      </nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-status"><div className="status-heading"><span className={`status-dot ${status}`} />API service <span className="status-word">{status === "online" ? "Online" : status === "connecting" ? "Connecting" : "Offline"}</span></div><small>Model: Calibrated ensemble</small></div>
      <div className="profile"><div className="avatar">RD</div><div><strong>Research demo</strong><small>Read-only workspace</small></div><span className="profile-more">···</span></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="mobile-brand"><div className="brand-mark"><span>+</span></div><strong>ClinicalAI</strong></div><div className="breadcrumbs"><span>ClinicalAI</span><b>/</b><strong>{view === "worklist" ? "Discharge worklist" : view === "calculator" ? "Risk calculator" : "Model governance"}</strong></div><div className="top-actions"><span className="environment-tag"><i />DEMO ENVIRONMENT</span><button className="help-button" title="Research demo information" onClick={() => setView("governance")}>?</button></div></header>

      <div className="page-content">
        <div className="page-title-row"><div><div className="eyebrow">CLINICAL DECISION SUPPORT · RESEARCH DEMO</div><h1>{view === "worklist" ? "Discharge readiness" : view === "calculator" ? "Bedside risk calculator" : "Model governance"}</h1><p>{view === "worklist" ? "Review a de-identified historical cohort scored for 30-day readmission." : view === "calculator" ? "Explore how selected clinical factors change a historical model score." : "Validation performance and fairness audit summaries for the demo model."}</p></div><span className="dataset-pill"><span /> Public de-identified dataset</span></div>
        <Notice>Research demonstration using historical, de-identified data. This model is not validated for patient care. Do not enter identifiable patient information or use predictions to make clinical decisions.</Notice>
        {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}

        {view === "worklist" && <>
          <section className="metric-grid">
            <MetricCard label="Scored encounters" value={summary.cohort_size ?? "—"} detail="Pre-scored demo cohort" icon="▤" tone="blue" />
            <MetricCard label="High-risk flags" value={summary.high_risk ?? "—"} detail={`${summary.cohort_size ? ((summary.high_risk / summary.cohort_size) * 100).toFixed(1) : "—"}% at ≥20% model score`} icon="⌁" tone="red" />
            <MetricCard label="Polypharmacy" value={summary.polypharmacy ?? "—"} detail="10 or more active medications" icon="✚" tone="amber" />
            <MetricCard label="Observed readmissions" value={summary.readmissions ?? "—"} detail="Historical cohort outcome" icon="↗" tone="green" />
          </section>
          <section className="panel worklist-panel">
            <div className="panel-heading"><div><h2>Encounter queue</h2><p>Risk-ranked historical encounters from the evaluation cohort</p></div><span className="record-count">{worklist.total} records</span></div>
            <div className="filters">
              <label className="search-box"><Icon>⌕</Icon><input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search encounter ID" aria-label="Search encounter ID" /><kbd>⌘ K</kbd></label>
              <label className="filter-select"><span>Risk level</span><select value={tier} onChange={(e) => { setTier(e.target.value); setPage(1); }}><option value="all">All risk levels</option><option value="high">High risk</option><option value="moderate">Moderate risk</option><option value="low">Low risk</option></select></label>
              <label className="filter-select"><span>Age group</span><select value={ageGroup} onChange={(e) => { setAgeGroup(e.target.value === "All ages" ? "all" : e.target.value); setPage(1); }}>{AGE_GROUPS.map((group) => <option key={group} value={group}>{group}</option>)}</select></label>
            </div>
            <div className="table-wrap"><table><thead><tr><th>ENCOUNTER</th><th>PROFILE</th><th>STAY</th><th>MEDS</th><th>PRIOR ACUTE</th><th>CARE FLAGS</th><th>RISK SCORE</th><th /></tr></thead>
              <tbody>{worklist.results.map((record) => <tr key={record.enc_id}>
                <td><strong className="enc-id">{record.enc_id}</strong><small>Historical cohort</small></td>
                <td><strong>{record.age}</strong><small>{record.gender} · {record.race}</small></td>
                <td>{record.stay}<small>days</small></td><td>{record.meds}<small>active</small></td>
                <td>{record.inpatient} inpatient <small>{record.er} ER visits</small></td>
                <td><div className="flag-list">{record.resources.slice(0, 2).map((flag) => <span key={flag}>{flag}</span>)}</div></td>
                <td><div className="score-cell"><strong className={`score-${record.tier.toLowerCase().split(" ")[0]}`}>{prettyPercent(record.prob)}</strong><RiskBadge tier={record.tier} /></div></td>
                <td><button className="text-button" onClick={() => openReview(record)}>Review <span>›</span></button></td>
              </tr>)}</tbody>
            </table>
              {!worklist.results.length && <div className="empty-state"><strong>No matching encounters</strong><span>Adjust the filters or clear the search.</span></div>}
            </div>
            <div className="table-footer"><span>Showing {worklist.results.length ? (page - 1) * 25 + 1 : 0}–{Math.min(page * 25, worklist.total)} of {worklist.total}</span><div className="pagination"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button><span>Page {page} of {worklist.pages || 1}</span><button disabled={page >= (worklist.pages || 1)} onClick={() => setPage(page + 1)}>Next →</button></div></div>
          </section>
          <div className="source-note"><Icon>i</Icon><span>Historical records are drawn from the public Diabetes 130-US Hospitals dataset. Encounter labels and cohort outcomes are included for demonstration only.</span></div>
        </>}

        {view === "calculator" && <section className="calculator-grid">
          <div className="panel input-panel"><div className="panel-heading"><div><h2>Scenario inputs</h2><p>Start from a cohort encounter, then adjust the demo values.</p></div><span className="step-number">01</span></div>
            <label className="field-label">Starting encounter<select className="field-control" value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>{sampleRows.map((row) => <option key={row.enc_id} value={row.enc_id}>{row.enc_id} · {row.age} · {row.tier}</option>)}</select></label>
            {currentEncounter && <div className="selected-summary"><span className="summary-avatar">{currentEncounter.age_group === "60+ Years" ? "60+" : currentEncounter.age_group === "30-60 Years" ? "30–60" : "<30"}</span><div><strong>{currentEncounter.enc_id}</strong><small>{currentEncounter.age} · {currentEncounter.gender} · {currentEncounter.race}</small></div><RiskBadge tier={currentEncounter.tier} /></div>}
            <div className="field-grid">
              <label className="field-label">Hospital stay <span className="input-suffix"><input type="number" min="1" max="14" value={draft?.time_in_hospital ?? ""} onChange={(e) => setDraft({ ...draft, time_in_hospital: Number(e.target.value) })} /><small>days</small></span></label>
              <label className="field-label">Active medications <span className="input-suffix"><input type="number" min="1" max="50" value={draft?.num_medications ?? ""} onChange={(e) => setDraft({ ...draft, num_medications: Number(e.target.value) })} /><small>count</small></span></label>
              <label className="field-label">Prior inpatient admissions <span className="input-suffix"><input type="number" min="0" max="10" value={draft?.number_inpatient ?? ""} onChange={(e) => setDraft({ ...draft, number_inpatient: Number(e.target.value) })} /><small>count</small></span></label>
              <label className="field-label">Prior emergency visits <span className="input-suffix"><input type="number" min="0" max="10" value={draft?.number_emergency ?? ""} onChange={(e) => setDraft({ ...draft, number_emergency: Number(e.target.value) })} /><small>count</small></span></label>
              <label className="field-label">A1C result<select className="field-control" value={draft?.A1Cresult ?? "None"} onChange={(e) => setDraft({ ...draft, A1Cresult: e.target.value })}>{A1C_OPTIONS.map((value) => <option key={value}>{value}</option>)}</select></label>
              <label className="field-label">Primary diagnosis group<select className="field-control" value={draft?.diag_1_cat ?? "Other"} onChange={(e) => setDraft({ ...draft, diag_1_cat: e.target.value })}>{DIAGNOSES.map((value) => <option key={value}>{value}</option>)}</select></label>
            </div>
            <div className="input-footnote"><Icon>i</Icon><span>Inputs are held in this browser session and sent to the public demo API for scoring. No scenario is saved.</span></div>
            <button className="primary-button" disabled={!currentEncounter || !draft || scoring} onClick={() => score(selectedId, draft, setPrediction)}>{scoring ? <><span className="spinner" /> Calculating…</> : <>Calculate demo risk <span>→</span></>}</button>
          </div>
          <div className="panel result-panel"><div className="panel-heading"><div><h2>Risk estimate</h2><p>Calibrated ensemble · 30-day readmission</p></div><span className="step-number">02</span></div>
            {!prediction && <div className="result-placeholder"><div className="placeholder-icon">⌁</div><strong>Run a scenario to view its score</strong><span>The estimate and supporting factors will appear here.</span></div>}
            {prediction && <div className="result-content"><div className="risk-meter"><div className="meter-value">{prettyPercent(prediction.probability)}</div><div className={`meter-track ${prediction.color}`}><span style={{ width: `${Math.min(100, prediction.probability * 250)}%` }} /></div><div className="meter-scale"><span>0%</span><span>12%</span><span>20%</span><span>40%+</span></div><RiskBadge tier={prediction.tier} /></div>
              <div className={`guidance-box ${prediction.color}`}><strong>Decision support summary</strong><p>{prediction.guidance}</p></div>
              <div className="result-subheading"><strong>Targeted care bundles</strong><span>{prediction.interventions.length} suggestions</span></div>
              <div className="intervention-list">{prediction.interventions.map((item, index) => <div className="intervention-item" key={`${item.Category}-${index}`}><span className="intervention-check">✓</span><div><strong>{item.Recommendation}</strong><small>{item.Rationale}</small></div></div>)}</div>
              {!!prediction.top_factors?.length && <div className="drivers"><div className="result-subheading"><strong>Model factors</strong><span>Relative influence</span></div>{prediction.top_factors.slice(0, 4).map((factor) => <div className="driver-row" key={factor.feature}><span>{factor.feature}</span><i><b style={{ width: `${Math.max(8, Math.min(100, Math.abs(factor.impact) * 220))}%` }} /></i></div>)}</div>}
              <div className="small-disclaimer">Scores support a research demonstration only and should not be used to guide care.</div>
            </div>}
          </div>
        </section>}

        {view === "governance" && <>
          <section className="metric-grid governance-metrics"><MetricCard label="Selected model" value="Calibrated ensemble" detail="Gradient-boosting soft vote" icon="✧" tone="blue" /><MetricCard label="Evaluation cohort" value="19,870" detail="Held-out encounters" icon="▤" tone="green" /><MetricCard label="AUC-ROC" value="66.4%" detail="Discrimination metric" icon="⌁" tone="violet" /><MetricCard label="Recall" value="53.4%" detail="At selected operating threshold" icon="↗" tone="amber" /></section>
          <div className="governance-grid"><section className="panel benchmark-panel"><div className="panel-heading"><div><h2>Model benchmark</h2><p>Held-out cohort performance comparison</p></div><span className="legend"><i className="auc-dot" />AUC-ROC <i className="recall-dot" />Recall</span></div>
            <div className="benchmark-list">{(governance?.models || []).map((model) => <div className="benchmark-row" key={model.Model}><div className="benchmark-label"><strong>{model.Model}</strong>{model.Model === governance?.selected_model && <span>SELECTED</span>}</div><div className="bar-metric"><small>AUC</small><div className="benchmark-track"><i style={{ width: `${Number(model["AUC-ROC"] || 0) * 100}%` }} /></div><b>{prettyPercent(model["AUC-ROC"], 1)}</b></div><div className="bar-metric recall"><small>Recall</small><div className="benchmark-track"><i style={{ width: `${Number(model["Recall (Sensitivity)"] || 0) * 100}%` }} /></div><b>{prettyPercent(model["Recall (Sensitivity)"], 1)}</b></div></div>)}</div>
            <div className="governance-footnote">Performance reflects the repository’s saved evaluation artifacts and may not generalize to other populations.</div>
          </section>
          <section className="panel fairness-panel"><div className="panel-heading"><div><h2>Fairness audit</h2><p>Equalized-odds TPR disparity</p></div><span className="audit-tag">AUDITED</span></div>
            <div className="fairness-cards">{[ ["Age group", governance?.fairness?.age_group], ["Race", governance?.fairness?.race_clean], ["Gender", governance?.fairness?.gender_clean] ].map(([label, item]) => <div className="fairness-row" key={label}><div><strong>{label}</strong><small>TPR disparity</small></div><div className="fairness-values"><span><small>Baseline</small><b>{prettyPercent(item?.baseline?.equalized_odds_tpr_diff)}</b></span><span><small>Mitigated</small><b className="mitigated-value">{prettyPercent(item?.mitigated?.equalized_odds_tpr_diff)}</b></span><span className="improvement">↓</span></div></div>)}</div>
            <div className="governance-footnote">Fairness metrics summarize this evaluation dataset; subgroup parity does not establish clinical safety or regulatory compliance.</div>
          </section></div>
          <Notice compact>Metrics and fairness audits are historical results from the checked-in model artifacts. They are not a substitute for external validation, clinical oversight, or regulatory review.</Notice>
        </>}
      </div>
    </main>

    <nav className="mobile-nav" aria-label="Mobile navigation">
      <button className={view === "worklist" ? "active" : ""} aria-label="Discharge worklist" aria-current={view === "worklist" ? "page" : undefined} onClick={() => changeView("worklist")}>
        <Icon>▤</Icon><span>Worklist</span>
      </button>
      <button className={view === "calculator" ? "active" : ""} aria-label="Risk calculator" aria-current={view === "calculator" ? "page" : undefined} onClick={() => changeView("calculator")}>
        <Icon>⌁</Icon><span>Calculator</span>
      </button>
      <button className={view === "governance" ? "active" : ""} aria-label="Model governance" aria-current={view === "governance" ? "page" : undefined} onClick={() => changeView("governance")}>
        <Icon>◫</Icon><span>Governance</span>
      </button>
    </nav>

    {reviewRecord && <div className="modal-backdrop" role="presentation" onClick={() => setReviewRecord(null)}><section className="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title" onClick={(e) => e.stopPropagation()}><button className="modal-close" aria-label="Close review" onClick={() => setReviewRecord(null)}>×</button><div className="modal-eyebrow">HISTORICAL COHORT ENCOUNTER</div><div className="modal-title"><div><h2 id="review-title">{reviewRecord.enc_id}</h2><p>{reviewRecord.age} · {reviewRecord.gender} · {reviewRecord.race}</p></div><RiskBadge tier={reviewRecord.tier} /></div><div className="review-score"><span>Saved model score</span><strong>{prettyPercent(reviewRecord.prob)}</strong></div><div className="review-facts"><span><small>Length of stay</small><strong>{reviewRecord.stay} days</strong></span><span><small>Medications</small><strong>{reviewRecord.meds} active</strong></span><span><small>A1C result</small><strong>{reviewRecord.a1c}</strong></span><span><small>Primary group</small><strong>{reviewRecord.diag}</strong></span></div><div className="modal-section-title">Care bundle preview</div>{reviewLoading && <div className="loading-line"><span className="spinner" /> Loading encounter suggestions</div>}{reviewPrediction && <div className="intervention-list">{reviewPrediction.interventions.map((item, index) => <div className="intervention-item" key={index}><span className="intervention-check">✓</span><div><strong>{item.Recommendation}</strong><small>{item.Rationale}</small></div></div>)}</div>}<Notice compact>Preview only. No EHR connection or care order is available in this demo.</Notice><button className="secondary-button" onClick={() => { setSelectedId(reviewRecord.enc_id); setView("calculator"); setReviewRecord(null); }}>Adjust scenario in calculator <span>→</span></button></section></div>}
  </div>;
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
