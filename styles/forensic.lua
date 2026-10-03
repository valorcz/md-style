-- ==============================================================================
-- forensic.lua
-- Pandoc Lua filter for Digital Forensics & Incident Response Reports
--
-- Features:
-- 1. Automatic nowrap on timestamp table columns and cells
-- 2. Normalization of Pandoc crushed column widths
-- 3. Automatic timeline table detection (.table-timeline)
-- 4. Automatic Executive Summary / Manažerské shrnutí KPI Grid transformation
-- 5. Automatic classification tagging for MITRE ATT&CK (.mitre-pill),
--    cryptographic hashes (.hash), and Indicators of Compromise (.ioc)
-- ==============================================================================

-- Check if cell string matches common timestamp / date formats
local function is_timestamp_str(s)
  if not s or #s == 0 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")

  -- 1. ISO 8601 Datetime or Date:
  --    2026-09-11 02:14:22, 2026-09-11T02:14:22, 2026-09-11 02:14:22.123, 2026-09-11
  if s:match("^%d%d%d%d%-%d%d%-%d%d") then
    return true
  end

  -- 2. European / Localized Datetime or Date:
  --    11.09.2026 02:14:22, 11/09/2026 02:14:22, 11.09.2026
  if s:match("^%d%d?%.%d%d?%.%d%d%d%d") or s:match("^%d%d?/%d%d?/%d%d%d%d") then
    return true
  end

  -- 3. Standalone Time:
  --    02:14:22, 02:14:22.541, 02:14
  if s:match("^%d%d?:%d%d:%d%d") or s:match("^%d%d?:%d%d") then
    return true
  end

  return false
end

-- Check if column header contains timestamp keywords in various languages
local function is_timestamp_header(s)
  if not s or #s == 0 then return false end
  local lower = pandoc.text.lower(s)

  local keywords = {
    -- English
    "time", "timestamp", "date", "datetime", "acquisition",
    -- Czech / Slovak (including diacritic and non-diacritic variants)
    "čas", "cas", "značka", "znacka", "datum", "dátum", "akvizic",
    -- German
    "zeit", "zeitstempel", "erfassungszeit",
    -- French / Spanish / Italian
    "horodatage", "date/heure", "fecha", "hora", "orario",
    -- Universal timezone & standard tokens
    "utc", "gmt", "iso8601", "epoch"
  }

  for _, kw in ipairs(keywords) do
    if lower:find(kw, 1, true) then
      return true
    end
  end

  return false
end

-- Check if header indicates a timeline table
local function is_timeline_title(s)
  if not s or #s == 0 then return false end
  local lower = pandoc.text.lower(s)
  local keywords = {
    "timeline", "časová osa", "casova osa", "chronolog", "průběh incidentu", "chronology"
  }
  for _, kw in ipairs(keywords) do
    if lower:find(kw, 1, true) then
      return true
    end
  end
  return false
end

-- Helper to safely add a class to an element's classes list
local function ensure_class(el, class_name)
  if not el.classes:includes(class_name) then
    el.classes:insert(class_name)
  end
end

-- Check if a string looks like a cryptographic hash or long hex token (e.g. SHA-256, SHA-1, MD5)
local function is_hash_or_token_str(s)
  if not s or #s < 24 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  -- Hexadecimal hash (e.g. MD5=32, SHA-1=40, SHA-256=64, SHA-512=128)
  if s:match("^%x+$") and #s >= 24 then
    return true
  end
  -- Prefixed hex hash (e.g. 0x...)
  if s:match("^0[xX]%x+$") and #s >= 26 then
    return true
  end
  -- Long unbroken token/identifier (>= 32 chars without whitespace)
  if #s >= 32 and not s:find("%s") then
    return true
  end
  return false
end

-- Check if string is an IPv4 address (standalone or with port)
local function is_ipv4_str(s)
  if not s or #s == 0 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  if s:match("^%d%d?%d?%.%d%d?%d?%.%d%d?%d?%.%d%d?%d?$") or s:match("^%d%d?%d?%.%d%d?%d?%.%d%d?%d?%.%d%d?%d?:%d+$") then
    return true
  end
  return false
end

-- Check if string is a MITRE ATT&CK technique ID (e.g. T1059, T1059.001)
local function is_mitre_id(s)
  if not s or #s == 0 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return (s:match("^T%d%d%d%d$") or s:match("^T%d%d%d%d%.%d%d%d$")) ~= nil
