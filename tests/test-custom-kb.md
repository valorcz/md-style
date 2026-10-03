---
title: "Test Case Custom Knowledge Base"
lang: cs
classification: "DŮVĚRNÉ // FORENZNÍ ŠETŘENÍ"
knowledge: "./fixtures/knowledge"
---

# Analýza incidentu a kompromitace domény

Během forenzní analýzy bylo zjištěno, že útočník cílil na doménový řadič `DC01.corp.internal` a pokusil se zneužít servisní účet `svc_backup`.

## Zjištěná aktivita útočníka

1. V prose textu byl detekován účet svc_backup a server DC01 bez zpětných uvozovek.
2. V kódových uvozovkách byl zaznamenán přístup k `svc_backup` a související `Event ID 4769` z interní IP adresy `192.168.45.1`.
3. Cílový server byl `DC01.corp.internal` a útok odpovídal technice `T1558.003`.
