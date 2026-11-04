---
title: "Interactive Operating Systems: Hardware Memory Isolation"
subtitle: "MMU Page Tables, DRAM Frame Allocation, and Page Fault Diagnostics"
style: "academic/modern"
author: "Systems Architecture Research Lab"
date: "2026-10-31"
abstract: >
  This interactive technical document examines hardware-enforced virtual memory isolation
  using an embedded Svelte component. Presenters and readers can dynamically pivot
  between process address spaces and inspect page faults in real time.
---

# 1. Executive Overview

Modern virtual memory architectures rely on hardware **Memory Management Units (MMUs)** to provide strict isolation between unprivileged userland processes. Every process executes under the illusion of possessing an exclusive, contiguous 64-bit linear address space starting at virtual address `0x00000000`.

# 2. Virtual Memory Translation Architecture

The diagram below is an interactive Svelte 5 component compiled directly into this standalone HTML document. Readers can click the filter buttons or press hotkeys `1` through `4` to inspect the translation pipelines.

```component LogicalPhysicalMap title="Interactive 3-Column Systems Architecture Map" #mmu-interactive-map
initialFilter: "procA"
```

## Key Observations

1. **Address Space Multiplexing**: Both **Process A (Browser)** and **Process B (Editor)** map their respective code segments (`.text`) to identical virtual addresses `0x00400000`, yet their CR3 page tables route requests to completely distinct physical DRAM frames (`PFN 3` vs `PFN 1`).
2. **Page Fault Handling (#PF)**: When an application touches an evicted page marked with `V=0`, the CPU triggers an architectural `#PF` interrupt, allowing the OS kernel to page in data from swap or disk.