end

-- Check if string is a CVE identifier (e.g. CVE-2024-12345)
local function is_cve_id(s)
  if not s or #s == 0 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s:match("^CVE%-%d%d%d%d%-%d+$") ~= nil
end

-- Process Code elements: hashes, MITRE pills, IoCs
function Code(el)
  local txt = el.text
  if is_mitre_id(txt) then
    ensure_class(el, "mitre-pill")
    ensure_class(el, "ioc")
  elseif is_hash_or_token_str(txt) then
    ensure_class(el, "hash")
    ensure_class(el, "ioc")
  elseif is_ipv4_str(txt) or is_cve_id(txt) then
    ensure_class(el, "ioc")
  end
  return el
end

-- Parse a BulletList item into a KPI card structure
local function parse_kpi_item(blocks)
  if not blocks or #blocks == 0 then return nil end
  local first_block = blocks[1]
  if first_block.t ~= "Plain" and first_block.t ~= "Para" then return nil end
  local inlines = first_block.content
  if not inlines or #inlines == 0 then return nil end

  local first_inline = inlines[1]
  if first_inline.t ~= "Strong" then return nil end

  -- Extract label inlines, stripping trailing colon if present
  local label_inlines = {}
  for i, inl in ipairs(first_inline.content) do
    if i == #first_inline.content and inl.t == "Str" and inl.text:sub(-1) == ":" then
      local trimmed = inl.text:sub(1, -2)
      if #trimmed > 0 then
        table.insert(label_inlines, pandoc.Str(trimmed))
      end
    else
      table.insert(label_inlines, inl)
    end
  end

  -- Value inlines: everything after the Strong
  local value_inlines = {}
  local start_idx = 2

  -- Check if next token is a colon or starts with a colon
  if #inlines >= 2 and inlines[2].t == "Str" and inlines[2].text == ":" then
    start_idx = 3
  elseif #inlines >= 2 and inlines[2].t == "Str" and inlines[2].text:sub(1, 1) == ":" then
    local rest = inlines[2].text:sub(2)
    if #rest > 0 then
      inlines[2] = pandoc.Str(rest)
      start_idx = 2
    else
      start_idx = 3
    end
  end

  -- Skip leading space in value
  while start_idx <= #inlines and inlines[start_idx].t == "Space" do
    start_idx = start_idx + 1
  end

  for idx = start_idx, #inlines do
    table.insert(value_inlines, inlines[idx])
  end

  -- Collect any extra blocks in this item (e.g. secondary paragraphs)
  local extra_blocks = {}
  for b = 2, #blocks do
    table.insert(extra_blocks, blocks[b])
  end

  return {
    label = label_inlines,
    value = value_inlines,
    extra = extra_blocks
  }
end

-- Convert a BulletList to a KPI Grid Div
local function bullet_list_to_kpi_grid(list_el)
  if not list_el or list_el.t ~= "BulletList" then return nil end
  local kpi_cards = {}

  for _, item_blocks in ipairs(list_el.content) do
    local kpi = parse_kpi_item(item_blocks)
    if kpi then
      local card_content = {
        pandoc.Div({ pandoc.Plain(kpi.label) }, pandoc.Attr("", {"kpi-label"})),
        pandoc.Div({ pandoc.Plain(kpi.value) }, pandoc.Attr("", {"kpi-value"}))
      }
      local is_wide = false
      if #kpi.extra > 0 then
        for _, eb in ipairs(kpi.extra) do
          table.insert(card_content, eb)
          if eb.t == "BulletList" or eb.t == "OrderedList" then
            is_wide = true
          end
        end
      end
      local card_classes = {"kpi-card"}
      if is_wide then
        table.insert(card_classes, "kpi-card-full")
      end
      table.insert(kpi_cards, pandoc.Div(card_content, pandoc.Attr("", card_classes)))
    else
      -- If item doesn't fit standard KPI pattern, wrap it as a full card
      table.insert(kpi_cards, pandoc.Div(item_blocks, pandoc.Attr("", {"kpi-card", "kpi-card-full"})))
    end
  end

  if #kpi_cards == 0 then return nil end
  return pandoc.Div(kpi_cards, pandoc.Attr("", {"kpi-grid"}))
end

