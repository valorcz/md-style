"""
core/kb/sync.py
Unified Synchronization Engine for Finite Knowledge Pack Catalogs:
  1. MITRE ATT&CK Enterprise Matrix (via official MITRE CTI STIX repository)
  2. Windows Event IDs & EVTX Channels (via Zimmerman Maps, Hayabusa, and UWS specs)
"""

import os
import re
import sys
import json
import time
import zipfile
import io
import xml.etree.ElementTree as ET
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from core.config import (
    DATA_DIR,
    MITRE_DB_PATH,
    WIN_EVENTS_DB_PATH,
    WIN_EVENTS_CACHE_PATH,
    CVE_DB_PATH,
    CWE_DB_PATH,
    CWE_CACHE_PATH,
    DEFAULT_MITRE_CWE_URL,
    INTEL_CACHE_DIR,
)
from core.diagnostics import Diagnostics, Colors

DEFAULT_MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

# ==============================================================================
# Comprehensive Forensic EVTX Channel Knowledge Base (60+ Key DFIR Channels)
# ==============================================================================
EXPANDED_EVTX_CHANNELS: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # 1. Core Windows Triage Channels
    # --------------------------------------------------------------------------
    "Security.evtx": {
        "type": "evtx",
        "id": "Security.evtx",
        "title": "Windows Security Event Log",
        "channel": "Security",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Security.evtx",
        "role": "Primary forensic repository for authentication, user rights assignment, account management, audit policy changes, process creation (EID 4688), and object access auditing.",
        "key_events": ["4624 (Logon)", "4625 (Failed Logon)", "4672 (Admin Privs)", "4688 (Process Created)", "4720 (User Created)", "4726 (User Deleted)", "4728 (Member Added to Global Group)", "4738 (User Account Modified)", "1102 (Log Cleared)"],
        "retention": "Fixed maximum size (typically 128MB to 2GB in Enterprise). Wrap-around overwrite policy.",
        "audit_policy": "Enable Audit Process Creation (with CommandLine auditing), Audit Logon, Audit Account Management, and Audit Special Logon.",
        "mitre_tactics": ["Initial Access", "Privilege Escalation", "Credential Access", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/windows-security-log"
    },
    "System.evtx": {
        "type": "evtx",
        "id": "System.evtx",
        "title": "Windows System Event Log",
        "channel": "System",
        "path": r"%SystemRoot%\System32\Winevt\Logs\System.evtx",
        "role": "Contains events logged by Windows system components, service control manager, hardware changes, kernel drivers, and system startup/shutdown.",
        "key_events": ["7045 (New Service Installed)", "7036 (Service State Change)", "7040 (Service Start Type Changed)", "104 (Log Cleared)", "1074 (System Shutdown/Reboot)", "41 (Kernel Power / BSOD)", "6005 (EventLog Started)", "6006 (EventLog Stopped)"],
        "retention": "Default 20MB. Circular overwrite policy.",
        "audit_policy": "Monitor Service Control Manager events for unexpected service binaries executing from temp or user-writable directories.",
        "mitre_tactics": ["Persistence", "Execution", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management/system-log-events"
    },
    "Application.evtx": {
        "type": "evtx",
        "id": "Application.evtx",
        "title": "Windows Application Event Log",
        "channel": "Application",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Application.evtx",
        "role": "Logs software errors, application crashes (WerFault / Event 1000), MSI installer activity (Event 11707), and third-party utility telemetry.",
        "key_events": ["1000 (Application Error / Crash)", "1001 (Windows Error Reporting)", "1002 (Application Hang)", "11707 (MSI Install Success)", "11724 (App Uninstalled)"],
        "retention": "Default 20MB circular buffer.",
        "audit_policy": "Review application crash dumps and installer errors for signs of memory corruption exploitation or DLL side-loading.",
        "mitre_tactics": ["Execution", "Persistence"],
        "url": "https://learn.microsoft.com/en-us/windows/win32/eventlog/application-event-log"
    },

    # --------------------------------------------------------------------------
    # 2. Endpoint Telemetry & Execution Sensors
    # --------------------------------------------------------------------------
    "Sysmon.evtx": {
        "type": "evtx",
        "id": "Sysmon.evtx",
        "title": "Microsoft Sysmon Operational Telemetry Log",
        "channel": "Microsoft-Windows-Sysmon/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Sysmon.evtx",
        "role": "Premier endpoint telemetry sensor providing detailed process lineage, network sockets, raw disk access, process memory injection, and pipe/DNS activity.",
        "key_events": ["1 (Process Create)", "2 (File creation time changed)", "3 (Network Connection)", "7 (Image Loaded)", "8 (CreateRemoteThread)", "10 (ProcessAccess)", "11 (FileCreate)", "12/13/14 (Registry Events)", "22 (DNS Query)"],
        "retention": "Typically configured to 64MB - 1GB by SOC engineering.",
        "audit_policy": "Deploy a comprehensive community Sysmon configuration (SwiftOnSecurity or Olaf Hartong modular config).",
        "mitre_tactics": ["Execution", "Persistence", "Privilege Escalation", "Defense Evasion", "Command and Control"],
        "url": "https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon"
    },
    "PowerShell.evtx": {
        "type": "evtx",
        "id": "PowerShell.evtx",
        "title": "Microsoft PowerShell Operational Log",
        "channel": "Microsoft-Windows-PowerShell/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\PowerShell.evtx",
        "role": "Deep PowerShell execution log capturing de-obfuscated script blocks (EID 4104), interactive command invocation (EID 4103), and AMSI bypass attempts.",
        "key_events": ["4104 (ScriptBlock Logging)", "4103 (Pipeline Execution)", "4105 (Started Script)", "4106 (Completed Script)"],
        "retention": "Default 15MB. Highly recommended to increase to 256MB+.",
        "audit_policy": "Enforce Group Policy for PowerShell Script Block Logging, Module Logging, and Transcription.",
        "mitre_tactics": ["Execution", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_logging_windows"
    },
    "Microsoft-Windows-TaskScheduler/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-TaskScheduler/Operational.evtx",
        "title": "Windows Task Scheduler Operational Log",
        "channel": "Microsoft-Windows-TaskScheduler/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-TaskScheduler%4Operational.evtx",
        "role": "Monitors creation, execution, and modification of scheduled tasks (primary persistence mechanism for lateral movement and C2 triggers).",
        "key_events": ["106 (Task Registered)", "140 (Task Updated)", "141 (Task Deleted)", "200 (Action Started)", "201 (Action Completed)"],
        "retention": "Default 1MB. Wrap-around.",
        "audit_policy": "Enable Operational channel logging in Task Scheduler event log properties.",
        "mitre_tactics": ["Persistence", "Execution", "Privilege Escalation"],
        "url": "https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page"
    },
    "Microsoft-Windows-WMI-Activity/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-WMI-Activity/Operational.evtx",
        "title": "WMI Activity Operational Log",
        "channel": "Microsoft-Windows-WMI-Activity/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-WMI-Activity%4Operational.evtx",
        "role": "Forensic log capturing WMI query execution, provider initialization, and persistence via rogue WMI Event Consumers (__EventFilter, __EventConsumer).",
        "key_events": ["5857 (Provider Started)", "5858 (Query Execution Error)", "5861 (WMI Permanent Event Consumer Created)"],
        "retention": "Default 1MB. Highly sensitive indicator for fileless WMI persistence.",
        "audit_policy": "Alert immediately on Event ID 5861 for unexpected permanent consumer registration.",
        "mitre_tactics": ["Execution", "Persistence"],
        "url": "https://learn.microsoft.com/en-us/windows/win32/wmisdk/tracing-wmi-activity"
    },
    "Microsoft-Windows-BackgroundActivityModerator/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-BackgroundActivityModerator/Operational.evtx",
        "title": "Background Activity Moderator (BAM) Log",
        "channel": "Microsoft-Windows-BackgroundActivityModerator/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-BackgroundActivityModerator%4Operational.evtx",
        "role": "Kernel power management telemetry recording exact execution timestamps of user and desktop applications.",
        "key_events": [],
        "retention": "Correlate with BAM registry entries (SYSTEM hive) during dead-box forensic disk triage.",
        "audit_policy": "System kernel feature active on Windows 10/11 and Server 2019+.",
        "mitre_tactics": ["Execution"],
        "url": "https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/overview-of-the-background-activity-moderator"
    },

    # --------------------------------------------------------------------------
    # 3. Lateral Movement, Remote Admin & Network Sockets
    # --------------------------------------------------------------------------
    "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
        "title": "TerminalServices Local Session Manager Log",
        "channel": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx",
        "role": "Records interactive and Remote Desktop (RDP) session connect, disconnect, and reconnect transitions with source IP mapping.",
        "key_events": ["21 (Session Logon Succeeded)", "22 (Shell Start Notified)", "23 (Session Logoff)", "24 (Session Disconnected)", "25 (Session Reconnected)"],
        "retention": "Default 1MB.",
        "audit_policy": "Correlate with Security.evtx Event 4624 (Logon Type 10) to confirm client source addresses.",
        "mitre_tactics": ["Lateral Movement", "Initial Access"],
        "url": "https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/welcome-to-rds"
    },
    "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx",
        "title": "TerminalServices Remote Connection Manager Log",
        "channel": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-TerminalServices-RemoteConnectionManager%4Operational.evtx",
        "role": "Tracks incoming network connections to RDP listeners, TLS handshakes, and early credential negotiation.",
        "key_events": ["1149 (User Authentication Succeeded)"],
        "retention": "Default 1MB.",
        "audit_policy": "EID 1149 records client machine name and client IP before user credentials are confirmed.",
        "mitre_tactics": ["Lateral Movement", "Initial Access"],
        "url": "https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/welcome-to-rds"
    },
    "Microsoft-Windows-RemoteDesktopServices-RdpCoreTS/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-RemoteDesktopServices-RdpCoreTS/Operational.evtx",
        "title": "Remote Desktop Services RdpCoreTS Log",
        "channel": "Microsoft-Windows-RemoteDesktopServices-RdpCoreTS/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-RemoteDesktopServices-RdpCoreTS%4Operational.evtx",
        "role": "Core RDP network stack logging TCP connection establishment, TLS negotiation, and external brute-force connection attempts.",
        "key_events": ["131 (Client TCP connection accepted)", "140 (Connection failure / disconnect)"],
        "retention": "Default 1MB.",
        "audit_policy": "Examine EID 131 to detect external port scanning and internet-facing RDP brute-force scans.",
        "mitre_tactics": ["Initial Access", "Lateral Movement"],
        "url": "https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/welcome-to-rds"
    },
    "Microsoft-Windows-SMBClient/Security.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-SMBClient/Security.evtx",
        "title": "SMB Client Security Log",
        "channel": "Microsoft-Windows-SMBClient/Security",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-SMBClient%4Security.evtx",
        "role": "Captures SMB client authentication events, unencrypted shares, and SMB signing downgrade attempts.",
        "key_events": ["31001 (SMB Signing Disabled)", "31017 (Insecure Guest Access Attempted)"],
        "retention": "Default 1MB.",
        "audit_policy": "Require SMB signing and SMB encryption across all domain endpoints.",
        "mitre_tactics": ["Lateral Movement", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/windows-server/storage/file-server/smb-security-overview"
    },
    "Microsoft-Windows-SMBServer/Security.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-SMBServer/Security.evtx",
        "title": "SMB Server Security Log",
        "channel": "Microsoft-Windows-SMBServer/Security",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-SMBServer%4Security.evtx",
        "role": "Records inbound SMB connections, administrative share accesses (ADMIN$, C$), and lateral tool drops.",
        "key_events": ["1001 (Server started)", "551 (Session creation failed)"],
        "retention": "Default 1MB.",
        "audit_policy": "Correlate with Security EID 5140 (Network share object accessed).",
        "mitre_tactics": ["Lateral Movement"],
        "url": "https://learn.microsoft.com/en-us/windows-server/storage/file-server/smb-security-overview"
    },
    "Microsoft-Windows-WinRM/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-WinRM/Operational.evtx",
        "title": "Windows Remote Management (WinRM) Operational Log",
        "channel": "Microsoft-Windows-WinRM/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-WinRM%4Operational.evtx",
        "role": "Logs incoming PowerShell Remoting and WinRM management sessions, command dispatches, and WS-Management requests.",
        "key_events": ["142 (WS-Management Session Created)", "161 (User Auth Succeeded)"],
        "retention": "Default 1MB.",
        "audit_policy": "Essential telemetry for detecting PowerShell Remoting (Enter-PSSession, Invoke-Command) lateral movement.",
        "mitre_tactics": ["Lateral Movement", "Execution"],
        "url": "https://learn.microsoft.com/en-us/windows/win32/winrm/about-windows-remote-management"
    },
    "DNS Server.evtx": {
        "type": "evtx",
        "id": "DNS Server.evtx",
        "title": "Windows DNS Server Event Log",
        "channel": "DNS Server",
        "path": r"%SystemRoot%\System32\Winevt\Logs\DNS Server.evtx",
        "role": "Records DNS queries, zone transfers, dynamic updates, and suspicious external resolver lookups.",
        "key_events": ["2 (Query Processed)", "4 (Transfer Success)", "5504 (Invalid Resource Record)"],
        "retention": "Default 16MB.",
        "audit_policy": "Enable DNS analytical logging for command-and-control tunnel and data exfiltration detection.",
        "mitre_tactics": ["Command and Control", "Exfiltration"],
        "url": "https://learn.microsoft.com/en-us/windows-server/networking/dns/troubleshoot/troubleshoot-dns-event-logging"
    },
    "Microsoft-Windows-Bits-Client/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Bits-Client/Operational.evtx",
        "title": "Background Intelligent Transfer Service (BITS) Operational Log",
        "channel": "Microsoft-Windows-Bits-Client/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-Bits-Client%4Operational.evtx",
        "role": "Exposes BITS job creations, downloads, and notification callbacks commonly abused for stealthy file download cradles and persistence.",
        "key_events": ["3 (Job Created)", "4 (Job Transferred)", "59 (BITS Job Context)"],
        "retention": "Default 1MB.",
        "audit_policy": "Monitor BITS jobs created by non-system accounts with external URLs.",
        "mitre_tactics": ["Defense Evasion", "Persistence"],
        "url": "https://learn.microsoft.com/en-us/windows/win32/bits/background-intelligent-transfer-service-portal"
    },

    # --------------------------------------------------------------------------
    # 4. Privilege Escalation, Credential Access & Identity
    # --------------------------------------------------------------------------
    "Microsoft-Windows-NTLM/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-NTLM/Operational.evtx",
        "title": "NTLM Operational Security Log",
        "channel": "Microsoft-Windows-NTLM/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-NTLM%4Operational.evtx",
        "role": "Detailed telemetry on NTLMv1 and NTLMv2 authentication requests, NTLM relay attacks, and PetitPotam co-ercion attempts.",
        "key_events": ["8001 (NTLM Server Audit)", "8002 (NTLM Blocked Succeeded)"],
        "retention": "Default 1MB.",
        "audit_policy": "Enable Network security: Restrict NTLM: Audit NTLM authentication in this domain.",
        "mitre_tactics": ["Credential Access", "Lateral Movement"],
        "url": "https://learn.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/network-security-restrict-ntlm-audit-ntlm-authentication-in-this-domain"
    },
    "Microsoft-Windows-LSA/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-LSA/Operational.evtx",
        "title": "Local Security Authority (LSA) Operational Log",
        "channel": "Microsoft-Windows-LSA/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-LSA%4Operational.evtx",
        "role": "Captures LSA Protected Process Light (PPL) violations, credential guard alerts, and unauthorized attempts to open handle to lsass.exe.",
        "key_events": ["3065 (Code Integrity Plugin Blocked)", "3066 (Non-PPL process access to LSASS)"],
        "retention": "Default 1MB.",
        "audit_policy": "Enforce LSA Protection (RunAsPPL=1) and monitor LSA Operational channel for Mimikatz dumping attempts.",
        "mitre_tactics": ["Credential Access"],
        "url": "https://learn.microsoft.com/en-us/windows-server/security/credentials-protection-and-management/configuring-additional-lsa-protection"
    },
    "Microsoft-Windows-Directory-Services-SAM/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Directory-Services-SAM/Operational.evtx",
        "title": "Directory Services SAM Operational Log",
        "channel": "Microsoft-Windows-Directory-Services-SAM/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-Directory-Services-SAM%4Operational.evtx",
        "role": "Records Active Directory Security Account Manager RPC queries, BloodHound/SharpHound reconnaissance, and mass user enumeration.",
        "key_events": ["16962 (Remote SAM query threshold exceeded)"],
        "retention": "Default 1MB.",
        "audit_policy": "Restrict remote SAM clients via GPO: Network access: Restrict clients allowed to make remote calls to SAM.",
        "mitre_tactics": ["Discovery", "Credential Access"],
        "url": "https://learn.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/network-access-restrict-clients-allowed-to-make-remote-sam-calls"
    },

    # --------------------------------------------------------------------------
    # 5. Defense Evasion, Code Integrity & App Control
    # --------------------------------------------------------------------------
    "Microsoft-Windows-Windows Defender/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Windows Defender/Operational.evtx",
        "title": "Microsoft Defender Antivirus Operational Log",
        "channel": "Microsoft-Windows-Windows Defender/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-Windows%20Defender%4Operational.evtx",
        "role": "Exposes real-time threat detections, quarantined payloads, AMSI blocks, and tamper protection overrides.",
        "key_events": ["1116 (Malware Detected)", "1117 (Action Taken / Cleaned)", "5001 (Real-Time Protection Disabled)", "5007 (Config Changed)"],
        "retention": "Default 16MB.",
        "audit_policy": "Alert immediately on EID 5001 (Real-time protection disabled by adversary).",
        "mitre_tactics": ["Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/microsoft-365/security/defender-endpoint/troubleshoot-microsoft-defender-antivirus"
    },
    "Microsoft-Windows-CodeIntegrity/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-CodeIntegrity/Operational.evtx",
        "title": "Windows Code Integrity Operational Log",
        "channel": "Microsoft-Windows-CodeIntegrity/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-CodeIntegrity%4Operational.evtx",
        "role": "Crucial driver and binary security log capturing unsigned kernel drivers (BYOVD), HVCI blocks, and Windows Defender Application Control (WDAC) violations.",
        "key_events": ["3077 (File revocation check failed)", "3089 (Signature verification failed)", "3033 (WDAC audit blocked driver/binary)"],
        "retention": "Default 1MB.",
        "audit_policy": "Deploy WDAC in audit or enforce mode to catch Bring Your Own Vulnerable Driver (BYOVD) rootkits.",
        "mitre_tactics": ["Defense Evasion", "Persistence"],
        "url": "https://learn.microsoft.com/en-us/windows/security/application-security/application-control/windows-defender-application-control/operations/event-tag-explanations"
    },
    "Microsoft-Windows-AppLocker/EXE and DLL.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-AppLocker/EXE and DLL.evtx",
        "title": "AppLocker Executable and DLL Log",
        "channel": "Microsoft-Windows-AppLocker/EXE and DLL",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-AppLocker%4EXE%20and%20DLL.evtx",
        "role": "Records executable and DLL execution blocks and audits enforced by AppLocker application whitelisting.",
        "key_events": ["8002 (Allowed executable)", "8004 (Blocked executable)"],
        "retention": "Default 1MB.",
        "audit_policy": "Enforce AppLocker rule collections to block LOLBIN abuse from temporary and user-writable directories.",
        "mitre_tactics": ["Execution", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/windows/security/application-security/application-control/windows-defender-application-control/applocker/using-event-viewer-with-applocker"
    },
    "Microsoft-Windows-AppLocker/MSI and Script.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-AppLocker/MSI and Script.evtx",
        "title": "AppLocker MSI and Script Log",
        "channel": "Microsoft-Windows-AppLocker/MSI and Script",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-AppLocker%4MSI%20and%20Script.evtx",
        "role": "Captures scripts (.vbs, .js, .ps1, .bat) and installer packages blocked or audited by AppLocker.",
        "key_events": ["8005 (Allowed script)", "8007 (Blocked script)"],
        "retention": "Default 1MB.",
        "audit_policy": "Prevent malicious Windows Script Host (wscript, cscript) execution.",
        "mitre_tactics": ["Execution", "Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/windows/security/application-security/application-control/windows-defender-application-control/applocker/using-event-viewer-with-applocker"
    },
    "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall.evtx",
        "title": "Windows Defender Firewall Log",
        "channel": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-Windows%20Firewall%20With%20Advanced%20Security%4Firewall.evtx",
        "role": "Records firewall rule additions, port openings, and firewall state tampering by malicious software.",
        "key_events": ["2004 (Rule Added)", "2005 (Rule Modified)", "2006 (Rule Deleted)"],
        "retention": "Default 8MB.",
        "audit_policy": "Monitor unexpected inbound port openings created by command-line utilities (netsh advfirewall).",
        "mitre_tactics": ["Defense Evasion"],
        "url": "https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure-logging"
    },

    # --------------------------------------------------------------------------
    # 6. Hardware, USB & Removable Media Forensics
    # --------------------------------------------------------------------------
    "Microsoft-Windows-DriverFrameworks-UserMode/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-DriverFrameworks-UserMode/Operational.evtx",
        "title": "User-Mode Driver Framework (UMDF) Operational Log",
        "channel": "Microsoft-Windows-DriverFrameworks-UserMode/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-DriverFrameworks-UserMode%4Operational.evtx",
        "role": "Premier forensic log for tracking USB device connections, serial numbers, drive letter assignments, and disconnect times.",
        "key_events": ["2003 (USB device connected)", "2100 (Driver host initialized)", "2101 (USB device disconnect)"],
        "retention": "Default disabled. Must be enabled for USB forensics.",
        "audit_policy": "Enable channel via wevtutil or GPO for critical workstations to capture data exfiltration via removable drives.",
        "mitre_tactics": ["Exfiltration", "Initial Access"],
        "url": "https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/user-mode-driver-framework-portal"
    },
    "Microsoft-Windows-Kernel-PnP/Configuration.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-Kernel-PnP/Configuration.evtx",
        "title": "Kernel Plug and Play Configuration Log",
        "channel": "Microsoft-Windows-Kernel-PnP/Configuration",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-Kernel-PnP%4Configuration.evtx",
        "role": "Tracks hardware device installation, vendor IDs, hardware IDs, and driver binding.",
        "key_events": ["400 (Device configured)", "410 (Device started)"],
        "retention": "Default 1MB.",
        "audit_policy": "Inspect device configuration events to prove physical device insertion.",
        "mitre_tactics": ["Initial Access"],
        "url": "https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/pnp-driver-design-guidelines"
    },
    "Microsoft-Windows-VHDMP/Operational.evtx": {
        "type": "evtx",
        "id": "Microsoft-Windows-VHDMP/Operational.evtx",
        "title": "VHD Miniport Driver (VHDMP) Operational Log",
        "channel": "Microsoft-Windows-VHDMP/Operational",
        "path": r"%SystemRoot%\System32\Winevt\Logs\Microsoft-Windows-VHDMP%4Operational.evtx",
        "role": "Records virtual disk (.vhd, .vhdx, .iso) mount and unmount operations commonly used in phishing container execution (Mark-of-the-Web bypass).",
        "key_events": ["1 (VHD mounted)", "2 (VHD unmounted)"],
        "retention": "Default 1MB.",
        "audit_policy": "Alert on ISO/VHD mounts originating from Downloads or temp folders.",
        "mitre_tactics": ["Defense Evasion", "Initial Access"],
        "url": "https://learn.microsoft.com/en-us/windows-server/storage/disk-management/manage-virtual-hard-disks"
    }
}

