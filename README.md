# CyberShield Sandbox: Social Engineering Simulation & Employee Awareness Platform

A GenAI-powered defense platform built for cybersecurity awareness training. It generates realistic, department-specific social engineering attack simulations (Vishing, Smishing, Pretexting), highlights active manipulation tactics, scores threats, maps activities to the MITRE ATT&CK matrix, provides quizzes, and exports PDF/DOCX compliance briefs.

---

## 🛡️ Important Safety & Defensive Compliance
- **Defensive Scope Only:** This application is strictly designed for cybersecurity training and defense awareness.
- **No Attack Tooling:** The platform does not generate executable payloads, exploitation scripts, or real phishing server templates.
- **Training Labels:** Every simulated dialogue, email, and SMS is prepended with the prominent safety tag: `[TRAINING SIMULATION ONLY]`.

---

## 🛠️ Project Architecture Diagram

```mermaid
graph TD
    User([User / Security Officer]) -->|1. Setup Profile & Sector| StreamlitApp[app.py]
    StreamlitApp -->|2. Generate Simulation Request| GeminiHelper[gemini_helper.py]
    GeminiHelper -->|3. Prompt LLM / Run Local Sandbox| GeminiAPI[Google Gemini API / Offline Sandbox]
    GeminiAPI -->|4. Parse JSON Response Structure| GeminiHelper
    GeminiHelper -->|5. Merge Mitigation Guides| MitreMapping[mitre_mapping.py]
    StreamlitApp -->|6. Render Multi-Tab UI Panels| StreamlitUI[Streamlit Panels]
    StreamlitUI -->|Plotly Render| RiskAnalytics[Interactive Risk Dashboard]
    StreamlitUI -->|Real-time Forms| InteractiveQuiz[Employee Training Quiz]
    StreamlitUI -->|File Stream| DocExporter[exporter.py]
    DocExporter -->|Binary Download| User
```

---

## 📂 Folder Structure

```
c:/Users/Victus/Documents/genaihackathon/
├── app.py                      # Streamlit Main Dashboard, Custom Styling, Interactive Forms & Tabs
├── gemini_helper.py            # LLM Prompts, API Configuration & Pre-seeded Offline Sandbox Scenarios
├── mitre_mapping.py            # Local MITRE ATT&CK Database mapping & defense logic
├── exporter.py                 # Report builders (docx, reportlab PDF) returning in-memory binary streams
├── requirements.txt            # Package configuration
└── README.md                   # Complete system manual, PPT Pitch Deck structure, and Demo Script
```

---

## 📝 Prompt Engineering Templates

The application uses Gemini 1.5 Flash to generate JSON responses. The template forces the model to act as a defensive cybersecurity analyst:

```
You are an expert cybersecurity awareness trainer and social engineering analyst.
Your job is to generate a realistic, high-quality, and highly educational training simulation.

=== CONSTRAINTS ===
- DO NOT generate real instructions on how to perform an attack.
- The output MUST serve purely educational purposes to train employees.
- EVERY output script or message MUST contain the label "[TRAINING SIMULATION ONLY]".
- Output MUST be structured JSON matching the schema.

=== PARAMETERS ===
- Sector: {sector}
- Target Department: {department}
- Employee Role: {employee_role}
- Social Engineering Attack Type: {attack_type}
- Context/Scenario: {scenario_description}
```

---

## ⛓️ MITRE ATT&CK & Threat Scoring Logic

### MITRE ATT&CK Mapping
Simulations are mapped to standard ATT&CK techniques:
- **T1566.003 (Spearphishing Voice):** Voice calls (Vishing) targeting dynamic actions or credentials.
- **T1566.002 (Spearphishing Link):** Sending SMS messages (Smishing) containing external login domains.
- **T1598 (Phishing for Information):** Posing as executives or vendors to acquire internal structural details.

### Threat Scoring Metrics
- **Risk Score (0-100):** Determined by evaluating:
  - *Sophistication of Pretext:* (0-40) - Use of valid partner details, names, or reference numbers.
  - *Emotional Cues:* (0-30) - Level of Urgency, Fear, or Authority pressure.
  - *Technical Action:* (0-30) - Requesting MFA tokens, direct wires, or downloading software.
- **Likelihood:** Low, Medium, High, or Critical.
- **Impact:** Financial Loss, Credential Leak, or Operational Interruption.

---