-- Pandoc Table processing
local function process_table(tbl, preceding_header_text)
  local header_time_cols = {}
  local col_total_cells = {}
  local col_timestamp_cells = {}

  -- 1. Scan Table Header (tbl.head)
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      for col_idx, cell in ipairs(row.cells) do
        local header_text = pandoc.utils.stringify(cell)
        if is_timestamp_header(header_text) then
          header_time_cols[col_idx] = true
          ensure_class(cell, "nowrap")
        end
      end
    end
  end

  -- 2. Scan Table Bodies (tbl.bodies)
  if tbl.bodies then
    for _, body in ipairs(tbl.bodies) do
      local rows = body.body or body.rows or {}
      for _, row in ipairs(rows) do
        for col_idx, cell in ipairs(row.cells) do
          local cell_text = pandoc.utils.stringify(cell)
          col_total_cells[col_idx] = (col_total_cells[col_idx] or 0) + 1

          local is_ts = is_timestamp_str(cell_text)
          if is_ts then
            col_timestamp_cells[col_idx] = (col_timestamp_cells[col_idx] or 0) + 1
          end

          if header_time_cols[col_idx] or is_ts then
            ensure_class(cell, "nowrap")
          end
        end
      end
    end
  end

  -- 3. Infer timestamp columns where majority of cells (>50% and >1) are timestamps
  local inferred_cols = {}
  for col_idx, ts_count in pairs(col_timestamp_cells) do
    local total = col_total_cells[col_idx] or 0
    if not header_time_cols[col_idx] and total > 1 and (ts_count / total) >= 0.5 then
      inferred_cols[col_idx] = true
    end
  end

  -- 4. Apply nowrap to all cells and header in inferred columns
  if next(inferred_cols) then
    if tbl.head and tbl.head.rows then
      for _, row in ipairs(tbl.head.rows) do
        for col_idx, cell in ipairs(row.cells) do
          if inferred_cols[col_idx] then
            ensure_class(cell, "nowrap")
          end
        end
      end
    end

    if tbl.bodies then
      for _, body in ipairs(tbl.bodies) do
        local rows = body.body or body.rows or {}
        for _, row in ipairs(rows) do
          for col_idx, cell in ipairs(row.cells) do
            if inferred_cols[col_idx] then
              ensure_class(cell, "nowrap")
            end
          end
        end
      end
    end
  end

  -- 5. Check if table is a timeline table (strict: requires timeline keyword in preceding heading)
  local is_timeline = false
  if preceding_header_text and is_timeline_title(preceding_header_text) then
    is_timeline = true
  end

  if is_timeline then
    ensure_class(tbl, "table-timeline")
  end

  -- 6. Normalize crushed column widths
  if tbl.colspecs then
    local has_crushed_col = false
    for _, colspec in ipairs(tbl.colspecs) do
      local w = colspec[2]
      if type(w) == "number" and w > 0 and w < 0.12 then
        has_crushed_col = true
        break
      end
    end
    if has_crushed_col then
      for i, colspec in ipairs(tbl.colspecs) do
        tbl.colspecs[i] = {colspec[1], pandoc.ColWidthDefault}
      end
    end
  end

  return tbl
end

-- Document-level transformation to handle Timeline Tables and explicit Opt-In KPI Grids
function Pandoc(doc)
  local new_blocks = {}
  local recent_header_text = ""

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" then
      recent_header_text = pandoc.utils.stringify(block)
      table.insert(new_blocks, block)

    elseif block.t == "Div" and (block.classes:includes("kpi-grid") or block.classes:includes("kpis")) then
      -- Explicit Div with kpi-grid class: transform internal bullet lists to cards
      local processed_content = {}
      for _, sub_b in ipairs(block.content) do
        if sub_b.t == "BulletList" then
          local grid = bullet_list_to_kpi_grid(sub_b)
          if grid then
            for _, card in ipairs(grid.content) do
              table.insert(processed_content, card)
            end
          else
            table.insert(processed_content, sub_b)
          end
        else
          table.insert(processed_content, sub_b)
        end
      end
      block.content = processed_content
      table.insert(new_blocks, block)

    elseif block.t == "Table" then
      local processed_tbl = process_table(block, recent_header_text)
      table.insert(new_blocks, processed_tbl)

    else
      table.insert(new_blocks, block)
    end
  end

  doc.blocks = new_blocks
  return doc
end