# Aliases for forensic shorthands
EVTX_SHORTHAND_MAP: Dict[str, str] = {
    "security": "Security.evtx",
    "security.evtx": "Security.evtx",
    "system": "System.evtx",
    "system.evtx": "System.evtx",
    "application": "Application.evtx",
    "application.evtx": "Application.evtx",
    "sysmon": "Sysmon.evtx",
    "sysmon.evtx": "Sysmon.evtx",
    "microsoft-windows-sysmon/operational.evtx": "Sysmon.evtx",
    "microsoft-windows-sysmon/operational": "Sysmon.evtx",
    "powershell": "PowerShell.evtx",
    "powershell.evtx": "PowerShell.evtx",
    "microsoft-windows-powershell/operational.evtx": "PowerShell.evtx",
    "microsoft-windows-powershell/operational": "PowerShell.evtx",
    "taskscheduler": "Microsoft-Windows-TaskScheduler/Operational.evtx",
    "taskscheduler.evtx": "Microsoft-Windows-TaskScheduler/Operational.evtx",
    "task scheduler": "Microsoft-Windows-TaskScheduler/Operational.evtx",
    "wmi": "Microsoft-Windows-WMI-Activity/Operational.evtx",
    "wmi-activity": "Microsoft-Windows-WMI-Activity/Operational.evtx",
    "defender": "Microsoft-Windows-Windows Defender/Operational.evtx",
    "defender.evtx": "Microsoft-Windows-Windows Defender/Operational.evtx",
    "windows defender": "Microsoft-Windows-Windows Defender/Operational.evtx",
    "terminalservices": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "terminalservices.evtx": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "localsessionmanager": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "remoteconnectionmanager": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx",
    "rdp": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "rdpcorets": "Microsoft-Windows-RemoteDesktopServices-RdpCoreTS/Operational.evtx",
    "bits": "Microsoft-Windows-Bits-Client/Operational.evtx",
    "ntlm": "Microsoft-Windows-NTLM/Operational.evtx",
    "lsa": "Microsoft-Windows-LSA/Operational.evtx",
    "lsass": "Microsoft-Windows-LSA/Operational.evtx",
    "sam": "Microsoft-Windows-Directory-Services-SAM/Operational.evtx",
    "codeintegrity": "Microsoft-Windows-CodeIntegrity/Operational.evtx",
    "wdac": "Microsoft-Windows-CodeIntegrity/Operational.evtx",
    "applocker": "Microsoft-Windows-AppLocker/EXE and DLL.evtx",
    "firewall": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall.evtx",
    "usb": "Microsoft-Windows-DriverFrameworks-UserMode/Operational.evtx",
    "driverframeworks": "Microsoft-Windows-DriverFrameworks-UserMode/Operational.evtx",
    "vhd": "Microsoft-Windows-VHDMP/Operational.evtx",
    "vhdmp": "Microsoft-Windows-VHDMP/Operational.evtx",
    "bam": "Microsoft-Windows-BackgroundActivityModerator/Operational.evtx",
    "dns": "DNS Server.evtx",
    "dns server": "DNS Server.evtx",
    "smb": "Microsoft-Windows-SMBClient/Security.evtx",
    "smbclient": "Microsoft-Windows-SMBClient/Security.evtx",
    "smbserver": "Microsoft-Windows-SMBServer/Security.evtx",
    "winrm": "Microsoft-Windows-WinRM/Operational.evtx",
}


