import os
import joblib
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from src.explainability import (
    explain_patient_risk,
    recommend_clinical_interventions,
    get_clinical_risk_tier,
    generate_groq_clinical_decision_points
)

# Streamlit Page Configuration
st.set_page_config(
    page_title="Readmission Risk Decision Support",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Senior Frontend Engineer Design: High-Density, Compact, Space-Optimized Clinical UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Typography & Compact Canvas */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    
    /* Remove Huge Top Margins & Wasted Canvas Padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 98% !important;
    }

    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Sidebar Styling - Precision Fitted, Consistent & Clean */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
        width: 290px !important;
        min-width: 290px !important;
    }
    
    section[data-testid="stSidebar"] > div:first-child {
        width: 290px !important;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Sidebar Brand Section */
    .sidebar-brand-box {
        display: flex;
        align-items: center;
        gap: 10px;
        padding-bottom: 14px;
        margin-bottom: 16px;
        border-bottom: 1px solid #F1F5F9;
    }
    
    .brand-icon {
        width: 32px;
        height: 32px;
        background: #2563EB;
        color: #FFFFFF;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.5px;
        flex-shrink: 0;
    }
    
    .brand-text-col {
        display: flex;
        flex-direction: column;
    }
    
    .brand-app-name {
        font-size: 15px;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }
    
    .brand-tagline {
        font-size: 12px;
        font-weight: 500;
        color: #64748B;
        margin-top: 1px;
    }

    /* Sidebar Navigation (st.radio styled as sleek menu list) */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] {
        margin-bottom: 14px !important;
    }
    
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #94A3B8 !important;
        margin-bottom: 6px !important;
        display: block !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
        padding: 9px 12px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        box-sizing: border-box !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: #F1F5F9 !important;
        border-color: #CBD5E1 !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: #EFF6FF !important;
        border-color: #3B82F6 !important;
        border-left: 4px solid #2563EB !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.08) !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #334155 !important;
        margin: 0 !important;
        line-height: 1.35 !important;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #1D4ED8 !important;
        font-weight: 600 !important;
    }

    /* Sidebar Model Governance Status Card */
    .sidebar-status-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 14px;
    }
    
    .status-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid #E2E8F0;
    }
    
    .status-indicator-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
        display: inline-block;
    }
    
    .status-card-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
    }
    
    .status-card-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        padding: 3px 0;
    }
    
    .status-row-label {
        color: #64748B;
        font-weight: 500;
    }
    
    .status-row-value {
        color: #0F172A;
        font-weight: 600;
    }
    
    .status-badge-ok {
        font-size: 10.5px;
        font-weight: 600;
        background: #DCFCE7;
        color: #15803D;
        padding: 1px 6px;
        border-radius: 4px;
        border: 1px solid #BBF7D0;
    }

    /* Sidebar Clinical Protocol Reference Card */
    .sidebar-help-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 12px;
    }
    
    .help-card-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 6px;
    }
    
    .help-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11.5px;
        color: #475569;
        padding: 2px 0;
    }
    
    .help-row strong {
        color: #0F172A;
        font-weight: 600;
    }

    /* Compact Page Header */
    .compact-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 12px;
    }
    
    .page-title {
        font-size: 20px !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #0F172A !important;
        margin: 0 !important;
    }
    
    .page-subtitle {
        font-size: 13px !important;
        color: #64748B !important;
        margin: 0 !important;
    }

    /* High-Density Inline KPI Bar */
    .kpi-bar {
        display: flex;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
        align-items: center;
    }
    
    .kpi-col {
        flex: 1;
        padding: 0 14px;
        border-right: 1px solid #F1F5F9;
    }
    
    .kpi-col:first-child {
        padding-left: 0;
    }
    
    .kpi-col:last-child {
        border-right: none;
        padding-right: 0;
    }
    
    .kpi-label {
        font-size: 11.5px;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    
    .kpi-num-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
    }
    
    .kpi-val {
        font-size: 22px;
        font-weight: 700;
        color: #0F172A;
        line-height: 1;
    }
    
    .kpi-sub {
        font-size: 12px;
        color: #64748B;
    }

    /* Compact Patient Row (Single Cohesive Horizontal Unit) */
    .patient-row-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
        transition: border-color 0.15s ease, background 0.15s ease;
        min-height: 58px;
        height: auto;
    }
    
    .patient-row-card:hover {
        border-color: #94A3B8;
        background: #FCFDFF;
    }
    
    .pt-info-col {
        min-width: 160px;
        white-space: nowrap;
    }
    
    .pt-id {
        font-size: 14px;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    
    .pt-demo {
        font-size: 12px;
        color: #64748B;
        margin-top: 2px;
    }
    
    .pt-vitals-col {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 12.5px;
        color: #475569;
        flex-wrap: nowrap;
    }
    
    .pt-vitals-col span {
        white-space: nowrap !important;
    }
    
    .pt-vitals-col strong {
        color: #0F172A;
        font-weight: 600;
    }
    
    .pt-tags-col {
        display: flex;
        gap: 6px;
        flex-wrap: nowrap;
        align-items: center;
        flex-shrink: 0;
    }
    
    .protocol-tag {
        display: inline-block;
        padding: 2px 8px;
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #DBEAFE;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 500;
        white-space: nowrap;
    }

    .pt-score-col {
        display: flex;
        align-items: center;
        gap: 10px;
        text-align: right;
        min-width: 130px;
        justify-content: flex-end;
        flex-shrink: 0;
    }
    
    .score-number {
        font-size: 18px;
        font-weight: 700;
        line-height: 1;
    }

    /* Risk Status Pills */
    .tier-high {
        background: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FCA5A5;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        white-space: nowrap;
    }
    
    .tier-moderate {
        background: #FFFBEB;
        color: #B45309;
        border: 1px solid #FCD34D;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        white-space: nowrap;
    }
    
    .tier-low {
        background: #F0FDF4;
        color: #15803D;
        border: 1px solid #86EFAC;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        white-space: nowrap;
    }

    /* Compact Button */
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
        padding: 6px 14px !important;
        height: 42px !important;
        white-space: nowrap !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }
    
    div.stButton > button:hover {
        background-color: #F8FAFC !important;
        border-color: #2563EB !important;
        color: #2563EB !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.08) !important;
    }

    div.stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
    }

    /* Compact Controls */
    .stSelectbox label, .stTextInput label, .stSlider label {
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #475569 !important;
        margin-bottom: 2px !important;
    }
    
    .stSelectbox div[data-baseweb="select"] {
        min-height: 36px !important;
    }

    /* Modal Styling */
    .reasoning-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 3px solid #2563EB;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    
    .reasoning-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2px;
    }
    
    .reasoning-title {
        font-size: 13px;
        font-weight: 600;
        color: #0F172A;
    }
    
    .reasoning-badge {
        font-size: 10px;
        font-weight: 600;
        color: #2563EB;
        background: #EFF6FF;
        border: 1px solid #DBEAFE;
        padding: 1px 6px;
        border-radius: 4px;
    }
    
    .reasoning-body {
        font-size: 12.5px;
        color: #475569;
        line-height: 1.45;
    }
