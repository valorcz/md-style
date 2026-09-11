-- ==============================================================================
-- table-nowrap.lua
-- Pandoc Lua filter for Digital Forensics & Incident Response Reports
--
-- Automatically identifies timestamp columns and cells in tables, preventing
-- timestamps from wrapping across multiple lines in HTML and PDF/print outputs.
--
-- Supports:
-- 1. Multilingual header keywords (English, Czech/Slovak, German, French, etc.)
-- 2. Timezone & standard identifiers (UTC, GMT, ISO)
-- 3. Content-driven pattern matching (ISO-8601, European dot notation, Unix time)
-- ==============================================================================

-- Check if cell string matches common timestamp / date formats
local function is_timestamp_str(s)
  if not s or #s == 0 then return false end
  -- Trim leading and trailing whitespace
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

-- Helper to safely add a class to a cell's attributes
local function add_nowrap_class(cell)
  if not cell.classes:includes("nowrap") then
    cell.classes:insert("nowrap")
  end
end

-- Pandoc Table filter hook
function Table(tbl)
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
          add_nowrap_class(cell)
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

          -- If header explicitly marked this column, or the cell itself is a timestamp
          if header_time_cols[col_idx] or is_ts then
            add_nowrap_class(cell)
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
            add_nowrap_class(cell)
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
              add_nowrap_class(cell)
            end
          end
        end
      end
    end
  end

  return tbl
end