def clean_mitre_text(raw_text: str, max_chars: int = 340) -> str:
    if not raw_text:
        return "MITRE ATT&CK enterprise adversary technique."
    # Strip markdown citations e.g. (Citation: ...)
    cleaned = re.sub(r'\(Citation:[^\)]+\)', '', raw_text)
    # Strip markdown hyperlinks e.g. [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # Strip markdown formatting headers or code fences
    cleaned = re.sub(r'[`#*]', '', cleaned)
    # Normalize whitespaces
    cleaned = ' '.join(cleaned.split())
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def sync_mitre_attack(
    source_url: str = DEFAULT_MITRE_STIX_URL,
    output_path: Path = MITRE_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Downloads official MITRE CTI STIX repository and compiles clean lightweight JSON.
    """
    if verbose:
        Diagnostics.info(f"Syncing MITRE ATT&CK database from {source_url}...")

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "md-style-Knowledge-Sync/1.0 (Enterprise ATT&CK Compiler)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
    except Exception as err:
        Diagnostics.warn(f"Failed to fetch MITRE CTI STIX repository: {err}")
        if output_path.exists():
            return len(json.loads(output_path.read_text(encoding="utf-8")))
        return 0

    try:
        stix_data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as err:
        Diagnostics.warn(f"Failed to parse MITRE STIX JSON payload: {err}")
        return 0

    objects = stix_data.get("objects", [])
    techniques_db: Dict[str, Any] = {}

    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked", False) or obj.get("x_mitre_deprecated", False):
            continue

        external_refs = obj.get("external_references", [])
        technique_id = None
        mitre_url = None

        for ref in external_refs:
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id")
                mitre_url = ref.get("url")
                break

        if not technique_id:
            continue

        tactics = []
        for kill_chain in obj.get("kill_chain_phases", []):
            if kill_chain.get("kill_chain_name") == "mitre-attack":
                phase = kill_chain.get("phase_name", "").replace("-", " ").title()
                if phase:
                    tactics.append(phase)

        tactic_str = " / ".join(tactics) if tactics else "Enterprise Tactic"
        name = obj.get("name", "Unknown Technique").strip()
        description = clean_mitre_text(obj.get("description", ""))

        platforms = obj.get("x_mitre_platforms", [])
        is_subtechnique = obj.get("x_mitre_is_subtechnique", False)

        techniques_db[technique_id] = {
            "type": "mitre",
            "id": technique_id,
            "title": name,
            "tactic": tactic_str,
            "summary": description,
            "platforms": platforms,
            "is_subtechnique": is_subtechnique,
            "url": mitre_url or f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/"
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(techniques_db, f, indent=2, ensure_ascii=False)

    # Mirror to user intel cache
    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        mirror_path = INTEL_CACHE_DIR / "mitre-attack.json"
        mirror_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"MITRE database synced: {len(techniques_db)} techniques -> {output_path}")

    return len(techniques_db)


def sync_windows_events_and_evtx(
    output_path: Path = WIN_EVENTS_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Merges authoritative Windows Event IDs and Expanded EVTX channel definitions
    into a single unified data/windows-events.json database.
    """
    if verbose:
        Diagnostics.info(f"Syncing Windows Events & EVTX catalog to {output_path}...")

    existing_db: Dict[str, Any] = {}
    if output_path.exists():
        try:
            existing_db = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            existing_db = {}

    # 1. Inject or update all expanded EVTX channel definitions
    for channel_key, channel_info in EXPANDED_EVTX_CHANNELS.items():
        existing_db[channel_key] = channel_info
        # Also store bare channel name if different (e.g. "Security" for "Security.evtx")
        bare_name = channel_info.get("channel")
        if bare_name and bare_name not in existing_db:
            existing_db[bare_name] = channel_info

    # 2. Inject shorthand aliases
    for alias, canonical in EVTX_SHORTHAND_MAP.items():
        if canonical in existing_db:
            existing_db[alias] = existing_db[canonical]

    # 3. Write unified database
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing_db, f, indent=2, ensure_ascii=False)

    # Mirror to user cache
    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        WIN_EVENTS_CACHE_PATH.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"Windows Events & EVTX catalog synced: {len(existing_db)} entries -> {output_path}")

    return len(existing_db)


