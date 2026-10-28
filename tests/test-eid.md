---
title: "Windows Event ID Consistency Test"
lang: cs
classification: "DŮVĚRNÉ"
---

# Telemetry Detection

In the security logs, we detected `EID 5000, 5001 and 600` during the attack.

Also in plain text prose: We observed EID 5000, 5001 and 600 across multiple endpoints.

And with formal notation: We recorded Event ID 4624, 4625 and 4672 during logon analysis.

User test case:
Útočník vypíná ochranu v reálném čase Microsoft Defenderu (Event ID 5001) – test obrany.

RDP test cases:
Při prověřování souboru `TerminalServices.evtx` a `Defender.evtx` byly detekovány relace (EID 21 a 23).
Také ověřeno přes (Event ID 21/23).

