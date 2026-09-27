import json
import os
import google.generativeai as genai
import requests

# Predefined high-quality sandbox dataset for one-click demo runs
SANDBOX_DATA = {
    "it_helpdesk": {
        "simulation_title": "IT Helpdesk Vishing: MFA Elicitation Attack",
        "attack_type": "Vishing",
        "simulation_text": (
            "[TRAINING SIMULATION ONLY]\n\n"
            "Caller (IT Support): \"Hey John, this is Marcus from the IT security desk. We're noticing some anomalous login attempts on your account from an IP address in Russia. We've temporarily blocked it, but I need to resync your security token to prevent a lockout. You should receive a 6-digit push verification code on your phone in just a second. I need you to read it out to me so I can verify and secure your connection. It's critical we do this right now or your account will be locked for 48 hours. Can you check your phone?\"\n\n"
            "Employee: \"Oh, okay. Let me check. Yes, I see a push notification with a code.\"\n\n"
            "Caller (IT Support): \"Excellent, please read it to me quickly so we can finish this and get you secured.\""
        ),
        "manipulation_techniques": [
            {
                "technique": "Impersonation",
                "snippet": "Marcus from the IT security desk",
                "danger_explanation": "Impersonating IT staff exploits the trust employees have in internal support teams, making them less likely to verify credentials.",
                "employee_response": "Politely decline to act, hang up, and call the IT helpdesk back via the verified internal number in the company directory."
            },
            {
                "technique": "Urgency",
                "snippet": "It's critical we do this right now or your account will be locked for 48 hours.",
                "danger_explanation": "Urgency creates panic, which disrupts rational decision-making and forces the employee to comply before validating the request.",
                "employee_response": "Recognize that security policies almost never require immediate, panic-inducing bypasses. Slow down and check procedures."
            },
            {
                "technique": "Fear",
                "snippet": "anomalous login attempts on your account from an IP address in Russia",
                "danger_explanation": "Triggering fear of a cyber breach causes the employee to cooperate, thinking they are helping to resolve a security emergency.",
                "employee_response": "Remember that IT handles backend security incidents without needing your live passwords or MFA codes over the phone."
            },
            {
                "technique": "Information Gathering",
                "snippet": "read it out to me so I can verify",
                "danger_explanation": "Eliciting an MFA code is a credential harvesting method. This code allows the attacker to log in directly by bypassing MFA.",
                "employee_response": "Never share multi-factor authentication (MFA) codes, SMS codes, or passwords with anyone, including people claiming to be IT support."
            }
        ],
        "emotional_profile": {
            "fear": 85,
            "urgency": 90,
            "authority": 95,
            "trust": 75,
            "curiosity": 30,
            "sympathy": 20,
            "scarcity": 15
        },
        "threat_intelligence": {
            "category": "Multi-Factor Authentication (MFA) Bypass / Social Engineering",
            "risk_score": 88,
            "likelihood": "High",
            "impact": "Critical"
        },
        "mitre_mapping": [
            {
                "technique_id": "T1566.003",
                "technique_name": "Phishing: Spearphishing Voice (Vishing)",
                "description": "Adversaries may use voice communications to direct victims to reveal credentials, provide information, or execute malicious commands."
            },
            {
                "technique_id": "T1598.003",
                "technique_name": "Phishing for Information: Spearphishing Voice",
                "description": "Adversaries may use phone calls specifically targeted at eliciting sensitive information about the organization, individuals, or systems."
            }
        ],
        "awareness_card": {
            "red_flags": [
                "Unsolicited call from IT support asking for dynamic security codes.",
                "Creating extreme pressure by threatening account lockouts.",
                "Mentioning scary threats (Russian hacker logins) to bypass protocols."
            ],
            "what_to_do": [
                "Verify the caller's identity by calling the official IT Helpdesk number.",
                "Report the vishing attempt to the Security Operations Center (SOC)."
            ],
            "what_not_to_do": [
                "Never read out or share one-time passcodes, MFA prompts, or passwords.",
                "Do not allow the caller to rush or panic you into violating protocols."
            ],
            "reporting_procedure": "Forward the date, time, and spoofed phone number of the call to security@organization.com and report it on the internal security portal."
        },
        "quiz": {
            "mcqs": [
                {
                    "question": "Why is sharing a 6-digit MFA verification code over the phone dangerous?",
                    "options": [
                        "It changes the language of your corporate portal.",
                        "It allows the caller to bypass your MFA check and log in as you.",
                        "It will automatically reset your mobile phone to factory settings.",
                        "It blocks IT from sending you future notifications."
                    ],
                    "correct_answer": "It allows the caller to bypass your MFA check and log in as you.",
                    "explanation": "MFA codes are secrets used to verify identity. If shared, the attacker can log in using your credentials from their own machine."
                },
                {
                    "question": "What is the best way to verify if a caller is actually an IT support team member?",
                    "options": [
                        "Believe them if they know your department and name.",
                        "Ask them to email you a screenshot.",
                        "Hang up and call the IT helpdesk number listed on the official company portal.",
                        "Give them a fake MFA code first to test them."
                    ],
                    "correct_answer": "Hang up and call the IT helpdesk number listed on the official company portal.",
                    "explanation": "Official directories provide trusted, out-of-band contact routes. Never use contact details provided by the caller."
                },
                {
                    "question": "What psychological trigger is used when the caller threatens account lockout within 48 hours?",
                    "options": [
                        "Scarcity",
                        "Urgency & Fear",
                        "Curiosity",
                        "Authority"
                    ],
                    "correct_answer": "Urgency & Fear",
                    "explanation": "Threatening a negative consequence under a tight timeframe forces the victim to act quickly, suspending rational checks."
                }
            ],
            "scenario_question": {
                "question": "You receive a phone call from 'Security Operations' saying your computer is sending malicious spam. They ask you to go to a website and download a tool called 'TeamViewer' so they can inspect it. What should you do?",
                "options": [
                    "Download and install the tool immediately to help protect the network.",
                    "Tell them your password instead so they can log in remotely.",
                    "Politely decline, hang up, report the call to your actual security team, and run standard corporate virus scans.",
                    "Ask them to hold for 30 minutes while you search for the file."
                ],
                "correct_answer": "Politely decline, hang up, report the call to your actual security team, and run standard corporate virus scans.",
                "explanation": "Unsolicited requests to install remote access software are a major pretexting indicator used by adversaries to gain access to corporate systems."
            }
        }
    },
    "hr_department": {
        "simulation_title": "HR Smishing: Urgent Direct Deposit Notification",
        "attack_type": "Smishing",
        "simulation_text": (
            "[TRAINING SIMULATION ONLY]\n\n"
            "SMS Alert: \"[HR-PORTAL] Urgent action required. We detected an anomaly in your direct deposit information for the upcoming pay cycle. To prevent a delay in your salary disbursement, you must update your banking details in the portal immediately. Click here to verify your identity: hxxps://company-hr-portal-sso.net/login. Failure to update by 5:00 PM today will delay your payment until the next month.\""
        ),
        "manipulation_techniques": [
            {
                "technique": "Impersonation",
                "snippet": "[HR-PORTAL]",
                "danger_explanation": "Using bracketed tags like '[HR-PORTAL]' mimics automated systems, making the text message look like an official automated system notification.",
                "employee_response": "Do not trust sender names or headers in SMS messages, as they can be easily spoofed."
            },
            {
                "technique": "Scarcity",
                "snippet": "delay in your salary disbursement",
                "danger_explanation": "Exploits the fear of financial loss or delayed salary, triggering direct emotional concern that causes the employee to override safety guidelines.",
                "employee_response": "Recognize that salary issues are handled via formal channels and will not be solved through random SMS links."
            },
            {
                "technique": "Urgency",
                "snippet": "Failure to update by 5:00 PM today will delay your payment",
                "danger_explanation": "Setting a strict, immediate deadline (5:00 PM today) forces the employee to act in haste without double-checking the URL.",
                "employee_response": "Ignore artificial deadlines. Contact HR directly using official internal messaging channels (Slack, Teams, or official email)."
            },
            {
                "technique": "Trust Building",
                "snippet": "company-hr-portal-sso.net",
                "danger_explanation": "Using domain typosquatting (adding words like 'sso' and '-net') makes the link look legitimate to users who don't inspect the full domain path.",
                "employee_response": "Inspect links closely. Official portals are hosted on the primary corporate domain (e.g., company.com), not external look-alike domains."
            }
        ],
        "emotional_profile": {
            "fear": 65,
            "urgency": 88,
            "authority": 82,
            "trust": 90,
            "curiosity": 40,
            "sympathy": 10,
            "scarcity": 92
        },
        "threat_intelligence": {
            "category": "Credential Harvesting / Financial Redirect Fraud",
            "risk_score": 94,
            "likelihood": "Critical",
            "impact": "High"
        },
        "mitre_mapping": [
            {
                "technique_id": "T1566.002",
                "technique_name": "Phishing: Spearphishing Link (Smishing)",
                "description": "Adversaries may use text messaging systems (smishing) containing malicious links to capture credentials or direct employees to fake portals."
            },
            {
                "technique_id": "T1204.001",
                "technique_name": "User Execution: Malicious Link",
                "description": "An adversary relies on a user clicking a link within a phishing or smishing message to execute credential harvesting."
            }
        ],
        "awareness_card": {
            "red_flags": [
                "Unsolicited SMS about internal payroll settings containing an external URL.",
                "Extreme deadline forcing quick action to secure your monthly pay.",
                "Use of a domain name that mimics official branding but is not the company domain."
            ],
            "what_to_do": [
                "Open your browser and navigate directly to your company's official HR portal bookmark.",
                "Send a message to the HR department via internal chat to verify the SMS."
            ],
            "what_not_to_do": [
                "Never click links in text messages regarding administrative actions.",
                "Never enter your corporate password on external domains not approved by IT."
            ],
            "reporting_procedure": "Take a screenshot of the SMS showing the sender and link, and upload it to the Security Incident tool, or email it to phishing-alert@organization.com."
        },
        "quiz": {
            "mcqs": [
                {
                    "question": "What is the primary indicator of phishing/smishing in the link 'company-hr-portal-sso.net'?",
                    "options": [
                        "It doesn't start with www.",
                        "It uses the '.net' top-level domain instead of the company's verified domain extension.",
                        "It has too many dashes in the name.",
                        "It contains the word 'login'."
                    ],
                    "correct_answer": "It uses the '.net' top-level domain instead of the company's verified domain extension.",
                    "explanation": "Attackers register similar domains (typosquatting) to build trust. Always verify that the domain matches your exact corporate domain."
                },
                {
                    "question": "What action should you take if you receive a text message warning that you won't get paid unless you click a link?",
                    "options": [
                        "Click the link immediately to ensure you get paid on time.",
                        "Ignore the text and look for a new job.",
                        "Verify via official company channels (like official HR email or portal) and report the text to the security team.",
                        "Reply with your credit card number just in case."
                    ],
                    "correct_answer": "Verify via official company channels (like official HR email or portal) and report the text to the security team.",
                    "explanation": "Never click unsolicited administrative links. Verify via trusted internal channels and report the phishing attempt immediately."
                },
                {
                    "question": "Which MITRE ATT&CK technique maps to the action of sending a text message with a malicious link?",
                    "options": [
                        "Spearphishing Voice (Vishing)",
                        "Spearphishing Link (Smishing)",
                        "System Firmware Discovery",
                        "Account Manipulation"
                    ],
                    "correct_answer": "Spearphishing Link (Smishing)",
                    "explanation": "T1566.002 represents spearphishing links sent via email, text, or messaging systems to harvest credentials."
                }
            ],
            "scenario_question": {
                "question": "You clicked the SMS link and logged in. Two minutes later, you realize it was a training simulation or actual attack. What is your immediate priority?",
                "options": [
                    "Delete the text message so nobody sees you fell for it.",
                    "Change your password immediately on the official portal, revoke active sessions if possible, and contact IT Security.",
                    "Wait until the end of the day to see if your password still works.",
                    "Call the number back and ask the sender to delete your login."
                ],
                "correct_answer": "Change your password immediately on the official portal, revoke active sessions if possible, and contact IT Security.",
                "explanation": "In credential leakage incidents, time is of the essence. Quick containment (changing password, notifying security) prevents attackers from establishing a foothold."
            }
        }
    },
    "finance_department": {
        "simulation_title": "Finance Pretexting: Fraudulent Invoice & Wire Redirect",
        "attack_type": "Pretexting",
        "simulation_text": (
            "[TRAINING SIMULATION ONLY]\n\n"
            "Email/Call: \"Hi Sarah, this is Robert Miller, CFO of Apex Logistics (your primary shipping partner). We have an outstanding invoice #AP-9981 of $42,500 that is currently overdue. Our internal audit department has flagged that your team hasn't paid. I understand things get busy, but we need this resolved immediately to avoid disruption. Also, please note we recently migrated our bank details; I'm sending over the updated routing instructions via a secure PDF attachment. Please update our billing records and process the invoice by end of day. Thanks for understanding.\""
        ),
        "manipulation_techniques": [
            {
                "technique": "Authority",
                "snippet": "Robert Miller, CFO of Apex Logistics",
                "danger_explanation": "Claiming a senior title (CFO) triggers compliance because employees hesitate to challenge high-ranking executives.",
                "employee_response": "Treat senior executives with standard verification protocols. CFOs must follow the same security verification channels as everyone else."
            },
            {
                "technique": "Trust Building",
                "snippet": "Apex Logistics (your primary shipping partner)",
                "danger_explanation": "Mentioning a real partner name build rapport, establishing credibility so the target lowers their guard.",
                "employee_response": "Perform secondary verification. Just because a caller knows your vendor names doesn't make them legitimate (this info is often public)."
            },
            {
                "technique": "Fear",
                "snippet": "avoid disruption",
                "danger_explanation": "Threatening business disruption (stopping shipping services) forces the employee to act quickly to avoid being blamed for a operational failure.",
                "employee_response": "Recognize that operations will support validation delays for high-value billing adjustments."
            },
            {
                "technique": "Information Gathering",
                "snippet": "invoice #AP-9981 of $42,500 that is currently overdue",
                "danger_explanation": "Introducing concrete invoice numbers and amounts is used to bait the accountant into cross-referencing and confirming internal payment schedules.",
                "employee_response": "Do not verify invoice details with unverified external parties. Always reference internal databases first."
            }
        ],
        "emotional_profile": {
            "fear": 75,
            "urgency": 95,
            "authority": 92,
            "trust": 88,
            "curiosity": 15,
            "sympathy": 30,
            "scarcity": 80
        },
        "threat_intelligence": {
            "category": "Business Email Compromise (BEC) / Invoice Redirection Fraud",
            "risk_score": 96,
            "likelihood": "High",
            "impact": "Critical"
        },
        "mitre_mapping": [
            {
                "technique_id": "T1566.002",
                "technique_name": "Phishing: Spearphishing Link / Attachment",
                "description": "Adversaries may use phishing emails with attachment payloads containing payment details or spoofed invoices."
            },
            {
                "technique_id": "T1598.003",
                "technique_name": "Phishing for Information: Spearphishing Voice",
                "description": "Adversaries may use phone calls specifically targeted at eliciting sensitive payment information."
            }
        ],
        "awareness_card": {
            "red_flags": [
                "Unsolicited request to change bank details for an existing vendor.",
                "Executive pressure to push payments outside standard business schedules.",
                "Receiving updated bank routing sheets via external PDF attachments."
            ],
            "what_to_do": [
                "Initiate secondary out-of-band confirmation: call a verified contact at the vendor using a pre-saved phone number.",
                "Submit the request to the finance supervisor for formal compliance approval."
            ],
            "what_not_to_do": [
                "Never modify wire transfer information, IBANs, or routing numbers based on email requests alone.",
                "Do not open payment attachments from unverified external accounts."
            ],
            "reporting_procedure": "Flag the suspicious email as Phishing/Fraud, notify the Accounts Payable lead, and report the caller ID/email to the IT Security Team."
        },
        "quiz": {
            "mcqs": [
                {
                    "question": "What is the primary control used to prevent Business Email Compromise (BEC) and wire transfer fraud?",
                    "options": [
                        "Emailing the sender to ask if they are sure.",
                        "Secondary verification via an independent, trusted out-of-band communication channel (e.g. calling a pre-saved number).",
                        "Paying only 10% of the invoice first to see if it works.",
                        "Comparing the font in the PDF to older invoices."
                    ],
                    "correct_answer": "Secondary verification via an independent, trusted out-of-band communication channel (e.g. calling a pre-saved number).",
                    "explanation": "Out-of-band verification is the single most effective control to confirm banking detail changes. Attackers who control email accounts cannot intercept independent telephone calls."
                },
                {
                    "question": "An email claiming to be from your vendor Apex Logistics is sent from 'accounting@apex-logistics-group.com', but your usual contact writes from '@apex-logistics.com'. What does this indicate?",
                    "options": [
                        "The vendor upgraded their email servers.",
                        "Domain typosquatting / Impersonation attempt.",
                        "Nothing, both domains are owned by the same company.",
                        "A temporary networking glitch on their side."
                    ],
                    "correct_answer": "Domain typosquatting / Impersonation attempt.",
                    "explanation": "Attackers register domains that look highly similar to the target vendor to fool recipients. Always verify the domain extension matches exactly."
                },
                {
                    "question": "Why is executive pressure (e.g. 'I am the CFO, pay this now') a common technique in financial scams?",
                    "options": [
                        "Because CFOs are usually in charge of sending invoices.",
                        "It exploits authority, prompting employees to bypass standard validation procedures out of deference or fear.",
                        "CFOs are the only ones allowed to change banking numbers.",
                        "It speeds up accounting software audits."
                    ],
                    "correct_answer": "It exploits authority, prompting employees to bypass standard validation procedures out of deference or fear.",
                    "explanation": "The 'Authority' trigger relies on the human tendency to obey hierarchy. Safe organizations require that all changes, even executive ones, undergo the same verification."
                }
            ],
            "scenario_question": {
                "question": "A vendor calls you claiming their email system is down and they need you to pay an urgent invoice by wire. They give you the routing number over the phone. What should you do?",
                "options": [
                    "Write down the details and run the payment immediately.",
                    "Refuse the request, tell them you must wait until email is back, verify via a trusted phone number, and follow standard AP approvals.",
                    "Ask them to text you the details instead.",
                    "Ask them to contact your bank directly to make the change."
                ],
                "correct_answer": "Refuse the request, tell them you must wait until email is back, verify via a trusted phone number, and follow standard AP approvals.",
                "explanation": "Any invoice adjustment request made solely over the phone is high-risk. A formal, verified workflow is necessary to update financial databases safely."
            }
        }
    }
}