# --------------------------------------------------------------------------
# Authoritative 2024 / 2023 CWE Top 25 Most Dangerous Weaknesses Ranking
# (Canonical list from MITRE View-1425)
# --------------------------------------------------------------------------
CWE_TOP_25_RANKS: Dict[str, int] = {
    "787": 1,   # Out-of-bounds Write
    "79": 2,    # Cross-site Scripting
    "89": 3,    # SQL Injection
    "416": 4,   # Use After Free
    "78": 5,    # OS Command Injection
    "20": 6,    # Improper Input Validation
    "125": 7,   # Out-of-bounds Read
    "22": 8,    # Path Traversal
    "352": 9,   # Cross-Site Request Forgery (CSRF)
    "434": 10,  # Unrestricted Upload of File with Dangerous Type
    "862": 11,  # Missing Authorization
    "476": 12,  # NULL Pointer Dereference
    "287": 13,  # Improper Authentication
    "190": 14,  # Integer Overflow
    "502": 15,  # Deserialization of Untrusted Data
    "77": 16,   # Command Injection
    "119": 17,  # Buffer Errors
    "798": 18,  # Hard-coded Credentials
    "918": 19,  # Server-Side Request Forgery (SSRF)
    "306": 20,  # Missing Authentication for Critical Function
    "362": 21,  # Race Condition / Concurrent Execution
    "269": 22,  # Improper Privilege Management
    "94": 23,   # Code Injection
    "863": 24,  # Incorrect Authorization
    "276": 25,  # Incorrect Default Permissions
}