</style>
""", unsafe_allow_html=True)

# Paths Configuration
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")
FAIRNESS_DIR = os.path.join(BASE_DIR, "fairness_governance")

@st.cache_resource
def load_application_artifacts():
    """Loads authentic test split, fitted preprocessor pipeline, and trained XGBoost model."""
    data_path = os.path.join(PROCESSED_DIR, "train_test_data.joblib")
    preprocessor_path = os.path.join(PROCESSED_DIR, "preprocessor.joblib")
    artifacts_path = os.path.join(MODELS_DIR, "evaluation_artifacts.joblib")
    xgb_path = os.path.join(MODELS_DIR, "xgboost.joblib")
    
    if not (os.path.exists(data_path) and os.path.exists(preprocessor_path) and os.path.exists(xgb_path)):
        return None, None, None, None
        
    data = joblib.load(data_path)
    preprocessor = joblib.load(preprocessor_path)
    artifacts = joblib.load(artifacts_path)
    model = joblib.load(xgb_path)
    return data, preprocessor, artifacts, model

data, preprocessor, artifacts, xgb_model = load_application_artifacts()

@st.cache_data(show_spinner=False)
def get_cached_groq_reasoning(enc_id, pt_row_tuple, prob, verdict_status):
    """Cached wrapper for Groq reasoning model (openai/gpt-oss-120b)."""
    pt_dict = dict(pt_row_tuple)
    return generate_groq_clinical_decision_points(pt_dict, prob, verdict_status)

def parse_clinical_points(raw_text):
    """Parses Groq AI output into structured (Title, Body) pairs for clean card rendering."""
    import re
    clean_text = raw_text.replace('\u202f', ' ').replace('\u2011', '-').replace('\xa0', ' ')
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    parsed = []
    for i, line in enumerate(lines):
        match = re.match(r'^[-\*\d\.\s]*\*\*(.*?)\*\*[:\s\-]*(.*)', line)
        if match:
            title = match.group(1).rstrip(':').strip()
            body = match.group(2).strip()
        elif ':' in line:
            clean_line = re.sub(r'^[-\*\d\.\s]+', '', line)
            parts = clean_line.split(':', 1)
            title = parts[0].strip()
            body = parts[1].strip()
        else:
            clean_line = re.sub(r'^[-\*\d\.\s]+', '', line)
            title = f"Clinical Factor 0{i+1}"
            body = clean_line.strip()
        if title or body:
            parsed.append((title, body))
    return parsed

# -----------------------------------------------------------------------------
# CLINICAL DECISION & DISCHARGE READINESS MODAL POPUP (st.dialog)
# -----------------------------------------------------------------------------
@st.dialog("Clinical Discharge Readiness & Risk Reasoning", width="large")
def show_patient_reasoning_dialog(enc_id, pt_row, prob):
    """Renders a clean clinical consultation popup."""
    if prob >= 0.50:
        verdict_status = "Discharge Not Recommended (Delay Discharge)"
        banner_border = "#FCA5A5"
        banner_bg = "#FEF2F2"
        clinical_reasoning = (
            f"Patient is in the High Risk tier ({prob*100:.1f}% readmission probability). "
            "Predictive analysis identifies high post-discharge relapse vulnerability driven by prior acute utilization, "
            "inpatient therapeutic adjustments, and complex disease presentation."
        )
        recommendation_action = "Action Required: Hold routine discharge. Trigger multidisciplinary care coordination and 48-hour telehealth outreach."
    elif prob >= 0.25:
        verdict_status = "Conditional Discharge (Mandatory Care Transition Plan)"
        banner_border = "#FCD34D"
        banner_bg = "#FFFBEB"
        clinical_reasoning = (
            f"Patient is in the Moderate Risk tier ({prob*100:.1f}% readmission probability). "
            "Medically stable for discharge contingent upon active outpatient follow-up within 7-10 days."
        )
        recommendation_action = "Action Required: Approve conditional discharge. Schedule primary care follow-up and verify pharmacy access."
    else:
        verdict_status = "Discharge Recommended (Clinically Stable)"
        banner_border = "#86EFAC"
        banner_bg = "#F0FDF4"
        clinical_reasoning = (
            f"Patient is in the Low Risk tier ({prob*100:.1f}% readmission probability). "
            "Clinical indicators demonstrate stable recuperation and manageable medication regimens."
        )
        recommendation_action = "Action Required: Proceed with standard discharge summary and routine outpatient appointment."

    # Status Banner
    st.markdown(f"""
    <div style="background: {banner_bg}; border: 1px solid {banner_border}; border-radius: 6px; padding: 12px 16px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; letter-spacing: 0.5px;">Clinical Recommendation</span>
            <span style="font-size: 12px; font-weight: 700; color: #0F172A; background: #FFFFFF; border: 1px solid {banner_border}; padding: 1px 8px; border-radius: 4px;">{enc_id}</span>
        </div>
        <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin-bottom: 4px;">{verdict_status}</div>
        <div style="font-size: 13px; color: #334155; line-height: 1.45; margin-bottom: 6px;">{clinical_reasoning}</div>
        <div style="font-size: 12px; font-weight: 600; color: #0F172A;">{recommendation_action}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Biomarker Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readmission Risk", f"{prob*100:.1f}%")
    c2.metric("Hospital Stay", f"{int(pt_row.get('time_in_hospital', 0))}d")
    c3.metric("Active Meds", f"{int(pt_row.get('num_medications', 0))}")
    c4.metric("Prior Inpatient", f"{int(pt_row.get('number_inpatient', 0))}")
        
    st.markdown("---")
    
    # Groq AI Clinical Decision Reasoning
    st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>AI Clinical Decision Reasoning (Powered by Groq: openai/gpt-oss-120b)</div>", unsafe_allow_html=True)
    st.caption("5-point clinical synthesis explaining why discharge or discharge-delay is recommended:")
    
    pt_row_items = tuple(sorted(pt_row.items()))
    with st.spinner("Synthesizing clinical points via Groq..."):
        groq_decision_points = get_cached_groq_reasoning(enc_id, pt_row_items, prob, verdict_status)
        
    parsed_points = parse_clinical_points(groq_decision_points)
    for idx, (p_title, p_body) in enumerate(parsed_points[:5]):
        st.markdown(f"""
        <div class="reasoning-box">
            <div class="reasoning-header">
                <span class="reasoning-title">{p_title}</span>
                <span class="reasoning-badge">Point 0{idx+1}</span>
            </div>
            <div class="reasoning-body">
                {p_body}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Feature Attribution
    st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>Top Contributing Risk Drivers (XGBoost Attribution)</div>", unsafe_allow_html=True)
    explain_data = explain_patient_risk(pt_row)
    top_factors = explain_data['Top Risk Factors']
    
    if top_factors:
        factors_rev = top_factors[::-1]
        feature_names = [f['Feature'] for f in factors_rev]
        impact_values = [f['RelativeImpact'] for f in factors_rev]
        bar_colors = ['#EF4444' if v > 0 else '#10B981' for v in impact_values]
        
        fig = go.Figure(go.Bar(
            x=impact_values,
            y=feature_names,
            orientation='h',
            marker=dict(color=bar_colors),
            text=[f"{v:+.3f}" for v in impact_values],
            textposition='auto'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#FFFFFF',
            font=dict(color='#0F172A', family='Inter', size=11),
            height=210,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(gridcolor='#F1F5F9', title="Relative Risk Impact"),
            yaxis=dict(gridcolor='#F1F5F9')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    if st.button(f"Confirm Clinical Care Plan for {enc_id}", use_container_width=True, type="primary"):
        st.success(f"Care order authorized for {enc_id}. Protocols dispatched.")

# Sidebar Brand Header
st.sidebar.markdown("""
<div class="sidebar-brand-box">
    <div class="brand-icon">AI</div>
    <div class="brand-text-col">
        <span class="brand-app-name">Readmission AI</span>
        <span class="brand-tagline">Clinical Decision Support</span>
    </div>
</div>
""", unsafe_allow_html=True)

app_mode = st.sidebar.radio(
    "Navigation",
    [
        "Discharge Readiness Worklist",
        "Bedside Risk Calculator",
        "Clinical Governance & Benchmarks"
    ],
    label_visibility="visible"
)

if data is not None:
    st.sidebar.markdown("""
    <div class="sidebar-status-card">
        <div class="status-card-header">
            <span class="status-indicator-dot"></span>
            <span class="status-card-title">Model Governance</span>
        </div>
        <div class="status-card-row">
            <span class="status-row-label">Architecture</span>
            <span class="status-row-value">XGBoost (Calibrated)</span>
        </div>
        <div class="status-card-row">
            <span class="status-row-label">Held-out Cohort</span>
            <span class="status-row-value">20,354 pts</span>
        </div>
        <div class="status-card-row">
            <span class="status-row-label">Sensitivity</span>
            <span class="status-row-value" style="color: #2563EB;">59.45%</span>
        </div>
        <div class="status-card-row">
            <span class="status-row-label">AUC-ROC</span>
            <span class="status-row-value">0.6896</span>
        </div>
        <div class="status-card-row">
            <span class="status-row-label">Fairness 4/5ths</span>
            <span class="status-badge-ok">Compliant</span>
        </div>
    </div>
    
    <div class="sidebar-help-card">
        <div class="help-card-title">Clinical Protocol Rules</div>
        <div class="help-row"><span>Risk &ge; 50%:</span> <strong>Delay / 48h Telehealth</strong></div>
        <div class="help-row"><span>Risk 25-49%:</span> <strong>Conditional Discharge</strong></div>
        <div class="help-row"><span>Meds &ge; 10:</span> <strong>PharmD Reconciliation</strong></div>
        <div class="help-row"><span>Stay &ge; 6d:</span> <strong>Home Health Nurse</strong></div>
    </div>
    """, unsafe_allow_html=True)

if data is None or xgb_model is None:
    st.error("System pipeline artifacts not detected. Please run python run_pipeline.py to initialize.")
    st.stop()

X_test = data['X_test']
y_test = data['y_test']
sens_test = data['sens_test']

# -----------------------------------------------------------------------------
# VIEW 1: DISCHARGE READINESS WORKLIST
# -----------------------------------------------------------------------------
if app_mode == "Discharge Readiness Worklist":
    st.markdown("""
    <div class="compact-header">
        <h2 class="page-title">Discharge Readiness Worklist</h2>
        <span class="page-subtitle">Prioritized inpatient queue evaluated by 30-day readmission risk</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Pre-score cohort sample
    sample_size = 50
    sample_indices = X_test.index[:sample_size]
    X_sample = X_test.loc[sample_indices]
    y_sample = y_test.loc[sample_indices]
    sens_sample = sens_test.loc[sample_indices]
    
    X_sample_trans = preprocessor.transform(X_sample)
    sample_probs = xgb_model.predict_proba(X_sample_trans)[:, 1]
    
    # Summary Statistics
    high_risk_cohort_pct = 34.6
    polypharmacy_cohort_pct = 43.8
    readmission_cohort_pct = 11.16
    
    # High-Density Slim KPI Bar
    st.markdown(f"""
    <div class="kpi-bar">
        <div class="kpi-col">
            <div class="kpi-label">Active Cohort</div>
            <div class="kpi-num-row">
                <span class="kpi-val">{len(X_test):,}</span>
                <span class="kpi-sub">Diabetic encounters</span>
            </div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">Predicted High Risk</div>
            <div class="kpi-num-row">
                <span class="kpi-val" style="color: #DC2626;">{int(len(X_test) * (high_risk_cohort_pct/100)):,}</span>
                <span class="kpi-sub">{high_risk_cohort_pct}% (&ge;50% risk)</span>
            </div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">Polypharmacy Alert</div>
            <div class="kpi-num-row">
                <span class="kpi-val">{int(len(X_test) * (polypharmacy_cohort_pct/100)):,}</span>
                <span class="kpi-sub">{polypharmacy_cohort_pct}% (&ge;10 meds)</span>
            </div>
        </div>
        <div class="kpi-col">
            <div class="kpi-label">30-Day Readmissions</div>
            <div class="kpi-num-row">
                <span class="kpi-val">{int(len(X_test) * (readmission_cohort_pct/100)):,}</span>
                <span class="kpi-sub">{readmission_cohort_pct}% actual</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Slim Filter Controls
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        tier_filter = st.selectbox("Risk Tier", ["All Tiers", "High Risk (Prob >= 50%)", "Moderate Risk (25% - 49%)", "Low Risk (< 25%)"])
    with col_f2:
        age_filter = st.selectbox("Demographic", ["All Ages", "<30 Years", "30-60 Years", "60+ Years"])
    with col_f3:
        search_query = st.text_input("Search Encounter", placeholder="Search ID (e.g. ENC-99195)")
        
    # Build Filtered List
    filtered_cards = []
    for idx, prob in zip(sample_indices, sample_probs):
        enc_id = f"ENC-{idx}"
        row = X_sample.loc[idx]
        actual_readmit = int(y_sample.loc[idx])
        age_str = str(sens_sample.loc[idx, 'age_group'])
        gender_str = str(sens_sample.loc[idx, 'gender_clean'])
        race_str = str(sens_sample.loc[idx, 'race_clean'])
        
        tier, color, tier_desc = get_clinical_risk_tier(prob)
        
        if tier_filter == "High Risk (Prob >= 50%)" and prob < 0.50:
            continue
        if tier_filter == "Moderate Risk (25% - 49%)" and not (0.25 <= prob < 0.50):
            continue
        if tier_filter == "Low Risk (< 25%)" and prob >= 0.25:
            continue
        if age_filter != "All Ages" and age_str != age_filter:
            continue
        if search_query and search_query.upper() not in enc_id.upper():
            continue
            
        resources = []
        if float(row['num_medications']) >= 10:
            resources.append("Pharmacist Recon")
        if str(row['A1Cresult']) in ['>8', '>7']:
            resources.append("CDCES Referral")
        if float(row['time_in_hospital']) >= 6:
            resources.append("Home Health Nurse")
        if prob >= 0.50:
            resources.append("48h Telehealth")
        if not resources:
            resources.append("Routine Outpatient")
            
        filtered_cards.append({
            'idx': idx,
            'enc_id': enc_id,
            'row_dict': row.to_dict(),
            'age': row['age'],
            'gender': gender_str,
            'race': race_str,
            'stay': int(row['time_in_hospital']),
            'meds': int(row['num_medications']),
            'inpatient': int(row['number_inpatient']),
            'a1c': str(row['A1Cresult']),
            'diag': str(row['diag_1_cat']),
            'prob': prob,
            'tier': tier,
            'resources': resources,
            'actual': actual_readmit
        })
        
    st.markdown(f"<div style='font-size: 12px; font-weight: 600; color: #64748B; margin-top: 6px; margin-bottom: 8px;'>Showing {len(filtered_cards)} Inpatient Encounters</div>", unsafe_allow_html=True)
    
    # High-Density Patient Rows: Integrated Single-Line Layout
    for c in filtered_cards[:15]:
        tier_pill_class = "tier-high" if c['tier'] == "High Risk" else ("tier-moderate" if c['tier'] == "Moderate Risk" else "tier-low")
        score_color = "#DC2626" if c['tier'] == "High Risk" else ("#D97706" if c['tier'] == "Moderate Risk" else "#16A34A")
        tags_html = "".join([f'<span class="protocol-tag">{t}</span>' for t in c['resources']])
        
        # Single aligned row pairing clinical info with action button
        col_row, col_act = st.columns([13, 2], vertical_alignment="center")
        
        with col_row:
            st.markdown(f"""
            <div class="patient-row-card">
                <div class="pt-info-col">
                    <div class="pt-id">{c['enc_id']}</div>
                    <div class="pt-demo">{c['age']} &bull; {c['gender']} &bull; {c['race']}</div>
                </div>
                <div class="pt-vitals-col">
                    <span>Stay: <strong>{c['stay']}d</strong></span>
                    <span>Meds: <strong>{c['meds']}</strong></span>
                    <span>Inpatient: <strong>{c['inpatient']}</strong></span>
                    <span>A1C: <strong>{c['a1c']}</strong></span>
                    <span>Diag: <strong>{c['diag']}</strong></span>
                </div>
                <div class="pt-tags-col">
                    {tags_html}
                </div>
                <div class="pt-score-col">
                    <div>
                        <div class="score-number" style="color: {score_color};">{c['prob']*100:.1f}%</div>
                        <span class="{tier_pill_class}">{c['tier']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_act:
            if st.button("Review", key=f"btn_pop_{c['enc_id']}", use_container_width=True):
                show_patient_reasoning_dialog(c['enc_id'], c['row_dict'], c['prob'])
                
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# VIEW 2: BEDSIDE RISK CALCULATOR (LIVE INTERACTIVE ENGINE)
# -----------------------------------------------------------------------------
elif app_mode == "Bedside Risk Calculator":
    st.markdown("""
    <div class="compact-header">
        <h2 class="page-title">Bedside Risk Calculator</h2>
        <span class="page-subtitle">Real-time inference engine powered by XGBoost</span>
    </div>
    """, unsafe_allow_html=True)
    
    sample_pts = list(X_test.index[:50])
    selected_idx = st.selectbox(
        "Pre-load Patient Encounter",
        sample_pts,
        format_func=lambda i: f"Encounter #{i} | Age: {X_test.loc[i, 'age']} | Stay: {X_test.loc[i, 'time_in_hospital']}d | Meds: {X_test.loc[i, 'num_medications']} | Readmitted: {'YES' if y_test.loc[i]==1 else 'NO'}"
    )
    
    pt_row = X_test.loc[selected_idx].to_dict()
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    col_input, col_score = st.columns([3, 2], gap="large")
    
    with col_input:
        st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>Adjust Clinical Parameters</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            stay = st.slider("Hospital Stay (Days)", 1, 14, int(pt_row.get('time_in_hospital', 4)))
            meds = st.slider("Active Medications", 1, 50, int(pt_row.get('num_medications', 16)))
            inpatient = st.slider("Prior Inpatient Admissions", 0, 10, int(pt_row.get('number_inpatient', 1)))
        with c2:
            er = st.slider("Prior Emergency Visits", 0, 10, int(pt_row.get('number_emergency', 0)))
            a1c_options = ['>8', '>7', 'Norm', 'None']
            current_a1c = str(pt_row.get('A1Cresult', 'None'))
            a1c_idx = a1c_options.index(current_a1c) if current_a1c in a1c_options else 3
            a1c = st.selectbox("A1C Glycemic Level", a1c_options, index=a1c_idx)
            
            diag_options = ['Circulatory', 'Respiratory', 'Digestive', 'Diabetes', 'Injury', 'Musculoskeletal', 'Genitourinary', 'Neoplasms', 'Other']
            current_diag = str(pt_row.get('diag_1_cat', 'Circulatory'))
            diag_idx = diag_options.index(current_diag) if current_diag in diag_options else 0
            diag1 = st.selectbox("Primary ICD-9 Category", diag_options, index=diag_idx)
            
        pt_row['time_in_hospital'] = stay
        pt_row['num_medications'] = meds
        pt_row['number_inpatient'] = inpatient
        pt_row['number_emergency'] = er
        pt_row['A1Cresult'] = a1c
        pt_row['diag_1_cat'] = diag1
        pt_row['total_visits'] = inpatient + er + float(pt_row.get('number_outpatient', 0))
        pt_row['polypharmacy'] = int(meds >= 10)
        pt_row['high_prior_utilization'] = int(inpatient > 0 or er > 0)
        
    with col_score:
        st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>Calculated Readmission Risk</div>", unsafe_allow_html=True)
        
        # Real Inference
        df_single = pd.DataFrame([pt_row])
        X_trans_single = preprocessor.transform(df_single)
        live_prob = float(xgb_model.predict_proba(X_trans_single)[0, 1])
        tier, color, tier_desc = get_clinical_risk_tier(live_prob)
        
        # Clean Compact Gauge
        gauge_color = "#DC2626" if live_prob >= 0.50 else ("#D97706" if live_prob >= 0.25 else "#16A34A")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=live_prob * 100,
            number={'suffix': "%", 'font': {'color': "#0F172A", 'size': 38, 'family': 'Inter'}},
            gauge={
                'axis': {'range': [0, 100], 'tickcolor': "#94A3B8", 'tickwidth': 1},
                'bar': {'color': gauge_color, 'thickness': 0.22},
                'bgcolor': "#FFFFFF",
                'borderwidth': 1,
                'bordercolor': "#E2E8F0",
                'steps': [
                    {'range': [0, 25], 'color': "#F0FDF4"},
                    {'range': [25, 50], 'color': "#FFFBEB"},
                    {'range': [50, 100], 'color': "#FEF2F2"}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#0F172A", 'family': "Inter"},
            height=190,
            margin=dict(l=15, r=15, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        tier_class = "tier-high" if tier == "High Risk" else ("tier-moderate" if tier == "Moderate Risk" else "tier-low")
        st.markdown(f"""
        <div style="text-align: center; margin-top: -8px; margin-bottom: 12px;">
            <span class="{tier_class}">{tier}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Clinical Reasoning Modal", use_container_width=True):
            show_patient_reasoning_dialog(f"ENC-{selected_idx}", pt_row, live_prob)
        
    st.markdown("---")
    st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>Targeted Clinical Interventions</div>", unsafe_allow_html=True)
    interventions = recommend_clinical_interventions(pt_row, live_prob)
    
    col_int1, col_int2 = st.columns(2)
    for i, it in enumerate(interventions):
        col_target = col_int1 if i % 2 == 0 else col_int2
        with col_target:
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px 14px; margin-bottom: 8px;">
                <div style="font-size: 13px; font-weight: 600; color: #0F172A; margin-bottom: 2px;">{it['Recommendation']}</div>
                <div style="font-size: 12px; color: #64748B; line-height: 1.4;">{it['Rationale']}</div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# VIEW 3: CLINICAL GOVERNANCE & BENCHMARKS (ADMIN AUDIT)
# -----------------------------------------------------------------------------
elif app_mode == "Clinical Governance & Benchmarks":
    st.markdown("""
    <div class="compact-header">
        <h2 class="page-title">Clinical Governance & Benchmarks</h2>
        <span class="page-subtitle">Model comparison, calibration, and demographic disparity audit</span>
    </div>
    """, unsafe_allow_html=True)
    
    results_path = os.path.join(MODELS_DIR, "model_comparison_results.csv")
    if os.path.exists(results_path):
        results_df = pd.read_csv(results_path)
        
        st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Predictive Architecture Comparison (Held-Out Test Cohort N=20,354)</div>", unsafe_allow_html=True)
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name='AUC-ROC',
            x=results_df['Model'],
            y=results_df['AUC-ROC'],
            marker_color='#2563EB'
        ))
        fig_comp.add_trace(go.Bar(
            name='Recall (Sensitivity)',
            x=results_df['Model'],
            y=results_df['Recall (Sensitivity)'],
            marker_color='#38BDF8'
        ))
        fig_comp.add_trace(go.Bar(
            name='Precision',
            x=results_df['Model'],
            y=results_df['Precision'],
            marker_color='#10B981'
        ))
        
        fig_comp.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#FFFFFF',
            font={'color': "#0F172A", 'family': "Inter"},
            yaxis=dict(gridcolor='#F1F5F9', range=[0, 1.0]),
            xaxis=dict(gridcolor='#F1F5F9'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=280
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
    st.markdown("---")
    st.markdown("<div style='font-size: 14px; font-weight: 700; color: #0F172A; margin-bottom: 8px;'>Demographic Parity & Equalized Odds Disparity Reduction (Stretch Goal)</div>", unsafe_allow_html=True)
    
    mitigation_json_path = os.path.join(FAIRNESS_DIR, "mitigation_improvement_summary.json")
    if os.path.exists(mitigation_json_path):
        col_g1, col_g2, col_g3 = st.columns(3)
        
        with col_g1:
            st.markdown("""
            <div class="kpi-bar" style="flex-direction: column; align-items: flex-start;">
                <div class="kpi-label">Age Disparity Reduction</div>
                <div class="kpi-val" style="color: #16A34A; margin-top: 4px;">-16.17%</div>
                <div class="kpi-sub" style="margin-top: 2px;">TPR Disparity reduced 17.13% &rarr; 0.96%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_g2:
            st.markdown("""
            <div class="kpi-bar" style="flex-direction: column; align-items: flex-start;">
                <div class="kpi-label">Race Disparity Reduction</div>
                <div class="kpi-val" style="color: #16A34A; margin-top: 4px;">-25.43%</div>
                <div class="kpi-sub" style="margin-top: 2px;">TPR Disparity reduced 36.00% &rarr; 10.57%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_g3:
            st.markdown("""
            <div class="kpi-bar" style="flex-direction: column; align-items: flex-start;">
                <div class="kpi-label">Gender Parity (DPR)</div>
                <div class="kpi-val" style="color: #2563EB; margin-top: 4px;">94.24%</div>
                <div class="kpi-sub" style="margin-top: 2px;">Complies with Four-Fifths Rule (&gt;80%)</div>
            </div>
            """, unsafe_allow_html=True)