def call_groq_api(api_key: str, prompt: str) -> dict:
    """
    Sends request to Groq API using requests to get a Llama 3.3 simulation JSON response.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    res_json = response.json()
    content = res_json["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_simulation(
    api_key: str, 
    sector: str, 
    department: str, 
    employee_role: str, 
    attack_type: str, 
    scenario_description: str,
    provider: str = "Gemini",
    groq_api_key: str = ""
) -> dict:
    """
    Generates a social engineering training simulation using the selected Multi-LLM provider,
    falling back dynamically if needed.
    """
    
    # 1. Fallback to sandbox if requested or no valid key provided
    if provider == "Gemini" and (not api_key or api_key == "SANDBOX_DEMO"):
        return get_sandbox_fallback(department)
    elif provider == "Llama 3.3 (Groq)" and (not groq_api_key or groq_api_key == "SANDBOX_DEMO"):
        return get_sandbox_fallback(department)

    prompt = f"""
You are an expert cybersecurity awareness trainer and social engineering analyst.
Your job is to generate a realistic, high-quality, and highly educational training simulation for defensive security training.

=== CONSTRAINTS ===
- DO NOT generate real instructions on how to perform an attack.
- The output MUST serve purely educational purposes to train employees.
- EVERY output script or message MUST contain the label "[TRAINING SIMULATION ONLY]".
- Output MUST be structured JSON matching the schema below.