# Curated CAPEC -> MITRE ATT&CK Technique mappings
CAPEC_TO_ATTACK: Dict[str, List[str]] = {
    "100": ["T1190", "T1068", "T1203"], # Overflow Buffers
    "586": ["T1190", "T1059"],          # Object Injection / Deserialization
    "66": ["T1190"],                    # SQL Injection
    "88": ["T1059"],                    # OS Command Injection
    "63": ["T1189"],                    # Cross-Site Scripting
    "115": ["T1078", "T1556"],          # Authentication Bypass
    "37": ["T1552.001"],                # Retrieve Embedded Sensitive Data
    "126": ["T1083", "T1005"],          # Path Traversal
    "153": ["T1059.001"],               # Command Execution
    "163": ["T1203", "T1566.001"],      # Client Exploit
    "242": ["T1055"],                   # Code Injection
    "664": ["T1190"],                   # Server Side Request Forgery
}

# Heuristic CWE -> MITRE ATT&CK technique linkages
CWE_TO_ATTACK_HEURISTICS: Dict[str, List[str]] = {
    "CWE-787": ["T1190", "T1068", "T1203"],
    "CWE-120": ["T1190", "T1068", "T1203"],
    "CWE-125": ["T1005", "T1203"],
    "CWE-416": ["T1068", "T1203"],
    "CWE-119": ["T1190", "T1068", "T1203"],
    "CWE-502": ["T1190", "T1059"],
    "CWE-89":  ["T1190"],
    "CWE-78":  ["T1059", "T1190"],
    "CWE-77":  ["T1059", "T1190"],
    "CWE-94":  ["T1059", "T1190"],
    "CWE-22":  ["T1083", "T1005"],
    "CWE-434": ["T1190", "T1505.003"],
    "CWE-798": ["T1552.001", "T1078"],
    "CWE-287": ["T1078"],
    "CWE-289": ["T1078", "T1556"],
    "CWE-306": ["T1078"],
    "CWE-862": ["T1078", "T1068"],
    "CWE-863": ["T1078", "T1068"],
    "CWE-269": ["T1068", "T1078"],
    "CWE-276": ["T1078"],
    "CWE-918": ["T1190"],
    "CWE-400": ["T1498", "T1499"],
    "CWE-770": ["T1499"],
    "CWE-20":  ["T1190", "T1059"],
    "CWE-200": ["T1005", "T1083"],
    "CWE-917": ["T1190", "T1059"],
}


