import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_executive_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Executive Agency Color Palette
    C_BG = RGBColor(248, 250, 252)          # Light Slate (#F8FAFC)
    C_CARD_BG = RGBColor(255, 255, 255)     # Card White (#FFFFFF)
    C_CARD_ALT = RGBColor(241, 245, 249)    # Card Tint (#F1F5F9)
    C_BORDER = RGBColor(203, 213, 225)      # Slate Border (#CBD5E1)
    C_BORDER_LIGHT = RGBColor(226, 232, 240)# Light Border (#E2E8F0)
    C_NAVY = RGBColor(15, 23, 42)           # Deep Slate Navy (#0F172A)
    C_NAVY_LIGHT = RGBColor(30, 41, 59)     # Navy Secondary (#1E293B)
    C_BLUE = RGBColor(37, 99, 235)          # Clinical Blue Accent (#2563EB)
    C_BLUE_LIGHT = RGBColor(239, 246, 255)  # Light Blue Tint (#EFF6FF)
    C_BLUE_BORDER = RGBColor(191, 219, 254) # Blue Border (#BFDBFE)
    C_GREEN = RGBColor(16, 185, 129)        # Emerald (#10B981)
    C_GREEN_LIGHT = RGBColor(240, 253, 244) # Green Light (#F0FDF4)
    C_RED = RGBColor(220, 38, 38)           # Red Alert (#DC2626)
    C_TEXT_DARK = RGBColor(15, 23, 42)      # Primary Dark Text (#0F172A)
    C_TEXT_MUTED = RGBColor(71, 85, 105)    # Slate Muted Text (#475569)
    C_TEXT_LIGHT = RGBColor(100, 116, 139)  # Light Muted (#64748B)

    def draw_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.fill.background()
        return bg

    def draw_header_and_footer(slide, slide_num, title, subtitle):
        # Header Box
        hdr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(0.35), Inches(12.133), Inches(0.92))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = C_CARD_BG
        hdr.line.color.rgb = C_BORDER_LIGHT
        hdr.line.width = Pt(1)

        # Left Accent Blue Line
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(0.35), Inches(0.08), Inches(0.92))
        accent.fill.solid()
        accent.fill.fore_color.rgb = C_BLUE
        accent.line.fill.background()

        # Header Text Box
        tx = slide.shapes.add_textbox(Inches(0.85), Inches(0.38), Inches(11.7), Inches(0.85))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p_tracker = tf.paragraphs[0]
        p_tracker.text = f"HACKFEST 2026 SCREENING ROUND | HEALTHCARE & MEDTECH | SLIDE 0{slide_num} OF 06"
        p_tracker.font.size = Pt(8.5)
        p_tracker.font.bold = True
        p_tracker.font.color.rgb = C_BLUE

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.size = Pt(17)
        p_title.font.bold = True
        p_title.font.color.rgb = C_NAVY
        p_title.space_before = Pt(1)

        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = C_TEXT_MUTED
        p_sub.space_before = Pt(1)

        # Footer Line
        foot_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(7.15), Inches(12.133), Inches(0.015))
        foot_line.fill.solid()
        foot_line.fill.fore_color.rgb = C_BORDER_LIGHT
        foot_line.line.fill.background()

        # Footer Text
        ftx = slide.shapes.add_textbox(Inches(0.6), Inches(7.20), Inches(12.133), Inches(0.25))
        ftf = ftx.text_frame
        ftf.word_wrap = True
        ftf.margin_left = ftf.margin_right = ftf.margin_top = ftf.margin_bottom = 0
        fp = ftf.paragraphs[0]
        fp.text = "Project: ClinicalAI Decision Support | Domain: Healthcare & MedTech | Team 8"
        fp.font.size = Pt(8)
        fp.font.color.rgb = C_TEXT_LIGHT

        fp_r = fp.add_run()
        fp_r.text = f"                                                                                                                  Slide {slide_num} of 6"
        fp_r.font.bold = True

    def draw_container_card(slide, left, top, width, height, header_title=None, header_bg=C_NAVY):
        card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_BORDER
        card.line.width = Pt(1)

        if header_title:
            hdr_band = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(0.42)
            )
            hdr_band.fill.solid()
            hdr_band.fill.fore_color.rgb = header_bg
            hdr_band.line.fill.background()

            tx = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.08), Inches(width - 0.3), Inches(0.3))
            tf = tx.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = header_title.upper()
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.LEFT
        return card

    # =========================================================================
    # SLIDE 1: Project Overview & Problem Statement
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    draw_background(s1)
    draw_header_and_footer(
        s1, 1,
        "Project Overview & Problem Statement",
        "ClinicalAI: 30-Day Hospital Readmission Risk Prediction & Intelligent Care Transition Decision Support"
    )

    # Left Column: Project Meta & Target Users
    draw_container_card(s1, 0.6, 1.4, 4.4, 5.6, "Project Meta & Target Stakeholders", C_NAVY)
    tx1_l = s1.shapes.add_textbox(Inches(0.8), Inches(1.95), Inches(4.0), Inches(4.9))
    tf1_l = tx1_l.text_frame
    tf1_l.word_wrap = True
    tf1_l.margin_left = tf1_l.margin_right = tf1_l.margin_top = tf1_l.margin_bottom = 0

    meta_items = [
        ("Selected Domain:", "Healthcare & MedTech / Clinical Decision Support (CDS)"),
        ("Project Title:", "ClinicalAI - Hospital Readmission CDS"),
        ("Team Details:", "Team 8 (Hospital AI Innovation Cohort)"),
        ("Data Foundation:", "UCI 130-US Hospitals Diabetes Dataset (101,766 Inpatient Encounters over 10 Years)"),
        ("Clinical Focus:", "Diabetic Inpatients with Multimorbidity & Polypharmacy"),
        ("Target End-Users:", "")
    ]
    for lbl, val in meta_items:
        p = tf1_l.add_paragraph() if tf1_l.paragraphs[0].text else tf1_l.paragraphs[0]
        p.text = f"{lbl} "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_NAVY
        if val:
            run = p.add_run()
            run.text = val
            run.font.bold = False
            run.font.color.rgb = C_TEXT_MUTED
        p.space_after = Pt(8)

    stakeholders = [
        ("Discharge Planners:", "Triage and coordinate post-acute transition plans."),
        ("Attending Physicians:", "Review clinical AI rationale and sign off on care orders."),
        ("Clinical Pharmacists:", "Reconcile high-risk polypharmacy medication regimens."),
        ("Post-Acute Telehealth:", "Prioritize 48-hour post-discharge patient outreach.")
    ]
    for role, desc in stakeholders:
        p = tf1_l.add_paragraph()
        p.text = f"• {role} "
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED
        p.space_after = Pt(5)

    # Right Column Top: The $26B Problem
    draw_container_card(s1, 5.2, 1.4, 7.533, 3.1, "The Problem: A $26B Avoidable Healthcare Crisis", C_NAVY)
    tx1_rt = s1.shapes.add_textbox(Inches(5.4), Inches(1.95), Inches(7.1), Inches(2.45))
    tf1_rt = tx1_rt.text_frame
    tf1_rt.word_wrap = True
    tf1_rt.margin_left = tf1_rt.margin_right = tf1_rt.margin_top = tf1_rt.margin_bottom = 0

    problems = [
        ("FINANCIAL CRISIS", "Unplanned 30-day hospital readmissions exceed $26 Billion annually in avoidable medical costs across US and global health systems."),
        ("PUNITIVE HRRP PENALTIES", "Under CMS Hospital Readmissions Reduction Program, hospitals face direct Medicare reimbursement forfeitures (up to 3% penalty) for excess readmissions."),
        ("COMPLEX COMORBIDITY RELAPSE", "Diabetic inpatients face extreme vulnerability: 79.0% have >=10 distinct medications administered during their stay, compounding metabolic and cardiovascular relapse risk."),
        ("SUBJECTIVE MANUAL TRIAGE", "Current discharge planning relies on subjective intuition or retrospective paper notes, missing over 45% of preventable readmission candidates.")
    ]
    for tag, desc in problems:
        p = tf1_rt.add_paragraph() if tf1_rt.paragraphs[0].text else tf1_rt.paragraphs[0]
        run_tag = p.add_run()
        run_tag.text = f"[{tag}] "
        run_tag.font.bold = True
        run_tag.font.size = Pt(10)
        run_tag.font.color.rgb = C_RED if "FINANCIAL" in tag or "PENALTIES" in tag else C_BLUE
        
        run_desc = p.add_run()
        run_desc.text = desc
        run_desc.font.size = Pt(10)
        run_desc.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(7)

    # Right Column Bottom: 3 Key Metrics Addressed
    draw_container_card(s1, 5.2, 4.65, 7.533, 2.35, "Key Challenge Metrics Addressed", C_NAVY_LIGHT)
    stats1 = [
        ("11.16%", "Actual Readmissions", "Ground truth 30-day readmissions across 101,766 diabetic patient encounters.", C_NAVY),
        ("79.00%", "High Medication Intensity", "Inpatients receiving >=10 distinct medications during stay (79% of sample).", C_RED),
        ("59.45%", "Targeted ML Sensitivity", "Prioritizing recall over accuracy to catch ~60% of all readmissions at point of care.", C_BLUE)
    ]
    for i, (val, title, desc, col) in enumerate(stats1):
        box = s1.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(5.4 + i * 2.38), Inches(5.15), Inches(2.2), Inches(1.7)
        )
        box.fill.solid()
        box.fill.fore_color.rgb = C_BLUE_LIGHT if i==2 else C_CARD_ALT
        box.line.color.rgb = C_BLUE_BORDER if i==2 else C_BORDER_LIGHT
        box.line.width = Pt(1)

        btx = s1.shapes.add_textbox(Inches(5.5 + i * 2.38), Inches(5.25), Inches(2.0), Inches(1.5))
        btf = btx.text_frame
        btf.word_wrap = True
        btf.margin_left = btf.margin_right = btf.margin_top = btf.margin_bottom = 0

        bp1 = btf.paragraphs[0]
        bp1.text = val
        bp1.font.size = Pt(24)
        bp1.font.bold = True
        bp1.font.color.rgb = col

        bp2 = btf.add_paragraph()
        bp2.text = title
        bp2.font.size = Pt(10)
        bp2.font.bold = True
        bp2.font.color.rgb = C_NAVY
        bp2.space_before = Pt(2)

        bp3 = btf.add_paragraph()
        bp3.text = desc
        bp3.font.size = Pt(8.5)
        bp3.font.color.rgb = C_TEXT_MUTED
        bp3.space_before = Pt(2)

    # =========================================================================
    # SLIDE 2: Proposed Solution & Objectives
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    draw_background(s2)
    draw_header_and_footer(
        s2, 2,
        "Proposed Solution & Core Objectives",
        "Explainable Clinical Decision Support System with Real-Time Risk Stratification & Targeted Care Bundles"
    )

    # Top Value Proposition Banner
    top_ban = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.4), Inches(12.133), Inches(1.15))
    top_ban.fill.solid()
    top_ban.fill.fore_color.rgb = C_NAVY
    top_ban.line.fill.background()

    tx_ban = s2.shapes.add_textbox(Inches(0.8), Inches(1.48), Inches(11.7), Inches(0.95))
    tf_ban = tx_ban.text_frame
    tf_ban.word_wrap = True
    tf_ban.margin_left = tf_ban.margin_right = tf_ban.margin_top = tf_ban.margin_bottom = 0
    bp1 = tf_ban.paragraphs[0]
    bp1.text = "THE PROPOSAL: BEDSIDE PREDICTIVE CDS WITH ON-DEMAND CLINICAL AI REASONING"
    bp1.font.size = Pt(11)
    bp1.font.bold = True
    bp1.font.color.rgb = RGBColor(56, 189, 248)

    bp2 = tf_ban.add_paragraph()
    bp2.text = "An end-to-end clinical intelligence suite pairing calibrated gradient boosting (XGBoost) with ultra-fast LLM reasoning (Groq: openai/gpt-oss-120b). It continuously evaluates inpatient EHR records, stratifies 30-day readmission risk, synthesizes 5-point actionable clinical rationale, and prescribes targeted care transition orders before discharge."
    bp2.font.size = Pt(10)
    bp2.font.color.rgb = RGBColor(241, 245, 249)
    bp2.space_before = Pt(3)

    # 3 Strategic Pillars
    s2_pillars = [
        ("1. KEY OBJECTIVES", C_BLUE, [
            ("Recall-First Clinical Tuning", "Prioritize sensitivity (>=59%) over raw accuracy to catch high-risk relapsing patients before discharge rather than optimizing for aggregate accuracy."),
            ("Explainable AI Decisions", "Eliminate physician black-box skepticism via local directional feature attribution and narrative clinical justification."),
            ("Demographic Parity Governance", "Ensure ethical equity and equalized opportunity across Age, Race, and Gender protected cohorts via active disparity audits.")
        ], "Metric: 59.45% Recall Target"),
        ("2. CORE CAPABILITIES", C_NAVY, [
            ("Discharge Readiness Worklist", "High-density queue displaying real-time patient risk tiers, biomarker flags, and automated protocol recommendations."),
            ("Bedside Simulation Engine", "Interactive parameter sliders allowing clinicians to adjust stay duration, meds, and A1C to model post-discharge trajectories in real-time."),
            ("On-Demand Groq AI Modal", "Sub-second synthesis of exactly 5 structured clinical points validating discharge or discharge-delay decisions.")
        ], "Feature: Sub-Second Groq Modal"),
        ("3. MEASURABLE BENEFITS", C_GREEN, [
            ("HRRP Penalty Avoidance", "Directly lowers avoidable 30-day readmissions, protecting hospital operating margins and Medicare reimbursement compliance."),
            ("Targeted Resource Allocation", "Dispatches high-cost protocols (PharmD Bedside Recon, Home Health) only to patients with verified clinical need."),
            ("Physician Trust & Workflow Fit", "High-density clinical slate UI built to authentic EHR hospital standards without distracting clutter.")
        ], "ROI: Millions Saved in Penalties")
    ]

    for i, (col_head, hdr_c, items, summary_badge) in enumerate(s2_pillars):
        draw_container_card(s2, 0.6 + i * 4.1, 2.7, 3.933, 4.3, col_head, hdr_c)
        tx = s2.shapes.add_textbox(Inches(0.75 + i * 4.1), Inches(3.25), Inches(3.633), Inches(3.2))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        for h, b in items:
            p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
            p.text = f"• {h}\n"
            p.font.size = Pt(10.5)
            p.font.bold = True
            p.font.color.rgb = C_NAVY
            run = p.add_run()
            run.text = b
            run.font.bold = False
            run.font.size = Pt(9.5)
            run.font.color.rgb = C_TEXT_MUTED
            p.space_after = Pt(10)

        # Summary Badge inside card at bottom
        s_badge = s2.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.75 + i * 4.1), Inches(6.45), Inches(3.633), Inches(0.4)
        )
        s_badge.fill.solid()
        s_badge.fill.fore_color.rgb = C_BLUE_LIGHT if i==0 else (C_CARD_ALT if i==1 else C_GREEN_LIGHT)
        s_badge.line.color.rgb = C_BLUE_BORDER if i==0 else (C_BORDER_LIGHT if i==1 else RGBColor(187, 247, 208))
        stf = s_badge.text_frame
        stf.word_wrap = True
        stf.margin_left = stf.margin_right = stf.margin_top = stf.margin_bottom = 0
        stp = stf.paragraphs[0]
        stp.text = summary_badge.upper()
        stp.font.size = Pt(9)
        stp.font.bold = True
        stp.font.color.rgb = C_BLUE if i==0 else (C_NAVY if i==1 else C_GREEN)
        stp.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 3: Innovation & Existing Alternatives
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    draw_background(s3)
    draw_header_and_footer(
        s3, 3,
        "Innovation & Existing Alternatives",
        "Structured Comparison Matrix and the Four Core Technological Differentiators of ClinicalAI"
    )

    # Comparison Table
    draw_container_card(s3, 0.6, 1.4, 12.133, 3.8, "Competitive Architecture Comparison Matrix", C_NAVY)

    table_shape = s3.shapes.add_table(6, 4, Inches(0.75), Inches(1.9), Inches(11.833), Inches(3.15))
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(3.0)
    table.columns[2].width = Inches(3.0)
    table.columns[3].width = Inches(3.633)

    headers = ["Evaluation Dimension", "Static Scores (LACE / HOSPITAL)", "Standard Commercial EHR ML", "ClinicalAI (Our Solution)"]
    for col_idx, text in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_BLUE if col_idx == 3 else C_NAVY_LIGHT
        p = cell.text_frame.paragraphs[0]
        p.text = text
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER if col_idx > 0 else PP_ALIGN.LEFT

    table_data = [
        ("Clinical Feature Depth", "4-6 static tally variables", "Tabular ML without clinical context", "45+ clinical biomarkers, meds, and diagnoses"),
        ("Recall / Sensitivity Focus", "Uncalibrated / Arbitrary cutoffs", "Low recall (optimizes for overall AUC)", "High sensitivity (59.45%, scale_pos_weight=7.96)"),
        ("Explainability & Reasoning", "None (opaque single integer)", "Global feature charts only (no narrative)", "Hybrid: Local Feature Impact + 5-Point Groq AI"),
        ("Actionable Care Directives", "Score only (no care pathway)", "Score only (no protocol linkage)", "Prescribes targeted bundles (PharmD, Telehealth)"),
        ("Algorithmic Fairness", "Completely ignored", "Unmonitored demographic bias", "Built-in Fairlearn parity audits; Age disparity < 1%")
    ]

    for row_idx, row in enumerate(table_data, start=1):
        for col_idx, val in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.fill.solid()
            if col_idx == 3:
                cell.fill.fore_color.rgb = C_BLUE_LIGHT
            elif row_idx % 2 == 0:
                cell.fill.fore_color.rgb = C_CARD_ALT
            else:
                cell.fill.fore_color.rgb = C_CARD_BG
            
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_BLUE if col_idx == 3 else C_TEXT_DARK
            p.font.bold = True if col_idx == 3 or col_idx == 0 else False

    # 4 Innovation Summary Cards at Bottom
    inno_cards = [
        ("DUAL-LAYER INFERENCE", "Couples calibrated XGBoost tabular scoring with sub-second on-demand Groq LLM (gpt-oss-120b) clinical reasoning."),
        ("RECALL-FIRST FOCUS", "Configured with scale_pos_weight=7.96 catching ~60% of all readmissions at point of care, preventing fatal misses."),
        ("AUDITED PARITY", "Age TPR disparity reduced from 17.13% to 0.96%; 94.24% Gender Demographic Parity (EEOC 4/5ths compliant)."),
        ("ACTIONABLE DIRECTIVES", "Directly prescribes Pharmacist Bedside Recon, CDCES Referral, Home Health Nurse, and 48h Telehealth Outreach.")
    ]
    for i, (head, desc) in enumerate(inno_cards):
        box = s3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6 + i * 3.08), Inches(5.35), Inches(2.9), Inches(1.65))
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD_BG
        box.line.color.rgb = C_BLUE_BORDER
        box.line.width = Pt(1)

        tx = s3.shapes.add_textbox(Inches(0.72 + i * 3.08), Inches(5.45), Inches(2.66), Inches(1.45))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p1 = tf.paragraphs[0]
        p1.text = head
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = C_BLUE

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(9)
        p2.font.color.rgb = C_TEXT_DARK
        p2.space_before = Pt(4)

    # =========================================================================
    # SLIDE 4: System Architecture & Clinical Workflow
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    draw_background(s4)
    draw_header_and_footer(
        s4, 4,
        "System Architecture & Clinical Workflow",
        "Labelled Pipeline from Inpatient EHR Ingestion to Point-of-Care Bedside Decision Support"
    )

    # 4 Architecture Stages
    arch_cols = [
        ("1. DATA & PIPELINE", C_NAVY, [
            ("UCI EHR Dataset", "101,766 inpatient encounters across 10 years of hospital care."),
            ("Missing Imputation", "Clinically sound imputation for weight, payer code, and medical specialty."),
            ("Outlier Winsorization", "99th percentile capping on acute visits to prevent extreme skew."),
            ("Feature Engineering", "Polypharmacy flags, admission velocity, and glycemic control tiering.")
        ]),
        ("2. MODEL & FAIRNESS", C_BLUE, [
            ("Scikit-Learn Pipeline", "Leakage-free OneHotEncoder + RobustScaler preprocessing transformation."),
            ("XGBoost Classifier", "Configured with scale_pos_weight=7.96 for severe class imbalance handling."),
            ("Model Benchmark", "Evaluated against Logistic Regression & Random Forest (AUC: 0.6896, Sens: 59.45%)."),
            ("Fairlearn Governance", "Active parity auditing reducing Age TPR disparity from 17.13% to 0.96%.")
        ]),
        ("3. EXPLAINABILITY", C_NAVY_LIGHT, [
            ("Directional Attributions", "Local horizontal feature attribution bar chart displaying top risk drivers."),
            ("Groq Cloud API", "Ultra-fast inference via openai/gpt-oss-120b responding in sub-second time."),
            ("5 Clinical Points", "Synthesizes stabilization, polypharmacy, A1C, utilization, and post-acute needs."),
            ("Encounter Caching", "@st.cache_data prevents redundant LLM calls and guarantees zero doctor lag.")
        ]),
        ("4. CLINICAL SLATE UI", C_NAVY, [
            ("Discharge Worklist", "High-density queue with risk tier filters, ID search, and biomarker flags."),
            ("Bedside Calculator", "Live slider simulation adjusting stay duration, active meds, and A1C in real-time."),
            ("Modal Dialog", "Single-click review popup with order authorization and care team dispatch."),
            ("Zero Bloat Design", "Space-optimized, clinical slate layout built to authentic hospital standards.")
        ])
    ]

    for i, (head, hdr_c, items) in enumerate(arch_cols):
        draw_container_card(s4, 0.6 + i * 3.08, 1.4, 2.9, 3.7, head, hdr_c)
        tx = s4.shapes.add_textbox(Inches(0.72 + i * 3.08), Inches(1.9), Inches(2.65), Inches(3.1))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        for title, desc in items:
            p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
            p.text = f"• {title}: "
            p.font.size = Pt(9.5)
            p.font.bold = True
            p.font.color.rgb = C_NAVY
            run = p.add_run()
            run.text = desc
            run.font.bold = False
            run.font.size = Pt(9)
            run.font.color.rgb = C_TEXT_MUTED
            p.space_after = Pt(7)

    # Bottom Workflow Ribbon
    draw_container_card(s4, 0.6, 5.25, 12.133, 1.75, "End-to-End Clinical User Workflow", C_BLUE)

    steps = [
        ("Step 1: EHR Intake", "Patient admitted & vitals recorded in EHR"),
        ("Step 2: Predictive Scoring", "XGBoost calculates calibrated readmission risk"),
        ("Step 3: Worklist Flag", "High-Risk patient prioritized on care dashboard"),
        ("Step 4: AI Consultation", "Doctor clicks Review; Groq outputs 5 points"),
        ("Step 5: Protocol Dispatch", "Bedside PharmD & Telehealth orders executed")
    ]
    for i, (st_title, st_desc) in enumerate(steps):
        s_box = s4.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.75 + i * 2.38), Inches(5.75), Inches(2.2), Inches(1.15)
        )
        s_box.fill.solid()
        s_box.fill.fore_color.rgb = C_BLUE_LIGHT if i == 3 else C_CARD_BG
        s_box.line.color.rgb = C_BLUE_BORDER if i == 3 else C_BORDER_LIGHT
        s_box.line.width = Pt(1)

        stx = s4.shapes.add_textbox(Inches(0.82 + i * 2.38), Inches(5.82), Inches(2.05), Inches(1.0))
        stf = stx.text_frame
        stf.word_wrap = True
        stf.margin_left = stf.margin_right = stf.margin_top = stf.margin_bottom = 0

        p1 = stf.paragraphs[0]
        p1.text = st_title
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = C_BLUE if i == 3 else C_NAVY

        p2 = stf.add_paragraph()
        p2.text = st_desc
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = C_TEXT_MUTED
        p2.space_before = Pt(3)

    # =========================================================================
    # SLIDE 5: Technology Stack & Implementation Plan
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    draw_background(s5)
    draw_header_and_footer(
        s5, 5,
        "Technology Stack & Implementation Plan",
        "Architectural Rationale, Team Division of Responsibilities, and Prototype Build Roadmap"
    )

    # Left: Technology Stack & Technical Suitability
    draw_container_card(s5, 0.6, 1.4, 5.8, 5.6, "Proposed Technology Stack & Justification", C_NAVY)
    tx5_l = s5.shapes.add_textbox(Inches(0.8), Inches(1.95), Inches(5.4), Inches(4.9))
    tf5_l = tx5_l.text_frame
    tf5_l.word_wrap = True
    tf5_l.margin_left = tf5_l.margin_right = tf5_l.margin_top = tf5_l.margin_bottom = 0

    tech_cards = [
        ("Python 3.11+ / Scikit-Learn Pipeline",
         "Core data science runtime. Provides leakage-free preprocessor serialization, robust scaling, and stratified cross-validation for clinical reproducibility."),
        ("XGBoost 1.7+ Tabular Classifier",
         "Superior non-linear tabular handling, handles sparse medical codes, native scale_pos_weight class balancing, and sub-15ms inference latency."),
        ("Groq Cloud API (openai/gpt-oss-120b)",
         "Delivers sub-second LPU inference for bedside doctor consultation modals, generating strict 5-point clinical reasoning without doctor waiting."),
        ("Fairlearn Governance Framework",
         "Enforces ethical AI compliance by auditing Demographic Parity Ratios and Equalized Odds TPR/FPR disparities across protected demographics."),
        ("Streamlit Custom Clinical Slate UI",
         "High-density clinical decision dashboard, custom Inter typography, responsive patient cards, and native modal dialogs built for hospital EHRs.")
    ]
    for title, just in tech_cards:
        p = tf5_l.add_paragraph() if tf5_l.paragraphs[0].text else tf5_l.paragraphs[0]
        p.text = f"• {title}\n"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        run = p.add_run()
        run.text = f"   Suitability: {just}"
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(11)

    # Right Top: Team Responsibilities
    draw_container_card(s5, 6.65, 1.4, 6.083, 2.65, "Team Responsibilities (Hackfest Execution)", C_NAVY)
    tx5_rt = s5.shapes.add_textbox(Inches(6.85), Inches(1.95), Inches(5.7), Inches(2.0))
    tf5_rt = tx5_rt.text_frame
    tf5_rt.word_wrap = True
    tf5_rt.margin_left = tf5_rt.margin_right = tf5_rt.margin_top = tf5_rt.margin_bottom = 0

    roles_data = [
        ("ML & Pipeline Lead:", "Data quality auditing, 99th-percentile Winsorization, 3-model benchmark, and Fairlearn demographic disparity mitigation."),
        ("LLM & Explainability Lead:", "Groq API prompt engineering, local feature attribution, CP1252 unicode sanitization, and caching architecture."),
        ("Full-Stack Clinical UX Lead:", "Streamlit design system, responsive patient queue, interactive bedside calculator, and clinical workflow validation.")
    ]
    for role, resp in roles_data:
        p = tf5_rt.add_paragraph() if tf5_rt.paragraphs[0].text else tf5_rt.paragraphs[0]
        p.text = f"• {role} "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_NAVY
        run = p.add_run()
        run.text = resp
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_MUTED
        p.space_after = Pt(8)

    # Right Bottom: Hackathon Prototype Roadmap
    draw_container_card(s5, 6.65, 4.25, 6.083, 2.75, "Hackathon Prototype Build Roadmap (36-Hour Timeline)", C_NAVY_LIGHT)
    tx5_rb = s5.shapes.add_textbox(Inches(6.85), Inches(4.8), Inches(5.7), Inches(2.1))
    tf5_rb = tx5_rb.text_frame
    tf5_rb.word_wrap = True
    tf5_rb.margin_left = tf5_rb.margin_right = tf5_rb.margin_top = tf5_rb.margin_bottom = 0

    timeline_data = [
        ("Hours 00 - 08: Data Ingestion & Benchmark", "UCI cleaning, 99% Winsorization, LogReg vs RF vs XGBoost benchmark."),
        ("Hours 08 - 18: Modeling & Fairness Governance", "XGBoost class weighting (scale_pos_weight), threshold tuning, Fairlearn audits."),
        ("Hours 18 - 28: Groq AI & Clinical Dashboard", "Groq API prompt engineering, encounter caching, high-density Streamlit build."),
        ("Hours 28 - 36: Hardening & Verification", "Edge-case stress testing, packaging live demo, compliance documentation verification.")
    ]
    for h, desc in timeline_data:
        p = tf5_rb.add_paragraph() if tf5_rb.paragraphs[0].text else tf5_rb.paragraphs[0]
        p.text = f"• {h}: "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(7)

    # =========================================================================
    # SLIDE 6: Expected Outcomes & Demo Plan
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    draw_background(s6)
    draw_header_and_footer(
        s6, 6,
        "Expected Outcomes & Live Demo Plan",
        "Working Prototype Deliverables, Success Metrics, Live Demonstration Flow, and Future Roadmap"
    )

    # Left: Planned Deliverables & Success Measures
    draw_container_card(s6, 0.6, 1.4, 5.8, 5.6, "Planned Deliverables & Quantified Success Measures", C_NAVY)
    tx6_l = s6.shapes.add_textbox(Inches(0.8), Inches(1.95), Inches(5.4), Inches(4.9))
    tf6_l = tx6_l.text_frame
    tf6_l.word_wrap = True
    tf6_l.margin_left = tf6_l.margin_right = tf6_l.margin_top = tf6_l.margin_bottom = 0

    outcomes = [
        ("Working Hackathon Prototype", "Fully operational web application running locally on port 8501, evaluated on 20,354 real held-out patient encounters."),
        ("High Sensitivity (Recall = 59.45%)", "Captures ~60% of all 30-day readmissions at point of care (AUC-ROC: 0.6896, Brier Score: 0.177)."),
        ("Verified Algorithmic Fairness", "Age TPR disparity slashed from 17.13% to 0.96%; Race TPR disparity reduced by 25.43%; Gender Demographic Parity Ratio at 94.24% (EEOC 4/5ths compliant)."),
        ("Sub-Second Groq AI Reasoning", "Instantaneous 5-point clinical justification cards with persistent encounter caching."),
        ("Operational Resource Allocation", "Automatic trigger logic for Pharmacist Bedside Recon, CDCES Referral, Home Health Nurse, and 48-Hour Telehealth Outreach.")
    ]
    for head, body in outcomes:
        p = tf6_l.add_paragraph() if tf6_l.paragraphs[0].text else tf6_l.paragraphs[0]
        p.text = f"• {head}\n"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        run = p.add_run()
        run.text = f"   Result: {body}"
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(11)

    # Right Top: Live Demonstration Walkthrough
    draw_container_card(s6, 6.65, 1.4, 6.083, 2.65, "What the Live Demo Will Show (Pitch Script)", C_NAVY)
    tx6_rt = s6.shapes.add_textbox(Inches(6.85), Inches(1.95), Inches(5.7), Inches(2.0))
    tf6_rt = tx6_rt.text_frame
    tf6_rt.word_wrap = True
    tf6_rt.margin_left = tf6_rt.margin_right = tf6_rt.margin_top = tf6_rt.margin_bottom = 0

    demo_walkthrough = [
        ("Step 1: Patient Worklist Queue", "Filter 20,354 inpatient encounters by High/Moderate/Low risk tier and search encounter IDs."),
        ("Step 2: Bedside Risk Simulation", "Interactively adjust hospital stay (days), medications, and A1C levels; observe live gauge recalibration."),
        ("Step 3: On-Demand Groq AI Modal", "Click 'Review' on patient ENC-99195; showcase 5 parsed reasoning points & XGBoost feature attribution."),
        ("Step 4: Clinical Governance Panel", "Examine multi-model benchmark curves and audited demographic disparity reduction metrics.")
    ]
    for stp, desc in demo_walkthrough:
        p = tf6_rt.add_paragraph() if tf6_rt.paragraphs[0].text else tf6_rt.paragraphs[0]
        p.text = f"• {stp}: "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_NAVY
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_MUTED
        p.space_after = Pt(6)

    # Right Bottom: Dependencies & Future Roadmap
    draw_container_card(s6, 6.65, 4.25, 6.083, 2.75, "Dependencies, Risks & Future Roadmap", C_NAVY_LIGHT)
    tx6_rb = s6.shapes.add_textbox(Inches(6.85), Inches(4.8), Inches(5.7), Inches(2.1))
    tf6_rb = tx6_rb.text_frame
    tf6_rb.word_wrap = True
    tf6_rb.margin_left = tf6_rb.margin_right = tf6_rb.margin_top = tf6_rb.margin_bottom = 0

    dependencies_data = [
        ("Required Datasets & Services:", "UCI 130-US Hospitals (Public, de-identified EHR; zero PHI risk) + Groq API Key (backed by deterministic fallback)."),
        ("Key Risks & Mitigation:", "LLM rate limits or network drops mitigated via in-memory caching and clinical rule fallbacks; clinical drift monitored via governance dashboard."),
        ("Hackathon vs. Future Scope:", "Hackathon delivers working standalone CDS prototype. Future roadmap expands to SMART-on-FHIR Epic/Cerner integration and prospective clinical trials.")
    ]
    for rf, desc in dependencies_data:
        p = tf6_rb.add_paragraph() if tf6_rb.paragraphs[0].text else tf6_rb.paragraphs[0]
        p.text = f"• {rf} "
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = C_BLUE
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_TEXT_DARK
        p.space_after = Pt(6)

    out_file = os.path.join("D:\\hackfest", "Hackfest_2026_Screening_Presentation.pptx")
    prs.save(out_file)
    print(f"[+] Executive PPTX successfully updated at: {out_file}")
    return out_file

if __name__ == "__main__":
    build_executive_deck()
