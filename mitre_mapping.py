"""
MITRE ATT&CK Mapping Module for Social Engineering Attacks.
Provides structured information and mitigation advice for techniques related to vishing, smishing, and pretexting.
"""

MITRE_DATABASE = {
    "T1566.003": {
        "id": "T1566.003",
        "name": "Phishing: Spearphishing Voice (Vishing)",
        "description": "Adversaries may use voice communications (vishing) to direct victims to take actions, such as revealing credentials, providing sensitive information, or executing malicious commands. Vishing relies on social engineering tactics (like authority or urgency) to build trust or intimidate victims.",
        "mitigation": "Establish out-of-band verification procedures for sensitive requests. Train employees to identify voice manipulation tactics and verify caller identity using official corporate directories.",
        "attack_types": ["Vishing", "Pretexting"]
    },
    "T1566.002": {
        "id": "T1566.002",
        "name": "Phishing: Spearphishing Link (Smishing/Phishing)",
        "description": "Adversaries may send phishing messages containing malicious links (smishing over SMS, or phishing over email) to capture credentials or deliver malware. These links often lead to fake login pages or drive-by download sites.",
        "mitigation": "Deploy link inspection/filtering tools. Educate employees to avoid clicking on unsolicited links and inspect URLs carefully before entering credentials.",
        "attack_types": ["Smishing", "Pretexting"]
    },
    "T1598.003": {
        "id": "T1598.003",
        "name": "Phishing for Information: Spearphishing Voice",
        "description": "Adversaries may use phone calls (vishing) specifically targeted at eliciting sensitive information about the organization, individuals, or IT systems. The goal is information gathering to prepare for subsequent attacks.",
        "mitigation": "Implement a strict information disclosure policy. Employees should never disclose organizational details, software versions, or system architectures to unverified callers.",
        "attack_types": ["Vishing", "Pretexting"]
    },
    "T1598.002": {
        "id": "T1598.002",
        "name": "Phishing for Information: Spearphishing Link",
        "description": "Adversaries may send links that guide victims to surveys, forms, or mock login pages designed solely to gather organizational details, passwords, or personal identifiable information (PII).",
        "mitigation": "Ensure web filtering blocks access to untrusted forms. Implement multi-factor authentication (MFA) to prevent compromised credentials from being used.",
        "attack_types": ["Smishing"]
    },
    "T1204.001": {
        "id": "T1204.001",
        "name": "User Execution: Malicious Link",
        "description": "An adversary relies on a user clicking a malicious link to achieve initial access or credential harvesting. This represents the human action step of clicking a link in a smishing or phishing message.",
        "mitigation": "Use browser security configuration, web reputation filters, and security awareness training to reduce employee link-clicking vulnerability.",
        "attack_types": ["Smishing", "Vishing"]
    },
    "T1592": {
        "id": "T1592",
        "name": "Gather Victim Host Information",
        "description": "Before an attack, adversaries may gather information about the victim's host operating systems, applications, and configurations using pretexting or open-source intelligence (OSINT). This information helps them tailor subsequent payloads.",
        "mitigation": "Train service desk staff to verify identities before discussing technical assets. Limit public exposure of detailed software inventories or configuration data.",
        "attack_types": ["Pretexting", "Vishing"]
    },
    "T1593": {
        "id": "T1593",
        "name": "Gather Victim Identity Information",
        "description": "Adversaries may gather information about organizational structure, employee names, roles, and email addresses to make their pretexting campaigns highly customized and believable.",
        "mitigation": "Sanitize public directories, social media profiles, and company websites of detailed employee contact lists and department hierarchies.",
        "attack_types": ["Pretexting"]
    }
}

def get_mitre_mapping(attack_type: str, custom_text: str = "") -> list:
    """
    Returns relevant MITRE ATT&CK techniques based on the attack type and context description.
    """
    attack_type_clean = attack_type.strip().capitalize()
    
    # Filter based on attack type first
    mappings = []
    for tech_id, info in MITRE_DATABASE.items():
        if attack_type_clean in info["attack_types"]:
            mappings.append({
                "technique_id": info["id"],
                "technique_name": info["name"],
                "description": info["description"],
                "mitigation": info["mitigation"]
            })
            
    # Default fallback mapping if none matched
    if not mappings:
        mappings.append({
            "technique_id": "T1566",
            "technique_name": "Phishing",
            "description": "Adversaries may send phishing messages to gain access to victim systems.",
            "mitigation": "Security awareness training, email filtering, and robust endpoint protection."
        })
        
    return mappings
