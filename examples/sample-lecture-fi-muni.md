---
title: "Architektura moderních operačních systémů"
subtitle: "Virtuální paměť, víceúrovňové stránkování a překlad adres v x86-64"
course: "PV157"
lecture: "04"
instructor: "doc. RNDr. Jan Novák, Ph.D."
term: "Podzim 2026"
institution: "Fakulta informatiky, Masarykova univerzita"
date: "2026-10-27"
style: "academic/lecture"
abstract: |
  Tento výukový text pokrývá principy virtuální paměti a hardwarové podpory překladu adres v moderních 64bitových procesorech architektury x86-64. Detailně analyzujeme hierarchický překlad prostřednictvím čtyřúrovňových tabulek (PML4, PDPT, PD, PT), mechanismus Translation Lookaside Buffer (TLB), podporu pro Huge Pages a systémovou obsluhu výjimky Page Fault v jádře OS.
---

# Úvod do virtuální paměti

Správa paměti představuje jeden z klíčových pilířů moderních víceúlohových operačních systémů. Hlavním cílem mechanismu virtuální paměti je poskytnout každému běžícímu procesu iluzi souvislého, izolovaného a privátního adresního prostoru, aniž by proces musel brát ohled na skutečné fyzické umístění dat v operační paměti RAM.

Díky oddělení virtuálního a fyzického adresního prostoru dosahuje operační systém tří zásadních vlastností:
1. **Izolace a bezpečnost**: Proces nemůže přistupovat do paměti jiného procesu ani přímo modifikovat datové struktury jádra bez patřičných oprávnění.
2. **Efektivní využití RAM**: Fyzické rámce paměti jsou alokovány až ve chvíli skutečného přístupu (*demand paging*).
3. **Sdílení paměti**: Sdílené knihovny a mechanismus *Copy-on-Write* (CoW) šetří desítky procent fyzické paměti napříč procesy.

> [!NOTE] Klíčový pojem: MMU a řídicí registr CR3
> Překlad virtuální adresy na fyzickou adresu neprovádí operační systém softwarově při každé instrukci, ale specializovaná hardwarová jednotka procesoru zvaná **Memory Management Unit (MMU)**. Jádro operačního systému pouze spravuje tabulky stránek v paměti RAM a při přepnutí kontextu procesu zapíše fyzickou adresu kořene tabulky do kontrolního registru procesoru (v x86-64 jde o registr `CR3`).

---

# Hierarchické stránkování v x86-64

Původní architektura x86-64 využívá 48bitový virtuální adresní prostor (s kanonickým rozšířením znaménka na 64 bitů) a standardní velikost základní stránky **4 KiB** ($2^{12}$ bajtů). Aby nebylo nutné alokovat jedinou gigantickou tabulku stránek v kuse, je překlad strukturován do čtyř úrovní:

| Úroveň | Zkratka | Celý název | Index v adrese | Velikost mapovaného bloku |
| :--- | :--- | :--- | :--- | :--- |
| **Úroveň 4** | **PML4** | Page Map Level 4 | Bity 47–39 (9 bitů) | 512 GiB |
| **Úroveň 3** | **PDPT** | Page Directory Pointer Table | Bity 38–30 (9 bitů) | 1 GiB |
| **Úroveň 2** | **PD** | Page Directory | Bity 29–21 (9 bitů) | 2 MiB |
| **Úroveň 1** | **PT** | Page Table | Bity 20–12 (9 bitů) | 4 KiB |
| **Offset** | — | Vnitrostránkový posun | Bity 11–0 (12 bitů) | 1 B |

Každá tabulka obsahuje přesně $2^9 = 512$ položek (PTE / PDE), přičemž každá položka má velikost 8 bajtů (64 bitů). Celá jedna tabulka libovolné úrovně tak přesně odpovídá jedné 4KiB stránce ($512 \times 8 = 4096$ bajtů), což je architektonicky velmi elegantní.

```c
// Ukázka C kódu pro extrakci indexů z 64bitové virtuální adresy
#include <stdint.h>
#include <stdio.h>

#define PAGE_OFFSET_MASK 0xFFFULL
#define PAGE_INDEX_MASK  0x1FFULL

typedef struct {
    uint16_t pml4_idx;
    uint16_t pdpt_idx;
    uint16_t pd_idx;
    uint16_t pt_idx;
    uint16_t offset;
} page_indices_t;

page_indices_t decode_virtual_address(uint64_t vaddr) {
    page_indices_t idx;
    idx.offset   = (uint16_t)(vaddr & PAGE_OFFSET_MASK);
    idx.pt_idx   = (uint16_t)((vaddr >> 12) & PAGE_INDEX_MASK);
    idx.pd_idx   = (uint16_t)((vaddr >> 21) & PAGE_INDEX_MASK);
    idx.pd_idx   = (uint16_t)((vaddr >> 30) & PAGE_INDEX_MASK);
    idx.pml4_idx = (uint16_t)((vaddr >> 39) & PAGE_INDEX_MASK);
    return idx;
}
```

---

# Optimalizace: Translation Lookaside Buffer (TLB)

Pokud by procesor musel při každém přístupu do paměti provést 4 dodatečná čtení z RAM pro průchod tabulkami, výkon celého systému by dramaticky poklesl. K eliminaci této režie slouží **TLB (Translation Lookaside Buffer)** — extrémně rychlá asociativní mezipaměť přímo v procesoru, která uchovává nedávno přeložené dvojice `virtuální stránka -> fyzický rámec`.

> [!TIP] Huge Pages a optimalizace TLB pro databáze
> Při použití standardních 4KiB stránek pokrývá 512položková TLB paměť pouze $512 \times 4\text{ KiB} = 2\text{ MiB}$ adresního prostoru. Při práci s velkými paměťovými bloky (např. databázové buffery v PostgreSQL nebo Java heap) je výhodné aktivovat **Huge Pages** (2 MiB nebo 1 GB). Jedna položka TLB pak pokryje 500× více dat, což radikálně snižuje počet *TLB miss* výpadků.

> [!WARNING] Úskalí invalidace TLB při změně mapování
> Změní-li jádro operačního systému záznam v tabulce stránek (například při uvolnění paměti `munmap`), hardwarové TLB procesorů se neaktualizují automaticky! Jádro musí explicitně provést invalidaci záznamu pomocí instrukce `INVLPG`, případně rozeslat meziprocesorové přerušení (*TLB shootdown*) všem ostatním jádrům na multiprocesorovém systému.

---

# Cvičení k procvičení

::: exercise
**Úloha 1: Výpočet spotřeby paměti pro tabulky**  
Předpokládejte 64bitový proces, který má v paměti alokovány pouze dvě 4KiB stránky na virtuálních adresách `0x0000_0000_0040_0000` (kódový segment) a `0x0000_7FFF_FFFF_0000` (zásobník). 
1. Kolik stránek pro tabulky překladu (PML4, PDPT, PD, PT) musí jádro OS celkem alokovat?
2. Jak by se situace změnila, kdyby systém nepodporoval víceúrovňové stránkování, ale vyžadoval lineární pole všech mapování?
:::

---

# Shrnutí přednášky

* Virtuální paměť poskytuje izolaci procesů, ochranu paměti a flexibilní správu fyzické RAM.
* Architektura x86-64 používá 4úrovňový překlad adres (PML4, PDPT, PD, PT) se standardní velikostí stránky 4 KiB.
* Překlad je hardwarově akcelerován pomocí MMU a asociativní cache TLB.
* Při přepnutí procesu zapisuje jádro fyzickou adresu kořene PML4 do registru `CR3`.