=== PARAMETERS ===
- Sector: {sector}
- Target Department: {department}
- Employee Role: {employee_role}
- Social Engineering Attack Type: {attack_type}
- Context/Scenario: {scenario_description}

=== JSON SCHEMA ===
Your response must be JSON only.
{{
  "simulation_title": "Provide a descriptive title for this simulation",
  "attack_type": "{attack_type}",
  "simulation_text": "Create a detailed dialogue script or message. Prefix this field with '[TRAINING SIMULATION ONLY]\\n\\n'. Make it look realistic, contextualized to the role, department, and sector.",
  "manipulation_techniques": [
    {{
      "technique": "Identify which of these is used: Authority, Urgency, Fear, Curiosity, Scarcity, Trust Building, Impersonation, Information Gathering",
      "snippet": "Exact snippet from the simulation_text that demonstrates this technique",
      "danger_explanation": "Explain why this snippet is manipulative/dangerous.",
      "employee_response": "Explain how the employee should identify, resist, and counter this specific tactic."
    }}
  ],
  "emotional_profile": {{
    "fear": integer (0 to 100 representing Fear presence in the message),
    "urgency": integer (0 to 100 representing Urgency presence),
    "authority": integer (0 to 100 representing Authority trigger presence),
    "trust": integer (0 to 100 representing Trust Exploitation presence),
    "curiosity": integer (0 to 100 representing Curiosity exploitation presence),
    "sympathy": integer (0 to 100 representing Sympathy presence),
    "scarcity": integer (0 to 100 representing Scarcity presence)
  }},
  "threat_intelligence": {{
    "category": "Identify threat category (e.g. Credential Harvesting, Financial Redirection, Malware Delivery)",
    "risk_score": integer (0 to 100 representing how dangerous/convincing this attack is),
    "likelihood": "High | Medium | Low",
    "impact": "High | Medium | Low"
  }},
  "mitre_mapping": [
    {{
      "technique_id": "Relevant MITRE ATT&CK technique ID (e.g. T1566.003, T1566.002, T1598.003)",
      "technique_name": "MITRE technique name",
      "description": "Short explanation of how this technique applies to this simulation"
    }}
  ],
  "awareness_card": {{
    "red_flags": ["List at least 3 red flags in the simulation_text"],
    "what_to_do": ["List at least 2 correct actions for the employee"],
    "what_not_to_do": ["List at least 2 dangerous actions to avoid"],
    "reporting_procedure": "Describe the correct procedure for reporting this specific attack type"
  }},
  "quiz": {{
    "mcqs": [
      {{
        "question": "A multiple-choice question testing understanding of this scenario.",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Write the exact correct option text",
        "explanation": "Explain why this option is correct."
      }}
    ],
    "scenario_question": {{
      "question": "A situational question testing how the employee would react in a similar scenario.",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Write the exact correct option text",
      "explanation": "Explain why this response is correct."
    }}
  }}
}}
"""

    # 2. Call the chosen model provider
    if provider == "Llama 3.3 (Groq)":
        try:
            return call_groq_api(groq_api_key, prompt)
        except Exception as e:
            print(f"Groq API Error: {e}. Falling back to Gemini or Sandbox.")
            # Fallback to Gemini if Gemini key is available
            if api_key and api_key != "SANDBOX_DEMO":
                provider = "Gemini"
            else:
                return get_sandbox_fallback(department)

    # Gemini Call (Default/Fallback)
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"Gemini API Error: {e}. Falling back to Sandbox.")
        return get_sandbox_fallback(department)


def get_sandbox_fallback(department: str) -> dict:
    """
    Returns fallback dataset matching the targeted department.
    """
    dep_lower = department.lower()
    if "it" in dep_lower or "helpdesk" in dep_lower or "tech" in dep_lower:
        return SANDBOX_DATA["it_helpdesk"]
    elif "hr" in dep_lower or "resource" in dep_lower:
        return SANDBOX_DATA["hr_department"]
    elif "finance" in dep_lower or "pay" in dep_lower or "bill" in dep_lower:
        return SANDBOX_DATA["finance_department"]
    else:
        return SANDBOX_DATA["it_helpdesk"]