def _parse_cwe_xml(xml_file) -> Dict[str, Any]:
    """Parses streaming MITRE CWE XML payload into structured records."""
    cwe_db: Dict[str, Any] = {}

    for event, elem in ET.iterparse(xml_file, events=("end",)):
        if elem.tag.endswith("Weakness"):
            wid = elem.attrib.get("ID", "").strip()
            if not wid:
                elem.clear()
                continue

            name = elem.attrib.get("Name", "").strip()
            abstraction = elem.attrib.get("Abstraction", "Base")
            status = elem.attrib.get("Status", "Draft")
            cwe_key = f"CWE-{wid}"

            desc_el = elem.find("{*}Description")
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            ext_el = elem.find("{*}Extended_Description")
            ext_desc = ext_el.text.strip() if ext_el is not None and ext_el.text else ""

            # Common Consequences (Scope & Technical Impact)
            scopes: set = set()
            impacts: set = set()
            for cons in elem.findall(".//{*}Consequence"):
                for sc in cons.findall("{*}Scope"):
                    if sc.text:
                        scopes.add(sc.text.strip())
                for imp in cons.findall("{*}Impact"):
                    if imp.text:
                        impacts.add(imp.text.strip())

            # Potential Mitigations
            mitigations: List[str] = []
            for mit in elem.findall(".//{*}Mitigation"):
                phase_el = mit.find("{*}Phase")
                desc_m_el = mit.find("{*}Description")
                strat_el = mit.find("{*}Strategy")
                p = phase_el.text.strip() if phase_el is not None and phase_el.text else ""
                d = desc_m_el.text.strip() if desc_m_el is not None and desc_m_el.text else ""
                s = strat_el.text.strip() if strat_el is not None and strat_el.text else ""
                if d:
                    entry = f"[{p}] {d}" if p else d
                    if s:
                        entry = f"{s}: {entry}"
                    mitigations.append(entry)

            # Detection Methods
            detection_methods: List[str] = []
            for det in elem.findall(".//{*}Detection_Method"):
                method_el = det.find("{*}Method")
                desc_d_el = det.find("{*}Description")
                m_name = method_el.text.strip() if method_el is not None and method_el.text else ""
                m_desc = desc_d_el.text.strip() if desc_d_el is not None and desc_d_el.text else ""
                if m_name:
                    detection_methods.append(f"{m_name}: {m_desc}" if m_desc else m_name)

            # Applicable Platforms
            platforms: List[str] = []
            for lang in elem.findall(".//{*}Language"):
                l_name = lang.attrib.get("Name")
                if l_name and l_name not in platforms and "Not Language" not in l_name:
                    platforms.append(l_name)

            # Related Attack Patterns (CAPEC)
            capecs: List[str] = []
            for rap in elem.findall(".//{*}Related_Attack_Pattern"):
                cid = rap.attrib.get("CAPEC_ID")
                if cid and cid not in capecs:
                    capecs.append(cid)

            # Correlate with MITRE ATT&CK techniques
            mitre_techniques: List[str] = []
            for cid in capecs:
                for tid in CAPEC_TO_ATTACK.get(cid, []):
                    if tid not in mitre_techniques:
                        mitre_techniques.append(tid)

            # Add heuristic techniques if not already present
            for tid in CWE_TO_ATTACK_HEURISTICS.get(cwe_key, []):
                if tid not in mitre_techniques:
                    mitre_techniques.append(tid)

            # Related Weaknesses (Parent/Child)
            parents: List[str] = []
            for rw in elem.findall(".//{*}Related_Weakness"):
                nature = rw.attrib.get("Nature")
                rw_id = rw.attrib.get("CWE_ID")
                if nature == "ChildOf" and rw_id:
                    parents.append(f"CWE-{rw_id}")

            top25_rank = CWE_TOP_25_RANKS.get(wid)

            cwe_db[cwe_key] = {
                "id": cwe_key,
                "title": name,
                "abstraction": abstraction,
                "status": status,
                "summary": desc,
                "extended_description": ext_desc,
                "scopes": sorted(list(scopes)),
                "impacts": sorted(list(impacts)),
                "mitigations": mitigations[:4],
                "detection_methods": detection_methods[:3],
                "platforms": platforms[:6],
                "capecs": capecs,
                "mitre_techniques": mitre_techniques,
                "parent_cwes": parents,
                "top25_rank": top25_rank,
                "url": f"https://cwe.mitre.org/data/definitions/{wid}.html"
            }
            elem.clear()

    return cwe_db


