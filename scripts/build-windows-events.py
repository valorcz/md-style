#!/usr/bin/env python3
"""
scripts/build-windows-events.py
Builds and compiles data/windows-events.json by aggregating authoritative forensic metadata
from the Ultimate Windows Security Encyclopedia and Microsoft Learn Security Auditing reference.

Can be run periodically or within a CI/CD pipeline to refresh forensic event definitions.

Usage:
  python3 scripts/build-windows-events.py
  python3 scripts/build-windows-events.py --refresh
  python3 scripts/build-windows-events.py --add-eids 4624,4688,7045 --refresh
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_OUTPUT = os.path.join(PROJECT_DIR, "data", "windows-events.json")

# Core Windows Event Log Channels
CORE_EVTX_CHANNELS = {
    "Security.evtx": {
        "type": "evtx",
        "id": "Security.evtx",
        "title": "Windows Security Event Log",
        "channel": "Security",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Security.evtx",
        "role": "Primary forensic repository for authentication, user rights assignment, account management, audit policy changes, and object access.",
        "key_events": ["4624 (Logon)", "4625 (Failed Logon)", "4672 (Admin Privs)", "4688 (Process Created)", "4720 (User Created)", "1102 (Log Cleared)"],
        "retention": "Fixed maximum size (typically 20MB to 1GB in Enterprise). Wrap-around overwrite policy.",
        "url": "https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/security-auditing-overview"
    },
    "System.evtx": {
        "type": "evtx",
        "id": "System.evtx",
        "title": "Windows System Event Log",
        "channel": "System",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\System.evtx",
        "role": "Contains events logged by Windows system components, service control manager, hardware changes, kernel drivers, and system startup/shutdown.",
        "key_events": ["7045 (Service Installed)", "7036 (Service State Change)", "104 (Log Cleared)", "1074 (System Shutdown)", "41 (Kernel Power / BSOD)"],
        "retention": "Default 20MB. Circular overwrite policy.",
        "url": "https://learn.microsoft.com/en-us/windows/win32/eventlog/system-event-log"
    },
    "Application.evtx": {
        "type": "evtx",
        "id": "Application.evtx",
        "title": "Windows Application Event Log",
        "channel": "Application",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Application.evtx",
        "role": "Logs software errors, application crashes (WerFault / Event 1000), MSI installer installations (Event 11707), and third-party utility telemetry.",
        "key_events": ["1000 (App Crash)", "1001 (Windows Error Reporting)", "11707 (MSI Install Success)", "11724 (App Uninstalled)"],
        "retention": "Default 20MB circular buffer.",
        "url": "https://learn.microsoft.com/en-us/windows/win32/eventlog/application-event-log"
    },
    "Microsoft-Windows-Sysmon/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Sysmon/Operational.evtx",
        "title": "Microsoft Sysmon Operational Telemetry Log",
        "channel": "Microsoft-Windows-Sysmon/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-Sysmon%4Operational.evtx",
        "role": "Premier endpoint telemetry sensor providing detailed process lineage, network sockets, raw disk access, process memory injection, and pipe/DNS activity.",
        "key_events": ["EID 1 (Process Create)", "EID 3 (Network Connect)", "EID 8 (CreateRemoteThread)", "EID 10 (ProcessAccess)", "EID 11 (FileCreate)", "EID 22 (DNS Query)"],
        "retention": "Typically configured to 64MB - 512MB by SOC engineering.",
        "url": "https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon"
    },
    "Sysmon.evtx": {
        "type": "evtx",
        "id": "Sysmon.evtx",
        "title": "Microsoft Sysmon Operational Telemetry Log",
        "channel": "Microsoft-Windows-Sysmon/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-Sysmon%4Operational.evtx",
        "role": "Premier endpoint telemetry sensor providing detailed process lineage, network sockets, raw disk access, process memory injection, and pipe/DNS activity.",
        "key_events": ["EID 1 (Process Create)", "EID 3 (Network Connect)", "EID 8 (CreateRemoteThread)", "EID 10 (ProcessAccess)", "EID 11 (FileCreate)", "EID 22 (DNS Query)"],
        "retention": "Typically configured to 64MB - 512MB by SOC engineering.",
        "url": "https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon"
    },
    "Microsoft-Windows-PowerShell/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-PowerShell/Operational.evtx",
        "title": "Microsoft PowerShell Operational Log",
        "channel": "Microsoft-Windows-PowerShell/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-PowerShell%4Operational.evtx",
        "role": "Deep PowerShell execution log capturing de-obfuscated script blocks (EID 4104), interactive command invocation (EID 4103), and AMSI bypass attempts.",
        "key_events": ["4104 (ScriptBlock Logging)", "4103 (Pipeline Execution)", "4105 (Started Script)", "4106 (Completed Script)"],
        "retention": "Default 15MB. Highly recommended to increase to 100MB+.",
        "url": "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging_windows"
    },
    "PowerShell.evtx": {
        "type": "evtx",
        "id": "PowerShell.evtx",
        "title": "Microsoft PowerShell Operational Log",
        "channel": "Microsoft-Windows-PowerShell/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-PowerShell%4Operational.evtx",
        "role": "Deep PowerShell execution log capturing de-obfuscated script blocks (EID 4104), interactive command invocation (EID 4103), and AMSI bypass attempts.",
        "key_events": ["4104 (ScriptBlock Logging)", "4103 (Pipeline Execution)", "4105 (Started Script)", "4106 (Completed Script)"],
        "retention": "Default 15MB. Highly recommended to increase to 100MB+.",
        "url": "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging_windows"
    },
    "Microsoft-Windows-TaskScheduler/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-TaskScheduler/Operational.evtx",
        "title": "Windows Task Scheduler Operational Log",
        "channel": "Microsoft-Windows-TaskScheduler/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-TaskScheduler%4Operational.evtx",
        "role": "Monitors creation, execution, and modification of scheduled tasks (primary persistence mechanism for lateral movement and C2 triggers).",
        "key_events": ["106 (Task Registered)", "140 (Task Updated)", "200 (Action Started)", "201 (Action Completed)"],
        "retention": "Default 1MB. Wrap-around.",
        "url": "https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page"
    },
    "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
        "title": "RDP Local Session Manager Log",
        "channel": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx",
        "role": "Records interactive and Remote Desktop (RDP) session connect, disconnect, and reconnect transitions with source IP mapping.",
        "key_events": ["21 (Session Logon Succeeded)", "24 (Session Disconnected)", "25 (Session Reconnected)"],
        "retention": "Default 1MB.",
        "url": "https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/welcome-to-rds"
    },
    "Microsoft-Windows-Windows Defender/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Windows Defender/Operational.evtx",
        "title": "Microsoft Defender Antivirus Operational Log",
        "channel": "Microsoft-Windows-Windows Defender/Operational",
        "path": "%SystemRoot%\\System32\\Winevt\\Logs\\Microsoft-Windows-Windows%20Defender%4Operational.evtx",
        "role": "Exposes real-time threat detections, quarantined payloads, AMSI blocks, and tamper protection overrides.",
        "key_events": ["1116 (Malware Detected)", "1117 (Action Taken / Cleaned)", "5001 (Real-Time Protection Disabled)"],
        "retention": "Default 16MB.",
        "url": "https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/troubleshoot-microsoft-defender-antivirus"
    }
}

# Core Forensic Event Definitions with rich contextual analysis
CORE_FORENSIC_EVENTS = {
    "4624": {
        "channel": "Security",
        "category": "Logon / Authentication",
        "severity": "AUDIT SUCCESS",
        "summary": "Records successful authentication sessions. The LogonType code discloses how authentication occurred: 2 (Interactive Console), 3 (Network / SMB / WMI), 5 (Service), 9 (NewCredentials / Pass-the-Hash / Mimikatz), 10 (RemoteInteractive / RDP).",
        "key_fields": ["LogonType", "TargetUserName", "TargetDomainName", "IpAddress", "WorkstationName", "ProcessName", "ElevatedToken"],
        "mitre": ["T1078 (Valid Accounts)", "T1021.001 (Remote Desktop Protocol)", "T1021.002 (SMB/Windows Admin Shares)"]
    },
    "4625": {
        "channel": "Security",
        "category": "Logon / Authentication",
        "severity": "AUDIT FAILURE",
        "summary": "Records failed authentication attempts. Vital for identifying brute force attacks, credential stuffing, and password spraying. Status/SubStatus codes reveal specific failure reasons (e.g. 0xC000006A: wrong password, 0xC0000064: user doesn't exist, 0xC000006D: bad credentials, 0xC0000234: account locked).",
        "key_fields": ["Status", "SubStatus", "TargetUserName", "WorkstationName", "IpAddress", "FailureReason", "ProcessName"],
        "mitre": ["T1110 (Brute Force)", "T1110.003 (Password Spraying)"]
    },
    "4672": {
        "channel": "Security",
        "category": "Privilege Use",
        "severity": "AUDIT SUCCESS",
        "summary": "Special administrative privileges assigned to a new logon session. Logged immediately following event 4624 when an account possessing sensitive rights logs in. Sensitive privileges include SeDebugPrivilege, SeTcbPrivilege, SeSecurityPrivilege, SeBackupPrivilege.",
        "key_fields": ["SubjectUserName", "SubjectDomainName", "PrivilegeList"],
        "mitre": ["T1078 (Valid Accounts)", "T1068 (Exploitation for Privilege Escalation)"]
    },
    "4688": {
        "channel": "Security",
        "category": "Detailed Tracking",
        "severity": "AUDIT SUCCESS",
        "summary": "Tracks execution of all binaries. When CommandLine auditing policy is active, exposes full script execution arguments, PowerShell one-liners, and living-off-the-land commands.",
        "key_fields": ["NewProcessName", "CommandLine", "ParentProcessName", "SubjectUserName", "TokenElevationType"],
        "mitre": ["T1059 (Command and Scripting Interpreter)", "T1105 (Ingress Tool Transfer)"]
    },
    "4697": {
        "channel": "Security",
        "category": "System / Service Install",
        "severity": "AUDIT SUCCESS",
        "summary": "A service was installed in the system. Logged in Security.evtx with service account details and service binary path. High fidelity persistence and lateral movement indicator (e.g. PsExec, malware services).",
        "key_fields": ["ServiceName", "ServiceFileName", "ServiceType", "ServiceStartType", "ServiceAccount"],
        "mitre": ["T1543.003 (Create or Modify System Process: Windows Service)"]
    },
    "7045": {
        "channel": "System",
        "category": "System / Service Install",
        "severity": "SYSTEM NOTICE",
        "summary": "A new service was installed on the system (logged by Service Control Manager in System.evtx). Primary source for discovering backdoor persistence and remote execution services.",
        "key_fields": ["ServiceName", "ImagePath", "ServiceType", "StartType", "AccountName"],
        "mitre": ["T1543.003 (Create or Modify System Process: Windows Service)"]
    },
    "4720": {
        "channel": "Security",
        "category": "Account Management",
        "severity": "AUDIT SUCCESS",
        "summary": "A user account was created. Critical indicator for unauthorized persistence, rogue backdoor creation, or shadow admin accounts.",
        "key_fields": ["TargetUserName", "TargetDomainName", "SubjectUserName", "SubjectDomainName", "SamAccountName"],
        "mitre": ["T1136.001 (Create Account: Local Account)", "T1136.002 (Create Account: Domain Account)"]
    },
    "4726": {
        "channel": "Security",
        "category": "Account Management",
        "severity": "AUDIT SUCCESS",
        "summary": "A user account was deleted. Often used by attackers to clean up temporary staging accounts or cover lateral tracks.",
        "key_fields": ["TargetUserName", "TargetDomainName", "SubjectUserName"],
        "mitre": ["T1531 (Account Access Removal)"]
    },
    "4728": {
        "channel": "Security",
        "category": "Account Management",
        "severity": "AUDIT SUCCESS",
        "summary": "A member was added to a security-enabled global group (e.g. Domain Admins, Enterprise Admins). A premier privilege escalation indicator in Active Directory breaches.",
        "key_fields": ["MemberName", "TargetGroupName", "SubjectUserName", "SubjectDomainName"],
        "mitre": ["T1098 (Account Manipulation)", "T1078 (Valid Accounts)"]
    },
    "4732": {
        "channel": "Security",
        "category": "Account Management",
        "severity": "AUDIT SUCCESS",
        "summary": "A member was added to a security-enabled local group (e.g. local Administrators, Remote Desktop Users). Indicates local privilege escalation.",
        "key_fields": ["MemberName", "TargetGroupName", "SubjectUserName"],
        "mitre": ["T1098 (Account Manipulation)"]
    },
    "4738": {
        "channel": "Security",
        "category": "Account Management",
        "severity": "AUDIT SUCCESS",
        "summary": "A user account was modified. Highlights account tampering such as password never expires, account enabled/disabled, UserAccountControl flags changed, or Kerberos pre-authentication disabled.",
        "key_fields": ["TargetUserName", "SubjectUserName", "UserAccountControl", "PasswordLastSet"],
        "mitre": ["T1098 (Account Manipulation)"]
    },
    "4768": {
        "channel": "Security",
        "category": "Kerberos Authentication",
        "severity": "AUDIT SUCCESS",
        "summary": "A Kerberos authentication ticket (TGT) was requested. Key forensic event for Golden Ticket verification and domain controller authentication telemetry.",
        "key_fields": ["TargetUserName", "IpAddress", "TicketOptions", "ResultCode"],
        "mitre": ["T1558.001 (Steal or Forge Kerberos Tickets: Golden Ticket)"]
    },
    "4769": {
        "channel": "Security",
        "category": "Kerberos Service Ticket",
        "severity": "AUDIT SUCCESS",
        "summary": "A Kerberos service ticket (TGS) was requested. Ticket encryption type 0x17 (RC4) indicates potential Kerberoasting attack against service account SPNs.",
        "key_fields": ["ServiceName", "TargetUserName", "TicketEncryptionType", "TicketOptions", "IpAddress"],
        "mitre": ["T1558.003 (Steal or Forge Kerberos Tickets: Kerberoasting)"]
    },
    "4771": {
        "channel": "Security",
        "category": "Kerberos Pre-Authentication",
        "severity": "AUDIT FAILURE",
        "summary": "Kerberos pre-authentication failed. Failure code 0x18 indicates wrong password; high volume indicates AS-REP roasting or password spraying.",
        "key_fields": ["TargetUserName", "IpAddress", "FailureCode"],
        "mitre": ["T1558.004 (Steal or Forge Kerberos Tickets: AS-REP Roasting)"]
    },
    "4776": {
        "channel": "Security",
        "category": "Credential Validation",
        "severity": "AUDIT SUCCESS / FAILURE",
        "summary": "The computer attempted to validate credentials for an account (NTLM authentication). Error code 0xC000006A denotes bad password.",
        "key_fields": ["PackageName", "TargetUserName", "Workstation", "Status"],
        "mitre": ["T1110 (Brute Force)"]
    },
    "1102": {
        "channel": "Security",
        "category": "Log Clear / Anti-Forensics",
        "severity": "CRITICAL AUDIT",
        "summary": "Logged when the Security event log is cleared via wevtutil cl Security, PowerShell Clear-EventLog, or attacker scripts. Always treated as an active malicious tampering indicator.",
        "key_fields": ["SubjectUserName", "SubjectDomainName", "SubjectLogonId"],
        "mitre": ["T1070.001 (Clear Windows Event Logs)"]
    },
    "104": {
        "channel": "System",
        "category": "Log Clear / Anti-Forensics",
        "severity": "CRITICAL AUDIT",
        "summary": "The log file was cleared (logged by eventlog service in System.evtx when System or Application log is wiped).",
        "key_fields": ["SubjectUserName", "SubjectDomainName"],
        "mitre": ["T1070.001 (Clear Windows Event Logs)"]
    },
    "4104": {
        "channel": "Microsoft-Windows-PowerShell/Operational",
        "category": "PowerShell Execution",
        "severity": "AUDIT SUCCESS",
        "summary": "Script block logging. Captures complete, un-obfuscated script content and commands executed by PowerShell 5.0+, defeating base64/xor obfuscation.",
        "key_fields": ["ScriptBlockText", "Path", "UserId"],
        "mitre": ["T1059.001 (Command and Scripting Interpreter: PowerShell)"]
    },
    "4103": {
        "channel": "Microsoft-Windows-PowerShell/Operational",
        "category": "PowerShell Execution",
        "severity": "AUDIT SUCCESS",
        "summary": "PowerShell pipeline execution logging. Records pipeline invocation details and command line parameters.",
        "key_fields": ["Payload", "CommandLine", "ContextInfo"],
        "mitre": ["T1059.001 (Command and Scripting Interpreter: PowerShell)"]
    },
    "Sysmon-1": {
        "channel": "Sysmon",
        "category": "Process Creation",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 1 (Process Create). Provides full process command line, image path, parent process image, hashes (SHA256), and integrity level.",
        "key_fields": ["UtcTime", "ProcessGuid", "Image", "CommandLine", "CurrentDirectory", "User", "ParentImage", "ParentCommandLine", "Hashes"],
        "mitre": ["T1059 (Command and Scripting Interpreter)"]
    },
    "Sysmon-3": {
        "channel": "Sysmon",
        "category": "Network Connection",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 3 (Network Connection). Discloses TCP/UDP connections initiated by binaries, with source/dest IP, port, and resolved hostname.",
        "key_fields": ["UtcTime", "Image", "User", "Protocol", "SourceIp", "SourcePort", "DestinationIp", "DestinationPort", "DestinationHostname"],
        "mitre": ["T1071 (Application Layer Protocol)", "T1043 (Commonly Used Port)"]
    },
    "Sysmon-7": {
        "channel": "Sysmon",
        "category": "Image Loaded",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 7 (Image Loaded). Logs DLLs and modules loaded into process memory. Key for DLL hijacking and sideloading investigation.",
        "key_fields": ["UtcTime", "Image", "ImageLoaded", "Hashes", "Signed", "SignatureStatus"],
        "mitre": ["T1574.002 (DLL Side-Loading)"]
    },
    "Sysmon-8": {
        "channel": "Sysmon",
        "category": "Process Injection",
        "severity": "CRITICAL TELEMETRY",
        "summary": "Sysmon Event ID 8 (CreateRemoteThread). Detects thread injection into another process address space (classic shellcode injection, Cobalt Strike beacons, Mimikatz).",
        "key_fields": ["UtcTime", "SourceImage", "TargetImage", "StartAddress", "StartFunction"],
        "mitre": ["T1055.002 (Process Injection: Portable Executable Injection)"]
    },
    "Sysmon-10": {
        "channel": "Sysmon",
        "category": "Process Access",
        "severity": "CRITICAL TELEMETRY",
        "summary": "Sysmon Event ID 10 (ProcessAccess). Detects processes opening handles to target processes. Primary detector for LSASS memory dumping (Mimikatz, Procdump).",
        "key_fields": ["UtcTime", "SourceImage", "TargetImage", "GrantedAccess", "CallTrace"],
        "mitre": ["T1003.001 (OS Credential Dumping: LSASS Memory)"]
    },
    "Sysmon-11": {
        "channel": "Sysmon",
        "category": "File Creation",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 11 (FileCreate). Logs creation or overwrite of files on disk. Tracks dropped ransomware notes, malware payloads, and staging archives.",
        "key_fields": ["UtcTime", "ProcessGuid", "Image", "TargetFilename", "CreationUtcTime"],
        "mitre": ["T1105 (Ingress Tool Transfer)"]
    },
    "Sysmon-12": {
        "channel": "Sysmon",
        "category": "Registry Modification",
        "severity": "MEDIUM TELEMETRY",
        "summary": "Sysmon Event ID 12 (RegistryEvent: Object create and delete). Monitors registry key creation/deletion.",
        "key_fields": ["EventType", "UtcTime", "Image", "TargetObject"],
        "mitre": ["T1112 (Modify Registry)"]
    },
    "Sysmon-13": {
        "channel": "Sysmon",
        "category": "Registry Persistence",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 13 (RegistryEvent: Value Set). Discloses registry values written to Run/RunOnce, Services, or COM hijack keys.",
        "key_fields": ["EventType", "UtcTime", "Image", "TargetObject", "Details"],
        "mitre": ["T1547.001 (Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder)"]
    },
    "Sysmon-22": {
        "channel": "Sysmon",
        "category": "DNS Query",
        "severity": "HIGH TELEMETRY",
        "summary": "Sysmon Event ID 22 (DNSEvent: DNS query). Records DNS lookups initiated by endpoint processes. Essential for C2 domain beaconing and DGA analysis.",
        "key_fields": ["UtcTime", "Image", "QueryName", "QueryStatus", "QueryResults"],
        "mitre": ["T1071.004 (Application Layer Protocol: DNS)"]
    }
}


def scrape_uws_event(eid: str) -> dict:
    """Scrapes event title, category, and description from Ultimate Windows Security."""
    clean_eid = re.sub(r'^[^\d]*', '', eid)
    if not clean_eid.isdigit():
        return {}

    url = f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={clean_eid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity-Forensic/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # Title: e.g. <title>Windows Security Log Event ID 4624 - An account was successfully logged on</title>
        m_title = re.search(r'<title>Windows Security Log Event ID \d+\s*[-–]\s*(.*?)</title>', html, re.I)
        title = m_title.group(1).strip() if m_title else None

        # Category from span
        m_cat = re.search(r'Category:.*?<span[^>]*>(.*?)</span>', html, re.I | re.DOTALL)
        cat = m_cat.group(1).strip() if m_cat else None

        return {
            "title": title,
            "category": cat,
            "url": url
        }
    except Exception as err:
        return {}


def build_events_dataset(output_path: str = DEFAULT_OUTPUT, refresh_online: bool = False, extra_eids: list = None, verbose: bool = False):
    print(f"[WINDOWS EVENTS BUILDER] Assembling dataset -> {output_path}")
    dataset = {}

    # 1. Add EVTX channels
    for name, data in CORE_EVTX_CHANNELS.items():
        dataset[name] = data
        # Also alias without directory path
        base = os.path.basename(name)
        if base not in dataset:
            dataset[base] = data

    # 2. Build Event IDs list
    eids_to_process = list(CORE_FORENSIC_EVENTS.keys())
    if extra_eids:
        for eid in extra_eids:
            clean = eid.strip()
            if clean and clean not in eids_to_process:
                eids_to_process.append(clean)

    for eid_key in eids_to_process:
        clean_num = re.sub(r'^[^\d]*', '', eid_key)
        curated = CORE_FORENSIC_EVENTS.get(eid_key, {})

        title = curated.get("title", f"Event ID {clean_num}")
        category = curated.get("category", "Windows Security")
        severity = curated.get("severity", "AUDIT EVENT")
        summary = curated.get("summary", f"Windows audit telemetry record for Event ID {clean_num}.")
        channel = curated.get("channel", "Security")
        key_fields = curated.get("key_fields", [])
        mitre = curated.get("mitre", [])
        url = f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={clean_num}"

        # If refresh_online is enabled and it's a numeric security event ID, scrape UWS
        if refresh_online and clean_num.isdigit():
            if verbose:
                print(f"[FETCH] Querying Ultimate Windows Security for Event ID {clean_num}...")
            live = scrape_uws_event(clean_num)
            if live.get("title"):
                title = live["title"]
            if live.get("category"):
                category = live["category"]
            time.sleep(0.3)  # Gentle rate limit

        record = {
            "type": "eventid",
            "id": clean_num,
            "title": title,
            "channel": channel,
            "category": category,
            "severity": severity,
            "summary": summary,
            "key_fields": key_fields,
            "mitre": mitre,
            "url": url
        }

        # Index primary key and common lookup variations
        dataset[eid_key] = record
        dataset[f"Event ID {clean_num}"] = record
        dataset[f"EID {clean_num}"] = record
        dataset[clean_num] = record

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"[SUCCESS] Compiled {len(dataset)} Windows Event records -> {output_path} ({size_kb:.1f} KB)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Compile Windows Event Log forensic intelligence dataset.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="Target JSON destination path")
    parser.add_argument("-r", "--refresh", action="store_true", help="Scrape live titles & categories from Ultimate Windows Security")
    parser.add_argument("--add-eids", default="", help="Comma-separated additional Event IDs to include")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    extras = [e.strip() for e in args.add_eids.split(",") if e.strip()] if args.add_eids else None
    sys.exit(build_events_dataset(args.output, args.refresh, extras, args.verbose))


if __name__ == "__main__":
    main()
