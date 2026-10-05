import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette - Professional Medical / Clinical AI Theme
    COLOR_BG = RGBColor(248, 250, 252)        # Light Slate (#F8FAFC)
    COLOR_CARD_BG = RGBColor(255, 255, 255)   # Pure White (#FFFFFF)
    COLOR_BORDER = RGBColor(226, 232, 240)    # Slate Border (#E2E8F0)
    COLOR_PRIMARY = RGBColor(15, 23, 42)      # Deep Slate (#0F172A)
    COLOR_SECONDARY = RGBColor(100, 116, 139) # Muted Text (#64748B)
    COLOR_ACCENT = RGBColor(37, 99, 235)      # Clinical Blue (#2563EB)
    COLOR_ACCENT_BG = RGBColor(239, 246, 255) # Light Blue Tint (#EFF6FF)
    COLOR_GREEN = RGBColor(16, 185, 129)      # Emerald (#10B981)
    COLOR_RED = RGBColor(220, 38, 38)         # Alert Red (#DC2626)
    COLOR_HEADER_BG = RGBColor(15, 23, 42)    # Dark Header (#0F172A)

    def set_slide_bg(slide):
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = COLOR_BG
        bg_shape.line.fill.background()
        return bg_shape

    def add_slide_header(slide, slide_num, title, subtitle):
        # Header banner container
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.95)
        )
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = COLOR_CARD_BG
        top_bar.line.color.rgb = COLOR_BORDER
        top_bar.line.width = Pt(1)

        # Slide Number Badge
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.55), Inches(1.8), Inches(0.3)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = COLOR_ACCENT_BG
        badge.line.color.rgb = RGBColor(191, 219, 254)
        badge.line.width = Pt(1)
        tf_b = badge.text_frame
        tf_b.word_wrap = True
        tf_b.margin_left = tf_b.margin_right = tf_b.margin_top = tf_b.margin_bottom = 0
        p_b = tf_b.paragraphs[0]
        p_b.text = f"SLIDE 0{slide_num} / 06 | HACKFEST 2026"
        p_b.font.size = Pt(8.5)
        p_b.font.bold = True
        p_b.font.color.rgb = COLOR_ACCENT
        p_b.alignment = PP_ALIGN.CENTER

        # Title Text
        tx_box = slide.shapes.add_textbox(Inches(3.0), Inches(0.42), Inches(9.3), Inches(0.9))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(18)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        p_s = tf.add_paragraph()
        p_s.text = subtitle
        p_s.font.size = Pt(10)
        p_s.font.color.rgb = COLOR_SECONDARY
        p_s.space_before = Pt(2)

    def add_card(slide, left, top, width, height, title, bg_color=COLOR_CARD_BG, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)

        if title:
            # Header container inside card
            tx = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.15), Inches(width - 0.4), Inches(0.4))
            tf = tx.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title.upper()
            p.font.size = Pt(10.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_ACCENT
        return card

    # =========================================================================
    # SLIDE 1: Project Overview & Problem Statement
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide1)
    add_slide_header(
        slide1, 1,
        "Project Overview & Problem Statement",
        "Clinical AI: 30-Day Hospital Readmission Risk Prediction & Intelligent Care Transition Support"
    )

    # Left Column: Project Identity & Target Users
    add_card(slide1, 0.8, 1.5, 4.2, 5.5, "Project Meta & Target Users")
    tx1_left = slide1.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(3.8), Inches(4.7))
    tf1_l = tx1_left.text_frame
    tf1_l.word_wrap = True
    tf1_l.margin_left = tf1_l.margin_right = tf1_l.margin_top = tf1_l.margin_bottom = 0

    meta_items = [
        ("Domain:", "Healthcare & MedTech / Clinical Decision Support"),
        ("Project Title:", "ClinicalAI - Readmission CDS"),
        ("Team Details:", "Team 8 (Hospital AI Innovation Cohort)"),
        ("Target Users:", "Inpatient Discharge Planners, Case Managers, Attending Physicians, Clinical Pharmacists"),
        ("EHR Data Source:", "UCI 130-US Hospitals Diabetes Dataset (101,766 Encounters across 10 Years)"),
        ("Deployment Target:", "Point-of-care Clinical Worklist & Bedside Discharge Consultation Module")
    ]
    for lbl, val in meta_items:
        p = tf1_l.add_paragraph() if tf1_l.paragraphs[0].text else tf1_l.paragraphs[0]
        p.text = f"{lbl} "
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        run = p.add_run()
        run.text = val
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(10)

    # Right Column Top: The Core Clinical & Financial Problem
    add_card(slide1, 5.2, 1.5, 7.333, 2.65, "The Clinical & Financial Crisis")
    tx1_rt = slide1.shapes.add_textbox(Inches(5.4), Inches(2.1), Inches(6.9), Inches(1.9))
    tf1_rt = tx1_rt.text_frame
    tf1_rt.word_wrap = True
    tf1_rt.margin_left = tf1_rt.margin_right = tf1_rt.margin_top = tf1_rt.margin_bottom = 0

    prob_points = [
        "Massive Healthcare Burden: Unplanned 30-day hospital readmissions exceed $26 Billion annually in avoidable US/Global medical expenditures.",
        "Regulatory Penalties: Under HRRP (Hospital Readmission Reduction Program), healthcare centers face severe Medicare reimbursement forfeitures.",
        "Clinical Complexity in Diabetes: Complex comorbidities, polypharmacy (>=10 medications), and unstable glycemic indicators multiply post-discharge relapse vulnerability.",
        "Retrospective & Manual Triage: Existing clinical assessments occur retrospectively or rely on gut-feel, missing up to 45% of preventable readmission incidents."
    ]
    for pt in prob_points:
        p = tf1_rt.add_paragraph() if tf1_rt.paragraphs[0].text else tf1_rt.paragraphs[0]
        p.text = f"• {pt}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_PRIMARY
        p.space_after = Pt(6)

    # Right Column Bottom: Impact Metric Callouts
    add_card(slide1, 5.2, 4.35, 7.333, 2.65, "Key Challenge Metrics Addressed")
    
    # 3 Stat Cards inside bottom right
    stats = [
        ("11.16%", "Actual Readmission", "Ground truth 30-day readmissions in diabetic inpatient cohort"),
        ("43.8%", "Polypharmacy Alert", "Inpatients taking >=10 medications facing drug-interaction risks"),
        ("59.5%", "Targeted Sensitivity", "ML recall priority to detect vulnerable readmissions before exit")
    ]
    for i, (val, title, sub) in enumerate(stats):
        sc = slide1.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.4 + i * 2.3), Inches(4.9), Inches(2.15), Inches(1.85)
        )
        sc.fill.solid()
        sc.fill.fore_color.rgb = COLOR_ACCENT_BG if i==2 else COLOR_BG
        sc.line.color.rgb = RGBColor(191, 219, 254) if i==2 else COLOR_BORDER
        sc.line.width = Pt(1)
        
        stx = slide1.shapes.add_textbox(Inches(5.5 + i * 2.3), Inches(5.0), Inches(1.95), Inches(1.65))
        stf = stx.text_frame
        stf.word_wrap = True
        stf.margin_left = stf.margin_right = stf.margin_top = stf.margin_bottom = 0
        
        sp1 = stf.paragraphs[0]
        sp1.text = val
        sp1.font.size = Pt(22)
        sp1.font.bold = True
        sp1.font.color.rgb = COLOR_ACCENT if i==2 else COLOR_PRIMARY
        
        sp2 = stf.add_paragraph()
        sp2.text = title
        sp2.font.size = Pt(10)
        sp2.font.bold = True
        sp2.font.color.rgb = COLOR_PRIMARY
        sp2.space_before = Pt(2)
        
        sp3 = stf.add_paragraph()
        sp3.text = sub
        sp3.font.size = Pt(8.5)
        sp3.font.color.rgb = COLOR_SECONDARY
        sp3.space_before = Pt(2)

    # =========================================================================
    # SLIDE 2: Proposed Solution and Objectives
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide2)
    add_slide_header(
        slide2, 2,
        "Proposed Solution & Core Objectives",
        "Explainable Clinical Decision Support System with Real-Time Risk Stratification & Targeted Care Bundles"
    )

    # The Big Idea Banner
    idea_box = slide2.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(1.1)
    )
    idea_box.fill.solid()
    idea_box.fill.fore_color.rgb = COLOR_HEADER_BG
    idea_box.line.fill.background()
    itx = slide2.shapes.add_textbox(Inches(1.0), Inches(1.6), Inches(11.3), Inches(0.9))
    itf = itx.text_frame
    itf.word_wrap = True
    itf.margin_left = itf.margin_right = itf.margin_top = itf.margin_bottom = 0
    ip1 = itf.paragraphs[0]
    ip1.text = "THE CORE PROPOSAL: BED-SIDE PREDICTIVE CDS WITH ON-DEMAND AI REASONING"
    ip1.font.size = Pt(11)
    ip1.font.bold = True
    ip1.font.color.rgb = RGBColor(56, 189, 248) # Sky blue
    ip2 = itf.add_paragraph()
    ip2.text = "An end-to-end clinical intelligence platform combining calibrated machine learning (XGBoost) with fast on-demand LLM reasoning (Groq: gpt-oss-120b). It automatically stratifies inpatients into risk tiers, provides 5-point actionable clinical rationale, and prescribes protocol-driven discharge interventions before the patient leaves the facility."
    ip2.font.size = Pt(10)
    ip2.font.color.rgb = RGBColor(241, 245, 249)
    ip2.space_before = Pt(2)

    # 3 Strategic Pillars
    pillars = [
        ("1. KEY OBJECTIVES", [
            ("Recall-First Clinical Optimization:", "Prioritize sensitivity over raw accuracy to prevent discharging patients at imminent risk of 30-day decompensation."),
            ("Explainable Decision Support:", "Eliminate black-box skepticism by delivering local SHAP/Tree feature impact alongside physician-grade narrative reasoning."),
            ("Demographic Parity Assurance:", "Enforce ethical governance by actively auditing and mitigating disparate impact across Age, Race, and Gender groups.")
        ]),
        ("2. CORE CAPABILITIES", [
            ("Discharge Readiness Worklist:", "High-density queue displaying real-time patient risk tiers, biomarker flags, and automated protocol recommendations."),
            ("Bedside Simulation Engine:", "Live parameter calculator allowing clinicians to adjust stay duration, medications, and A1C to model post-discharge trajectories."),
            ("On-Demand Groq Reasoning Modal:", "Sub-second synthesis of exactly 5 structured clinical points validating discharge or discharge-delay decisions.")
        ]),
        ("3. MEASURABLE BENEFITS", [
            ("Drastic HRRP Penalty Avoidance:", "Prevents avoidable readmissions through timely outpatient care transition coordination."),
            ("Targeted Resource Allocation:", "Dispatches high-cost interventions (Home Health, PharmD Bedside Recon) only to the patients who strictly need them."),
            ("Physician Trust & Workflow Fit:", "Clean, space-efficient interface built to hospital EHR standards without distracting clutter.")
        ])
    ]

    for i, (col_title, items) in enumerate(pillars):
        add_card(slide2, 0.8 + i * 4.0, 2.75, 3.733, 4.25, col_title)
        cx = slide2.shapes.add_textbox(Inches(1.0 + i * 4.0), Inches(3.3), Inches(3.333), Inches(3.6))
        ctf = cx.text_frame
        ctf.word_wrap = True
        ctf.margin_left = ctf.margin_right = ctf.margin_top = ctf.margin_bottom = 0
        
        for head, body in items:
            p = ctf.add_paragraph() if ctf.paragraphs[0].text else ctf.paragraphs[0]
            p.text = f"• {head} "
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = COLOR_PRIMARY
            
            run = p.add_run()
            run.text = body
            run.font.bold = False
            run.font.color.rgb = COLOR_SECONDARY
            p.space_after = Pt(8)

    # =========================================================================
    # SLIDE 3: Innovation and Existing Alternatives
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide3)
    add_slide_header(
        slide3, 3,
        "Innovation & Existing Alternatives",
        "How ClinicalAI Surpasses Traditional Scoring Indices and Opaque Machine Learning Models"
    )

    # Left Column: Existing Solutions & Failures
    add_card(slide3, 0.8, 1.5, 4.4, 5.5, "Existing Industry Approaches & Pitfalls")
    tx3_l = slide3.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(4.0), Inches(4.7))
    tf3_l = tx3_l.text_frame
    tf3_l.word_wrap = True
    tf3_l.margin_left = tf3_l.margin_right = tf3_l.margin_top = tf3_l.margin_bottom = 0

    comp_points = [
        ("1. Static Risk Scores (LACE / HOSPITAL / Charlson):",
         "Rely on simple 4-6 point manual point tallies. Completely blind to polypharmacy, nuanced glycemic variability, or multidimensional comorbidity clusters. Static and non-personalized."),
        ("2. Standard Commercial Hospital EHR Models:",
         "Trained for aggregate ROC-AUC rather than clinical recall. They yield overwhelming false negatives in vulnerable cohorts, provide raw scores without clinical rationale, and treat protected demographics as blind variables."),
        ("3. Generic Generative AI Chatbots:",
         "Prone to medical hallucination, untethered to actual EHR tabular parameters, and uncalibrated for probabilistic medical risk scoring.")
    ]
    for h, b in comp_points:
        p = tf3_l.add_paragraph() if tf3_l.paragraphs[0].text else tf3_l.paragraphs[0]
        p.text = f"{h}\n"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_RED
        run = p.add_run()
        run.text = b
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(12)

    # Right Column: The 4 Key Innovations
    add_card(slide3, 5.4, 1.5, 7.133, 5.5, "Our 4 Core Technological Innovations")
    
    innovations = [
        ("Dual-Layer Inference Engine (XGBoost + Groq LLM)",
         "Couples deterministic, calibrated gradient boosting on 45+ EHR features with on-demand Groq reasoning (openai/gpt-oss-120b) to produce verified 5-point clinical justifications on demand."),
        ("Clinical Sensitivity (Recall) Prioritization",
         "Configured with class-imbalance weighting (scale_pos_weight=7.96) to achieve 59.45% sensitivity, ensuring high-risk relapsing patients are actively flagged rather than missed."),
        ("Built-In Ethical AI & Algorithmic Parity",
         "Integrates Fairlearn governance: verified 94.24% Demographic Parity on Gender (compliant with EEOC 4/5ths rule) and reduced Age TPR disparity from 17.13% to 0.96% via post-hoc mitigation."),
        ("Actionable Protocol Prescriptions (Not Just Scores)",
         "Translates mathematical probabilities into concrete care transition directives: Pharmacist Bedside Reconciliation, CDCES Diabetes Referral, Home Health Nurse, and 48-Hour Telehealth Outreach.")
    ]
    for i, (title, desc) in enumerate(innovations):
        in_box = slide3.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.6), Inches(2.1 + i * 1.18), Inches(6.733), Inches(1.05)
        )
        in_box.fill.solid()
        in_box.fill.fore_color.rgb = COLOR_ACCENT_BG
        in_box.line.color.rgb = RGBColor(191, 219, 254)
        in_box.line.width = Pt(1)
        
        itx = slide3.shapes.add_textbox(Inches(5.75), Inches(2.18 + i * 1.18), Inches(6.4), Inches(0.9))
        itf = itx.text_frame
        itf.word_wrap = True
        itf.margin_left = itf.margin_right = itf.margin_top = itf.margin_bottom = 0
        
        p1 = itf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_ACCENT
        
        p2 = itf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_PRIMARY
        p2.space_before = Pt(2)

    # =========================================================================
    # SLIDE 4: System Architecture and Workflow
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide4)
    add_slide_header(
        slide4, 4,
        "System Architecture & Clinical Workflow",
        "Labelled Pipeline from Inpatient EHR Ingestion to Point-of-Care Bedside Decision Support"
    )

    # 4 Architecture Blocks
    arch_steps = [
        ("1. DATA & PIPELINE", COLOR_HEADER_BG, RGBColor(255,255,255), [
            ("UCI EHR Dataset:", "101,766 inpatient encounters across 10 years."),
            ("Missing Imputation:", "Clinically sound imputation for weight/payer/meds."),
            ("Winsorization:", "99th percentile cap on utilization outliers."),
            ("Feature Engineering:", "Polypharmacy flag, visit velocity, glycemic tiering.")
        ]),
        ("2. MODEL & FAIRNESS", COLOR_ACCENT, RGBColor(255,255,255), [
            ("Preprocessing:", "OneHotEncoder + RobustScaler Pipeline."),
            ("Classifier:", "XGBoost with scale_pos_weight class balancing."),
            ("Performance:", "Recall: 59.45% | AUC: 0.6896 | Brier: 0.177."),
            ("Fairness Audit:", "Equalized Odds & Demographic Parity verified.")
        ]),
        ("3. EXPLAINABILITY", COLOR_CARD_BG, COLOR_PRIMARY, [
            ("SHAP / Feature Impact:", "Local horizontal feature attribution bar chart."),
            ("Groq API Reasoning:", "openai/gpt-oss-120b ultra-fast inference."),
            ("5 Clinical Points:", "Synthesizes stabilization, reconciliation, A1C."),
            ("Encounter Caching:", "@st.cache_data prevents redundant API latency.")
        ]),
        ("4. CLINICAL UI/UX", COLOR_CARD_BG, COLOR_PRIMARY, [
            ("Readiness Worklist:", "High-density queue with search & tier filters."),
            ("Bedside Simulator:", "Live slider adjustment for stay & medications."),
            ("Modal Dialog:", "Single-click review popup with order authorization."),
            ("Zero Emojis:", "Enterprise medical slate typography and styling.")
        ])
    ]

    for i, (col_head, bg_c, txt_c, bullet_items) in enumerate(arch_steps):
        # Header banner for block
        hb = slide4.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + i * 2.98), Inches(1.5), Inches(2.8), Inches(0.5)
        )
        hb.fill.solid()
        hb.fill.fore_color.rgb = bg_c
        hb.line.color.rgb = COLOR_BORDER
        hbtf = hb.text_frame
        hbtf.word_wrap = True
        hbtf.margin_left = hbtf.margin_right = hbtf.margin_top = hbtf.margin_bottom = 0
        hbp = hbtf.paragraphs[0]
        hbp.text = col_head
        hbp.font.size = Pt(10)
        hbp.font.bold = True
        hbp.font.color.rgb = txt_c
        hbp.alignment = PP_ALIGN.CENTER
        
        # Body Card
        cb = slide4.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + i * 2.98), Inches(2.05), Inches(2.8), Inches(3.6)
        )
        cb.fill.solid()
        cb.fill.fore_color.rgb = COLOR_CARD_BG
        cb.line.color.rgb = COLOR_BORDER
        cb.line.width = Pt(1)
        
        cbtx = slide4.shapes.add_textbox(Inches(0.95 + i * 2.98), Inches(2.15), Inches(2.5), Inches(3.4))
        cbtf = cbtx.text_frame
        cbtf.word_wrap = True
        cbtf.margin_left = cbtf.margin_right = cbtf.margin_top = cbtf.margin_bottom = 0
        
        for k, v in bullet_items:
            p = cbtf.add_paragraph() if cbtf.paragraphs[0].text else cbtf.paragraphs[0]
            p.text = f"• {k} "
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_PRIMARY
            run = p.add_run()
            run.text = v
            run.font.bold = False
            run.font.color.rgb = COLOR_SECONDARY
            p.space_after = Pt(7)

    # Workflow Strip at Bottom
    flow_bar = slide4.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.8), Inches(11.733), Inches(1.2)
    )
    flow_bar.fill.solid()
    flow_bar.fill.fore_color.rgb = COLOR_ACCENT_BG
    flow_bar.line.color.rgb = RGBColor(191, 219, 254)
    flow_bar.line.width = Pt(1)
    
    ftx = slide4.shapes.add_textbox(Inches(1.0), Inches(5.9), Inches(11.3), Inches(1.0))
    ftf = ftx.text_frame
    ftf.word_wrap = True
    ftf.margin_left = ftf.margin_right = ftf.margin_top = ftf.margin_bottom = 0
    fp1 = ftf.paragraphs[0]
    fp1.text = "END-TO-END CLINICAL USER WORKFLOW:"
    fp1.font.size = Pt(9.5)
    fp1.font.bold = True
    fp1.font.color.rgb = COLOR_ACCENT
    fp2 = ftf.add_paragraph()
    fp2.text = "Inpatient EHR Ingestion  -->  Pre-Discharge Risk Scoring (XGBoost)  -->  High-Risk Notification on Worklist  -->  Physician Clicks 'Review' (Groq Synthesizes 5 Clinical Points)  -->  Targeted Interventions Dispatched (PharmD / Telehealth)  -->  Readmission Prevented."
    fp2.font.size = Pt(10)
    fp2.font.bold = True
    fp2.font.color.rgb = COLOR_PRIMARY
    fp2.space_before = Pt(3)

    # =========================================================================
    # SLIDE 5: Technology Stack and Implementation Plan
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide5)
    add_slide_header(
        slide5, 5,
        "Technology Stack & Implementation Plan",
        "Architectural Rationale, Team Division of Responsibilities, and Prototype Build Roadmap"
    )

    # Left: Technology Stack Table & Justification
    add_card(slide5, 0.8, 1.5, 5.7, 5.5, "Technology Stack & Technical Suitability")
    tx5_l = slide5.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(5.3), Inches(4.7))
    tf5_l = tx5_l.text_frame
    tf5_l.word_wrap = True
    tf5_l.margin_left = tf5_l.margin_right = tf5_l.margin_top = tf5_l.margin_bottom = 0

    tech_specs = [
        ("Python 3.11+ / Scikit-Learn:", "Core data science runtime, Pipeline orchestration, Winsorization, and cross-validation."),
        ("XGBoost 1.7+ Classifier:", "Superior non-linear tabular handling, handles sparse medical codes, native scale_pos_weight class balancing, and low inference latency (<15ms)."),
        ("Groq Cloud API (openai/gpt-oss-120b):", "Delivers sub-second LLM inference for live bedside consultation modals, generating strict 5-point clinical reasoning without user lag."),
        ("Fairlearn Governance Framework:", "Demographic Parity Ratio and Equalized Odds TPR/FPR disparity auditing and post-hoc threshold adjustment."),
        ("Streamlit 1.30+ Custom Slate UI:", "High-density clinical decision dashboard, custom Inter typography, responsive patient cards, and native modal dialogs.")
    ]
    for tech, just in tech_specs:
        p = tf5_l.add_paragraph() if tf5_l.paragraphs[0].text else tf5_l.paragraphs[0]
        p.text = f"• {tech}\n"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        run = p.add_run()
        run.text = f"   Rationale: {just}"
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(7)

    # Right Top: Team Division of Responsibilities
    add_card(slide5, 6.7, 1.5, 5.833, 2.65, "Team Responsibilities (Hackfest Execution)")
    tx5_rt = slide5.shapes.add_textbox(Inches(6.9), Inches(2.1), Inches(5.4), Inches(1.9))
    tf5_rt = tx5_rt.text_frame
    tf5_rt.word_wrap = True
    tf5_rt.margin_left = tf5_rt.margin_right = tf5_rt.margin_top = tf5_rt.margin_bottom = 0

    roles = [
        ("ML & Pipeline Lead:", "Data cleaning, feature engineering, 3-model benchmark (LogReg, RF, XGBoost), and Fairlearn disparity mitigation."),
        ("LLM & Explainability Lead:", "Groq API integration, medical prompt engineering, SHAP local feature attribution, and unicode CP1252 sanitization."),
        ("Full-Stack Clinical UX Lead:", "Streamlit slate design system, responsive patient queue, interactive bedside calculator, and clinical workflow validation.")
    ]
    for role, resp in roles:
        p = tf5_rt.add_paragraph() if tf5_rt.paragraphs[0].text else tf5_rt.paragraphs[0]
        p.text = f"• {role} "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        run = p.add_run()
        run.text = resp
        run.font.bold = False
        run.font.color.rgb = COLOR_PRIMARY
        p.space_after = Pt(6)

    # Right Bottom: Prototype Timeline
    add_card(slide5, 6.7, 4.35, 5.833, 2.65, "Hackathon Prototype Build Timeline")
    tx5_rb = slide5.shapes.add_textbox(Inches(6.9), Inches(4.9), Inches(5.4), Inches(1.9))
    tf5_rb = tx5_rb.text_frame
    tf5_rb.word_wrap = True
    tf5_rb.margin_left = tf5_rb.margin_right = tf5_rb.margin_top = tf5_rb.margin_bottom = 0

    milestones = [
        ("Hours 00 - 08: Data & Benchmark", "UCI cleaning, 99% Winsorization, LogReg vs RF vs XGBoost benchmark."),
        ("Hours 08 - 18: Modeling & Fairness", "XGBoost tuning (scale_pos_weight), threshold optimization, Fairlearn audits."),
        ("Hours 18 - 28: Groq AI & Application", "Groq API prompt engineering, caching, Streamlit clinical slate layout build."),
        ("Hours 28 - 36: Polish & Verification", "Edge-case stress testing, packaging demo, compliance reports verification.")
    ]
    for h, desc in milestones:
        p = tf5_rb.add_paragraph() if tf5_rb.paragraphs[0].text else tf5_rb.paragraphs[0]
        p.text = f"• {h}: "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 6: Expected Outcomes and Demo Plan
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide6)
    add_slide_header(
        slide6, 6,
        "Expected Outcomes & Live Demo Plan",
        "Working Prototype Deliverables, Success Metrics, Live Demonstration Flow, and Future Roadmap"
    )

    # Left: Planned Deliverables & Success Metrics
    add_card(slide6, 0.8, 1.5, 5.7, 5.5, "Planned Deliverables & Success Measures")
    tx6_l = slide6.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(5.3), Inches(4.7))
    tf6_l = tx6_l.text_frame
    tf6_l.word_wrap = True
    tf6_l.margin_left = tf6_l.margin_right = tf6_l.margin_top = tf6_l.margin_bottom = 0

    deliverables = [
        ("Working Hackathon Prototype:", "Fully functional, locally hosted web application (Streamlit on port 8501) evaluated on 20,354 real patient encounters."),
        ("Predictive Sensitivity (Recall):", "59.45% sensitivity on 30-day readmissions (capturing ~60% of all readmissions at point of care; AUC 0.6896)."),
        ("Quantified Algorithmic Parity:", "Age TPR Disparity slashed from 17.13% to 0.96%; Race TPR disparity reduced by 25.43%; Gender Demographic Parity Ratio at 94.24%."),
        ("Fast Clinical AI Reasoning:", "Sub-second Groq API modal response delivering 5 verified points with cached persistence per encounter."),
        ("Operational Resource Allocation:", "Automatic trigger logic for Pharmacist Bedside Recon, CDCES Referral, Home Health Nurse, and 48-Hour Telehealth Outreach.")
    ]
    for head, body in deliverables:
        p = tf6_l.add_paragraph() if tf6_l.paragraphs[0].text else tf6_l.paragraphs[0]
        p.text = f"• {head}\n"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        run = p.add_run()
        run.text = f"   Result: {body}"
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(7)

    # Right Top: Live Demo Walkthrough
    add_card(slide6, 6.7, 1.5, 5.833, 2.65, "What the Live Demo Will Show")
    tx6_rt = slide6.shapes.add_textbox(Inches(6.9), Inches(2.1), Inches(5.4), Inches(1.9))
    tf6_rt = tx6_rt.text_frame
    tf6_rt.word_wrap = True
    tf6_rt.margin_left = tf6_rt.margin_right = tf6_rt.margin_top = tf6_rt.margin_bottom = 0

    demo_steps = [
        ("Step 1: Patient Worklist Queue", "Filter 20,354 inpatient encounters by High/Moderate/Low risk tier and search encounter IDs."),
        ("Step 2: Bedside Risk Simulation", "Interactively adjust hospital stay (days), medications, and A1C levels; observe live gauge recalibration."),
        ("Step 3: On-Demand Groq AI Modal", "Click 'Review' on high-risk patient ENC-99195; review the 5 parsed reasoning points and XGBoost feature attribution chart."),
        ("Step 4: Clinical Governance Panel", "Examine multi-model benchmark curves and audited demographic disparity reduction metrics.")
    ]
    for stp, desc in demo_steps:
        p = tf6_rt.add_paragraph() if tf6_rt.paragraphs[0].text else tf6_rt.paragraphs[0]
        p.text = f"• {stp}: "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_ACCENT
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = COLOR_PRIMARY
        p.space_after = Pt(4)

    # Right Bottom: Risks, Dependencies & Future Scope
    add_card(slide6, 6.7, 4.35, 5.833, 2.65, "Dependencies, Risks & Future Roadmap")
    tx6_rb = slide6.shapes.add_textbox(Inches(6.9), Inches(4.9), Inches(5.4), Inches(1.9))
    tf6_rb = tx6_rb.text_frame
    tf6_rb.word_wrap = True
    tf6_rb.margin_left = tf6_rb.margin_right = tf6_rb.margin_top = tf6_rb.margin_bottom = 0

    risks_future = [
        ("Required Datasets & Services:", "UCI 130-US Hospitals (Public, de-identified EHR; zero PHI risk) + Groq API Key (backed by deterministic fallback)."),
        ("Key Risks & Mitigation:", "LLM network latency/rate-limit mitigated via Streamlit caching and rule-based fallback; clinical drift monitored via governance metrics."),
        ("Hackathon vs. Future Scope:", "Hackathon delivers working standalone CDS prototype. Future roadmap expands to SMART-on-FHIR Epic/Cerner EHR integration and prospective clinical trials.")
    ]
    for rf, desc in risks_future:
        p = tf6_rb.add_paragraph() if tf6_rb.paragraphs[0].text else tf6_rb.paragraphs[0]
        p.text = f"• {rf} "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = COLOR_SECONDARY
        p.space_after = Pt(4)

    # Output Presentation File
    output_path = os.path.join("D:\\hackfest", "Hackfest_2026_Screening_Presentation.pptx")
    prs.save(output_path)
    print(f"[+] Successfully generated 6-slide presentation at: {output_path}")
    return output_path

if __name__ == "__main__":
    create_deck()