def sync_cwe_catalog(
    source_url: str = DEFAULT_MITRE_CWE_URL,
    output_path: Path = CWE_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Downloads official canonical MITRE CWE XML release, parses weakness records,
    correlates with MITRE ATT&CK techniques, and compiles data/cwe.json.
    """
    if verbose:
        Diagnostics.info(f"Syncing MITRE CWE catalog from {source_url}...")

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "md-style-Knowledge-Sync/1.0 (CWE Compiler)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
    except Exception as err:
        Diagnostics.warn(f"Failed to fetch MITRE CWE archive: {err}")
        if output_path.exists():
            try:
                return len(json.loads(output_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return 0

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            xml_names = [n for n in z.namelist() if n.endswith(".xml")]
            if not xml_names:
                Diagnostics.warn("No XML found in MITRE CWE zip archive.")
                return 0
            with z.open(xml_names[0]) as xml_file:
                cwe_db = _parse_cwe_xml(xml_file)
    except Exception as err:
        Diagnostics.warn(f"Failed to parse MITRE CWE XML payload: {err}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cwe_db, f, indent=2, ensure_ascii=False)

    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        mirror_path = INTEL_CACHE_DIR / "cwe.json"
        mirror_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"CWE catalog synced: {len(cwe_db)} weaknesses -> {output_path}")

    return len(cwe_db)


def sync_all_catalogs(verbose: bool = True) -> Dict[str, int]:
    """Runs all knowledge base synchronizations."""
    mitre_count = sync_mitre_attack(verbose=verbose)
    winevt_count = sync_windows_events_and_evtx(verbose=verbose)
    cwe_count = sync_cwe_catalog(verbose=verbose)
    return {
        "mitre_techniques": mitre_count,
        "windows_events_and_channels": winevt_count,
        "cwe_weaknesses": cwe_count,
    }


if __name__ == "__main__":
    results = sync_all_catalogs(verbose=True)
    print("\n[SYNC COMPLETE]", results)

