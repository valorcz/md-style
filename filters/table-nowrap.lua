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

-- Check if cell string matches a timestamp range (e.g. 2026-01-01T11:12:13-14:15:16, 2026-09-11 02:10 - 02:50)
local function is_timestamp_range_str(s)
  if not s or #s == 0 or #s > 60 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  -- ISO datetime range: 2026-01-01... - 2026-01-02... or 2026-01-01T11:12:13-14:15:16
  if s:match("^%d%d%d%d%-%d%d%-%d%d.*[%-%–%—].*%d") then
    return true
  end
  -- European date range: 01.01.2026 - 02.01.2026
  if s:match("^%d%d?%.%d%d?%.%d%d%d%d.*[%-%–%—].*%d") then
    return true
  end
  -- Time range: 11:12:13-14:15:16 or 11:12 - 14:15
  if s:match("^%d%d?:%d%d.*[%-%–%—].*%d%d?:%d%d") then
    return true
  end
  return false
end

-- Make timestamp range cell breakable between dates/times while keeping units intact
local function make_range_breakable(cell)
  if not cell.classes:includes("timestamp-range") then
    cell.classes:insert("timestamp-range")
  end
  for idx, c in ipairs(cell.classes) do
    if c == "nowrap" then
      table.remove(cell.classes, idx)
      break
    end
  end

  local function add_wbr_to_str(text)
    local pre, post = text:match("^(.-%d%d?:%d%d:%d%d)%-(%d%d?:%d%d.*)$")
    if pre and post then
      return { pandoc.Str(pre .. "-"), pandoc.RawInline("html", "<wbr>"), pandoc.Str(post) }
    end
    pre, post = text:match("^(.-%d%d?:%d%d)%-(%d%d?:%d%d.*)$")
    if pre and post then
      return { pandoc.Str(pre .. "-"), pandoc.RawInline("html", "<wbr>"), pandoc.Str(post) }
    end
    pre, post = text:match("^(.-%d%d%d%d%-%d%d%-%d%d)%-(%d%d%d%d%-%d%d%-%d%d.*)$")
    if pre and post then
      return { pandoc.Str(pre .. "-"), pandoc.RawInline("html", "<wbr>"), pandoc.Str(post) }
    end
    return nil
  end

  local contents = cell.content or cell.contents or {}
  local div = pandoc.Div(contents)
  local walked = pandoc.walk_block(div, {
    Str = function(el)
      local rep = add_wbr_to_str(el.text)
      if rep then return rep end
      return el
    end,
    Code = function(el)
      local pre, post = el.text:match("^(.-%d%d?:%d%d:%d%d)%-(%d%d?:%d%d.*)$")
      if not pre then
        pre, post = el.text:match("^(.-%d%d?:%d%d)%-(%d%d?:%d%d.*)$")
      end
      if not pre then
        pre, post = el.text:match("^(.-%d%d%d%d%-%d%d%-%d%d)%-(%d%d%d%d%-%d%d%-%d%d.*)$")
      end
      if pre and post then
        return {
          pandoc.Code(pre .. "-"),
          pandoc.RawInline("html", "<wbr>"),
          pandoc.Code(post)
        }
      end
      return el
    end
  })
  if cell.content then
    cell.content = walked.content
  else
    cell.contents = walked.content
  end
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

          local is_range = is_timestamp_range_str(cell_text)
          local is_ts = is_timestamp_str(cell_text)

          if is_range then
            make_range_breakable(cell)
            col_timestamp_cells[col_idx] = (col_timestamp_cells[col_idx] or 0) + 1
          elseif is_ts then
            col_timestamp_cells[col_idx] = (col_timestamp_cells[col_idx] or 0) + 1
            if header_time_cols[col_idx] or is_ts then
              add_nowrap_class(cell)
            end
          elseif header_time_cols[col_idx] then
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

  -- 4. Apply nowrap to all cells and header in inferred columns (except ranges)
  if next(inferred_cols) then
    if tbl.head and tbl.head.rows then
      for _, row in ipairs(tbl.head.rows) do
        for col_idx, cell in ipairs(row.cells) do
          if inferred_cols[col_idx] and not cell.classes:includes("timestamp-range") then
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
            if inferred_cols[col_idx] and not cell.classes:includes("timestamp-range") then
              add_nowrap_class(cell)
            end
          end
        end
      end
    end
  end

  -- 5. Normalize column widths so Pandoc outputs fluid, content-driven columns
  if tbl.colspecs then
    for i, colspec in ipairs(tbl.colspecs) do
      tbl.colspecs[i] = {colspec[1], pandoc.ColWidthDefault}
    end
  end

  return pandoc.Div({ tbl }, pandoc.Attr("", { "table-wrapper" }))
end

-- Check if a string looks like a cryptographic hash or long hex token (e.g. SHA-256, SHA-1, MD5)
local function is_hash_or_token_str(s)
  if not s or #s < 24 then return false end
  -- Trim whitespace
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

-- Pandoc Code element hook: automatically add 'hash' class to long hashes/tokens
function Code(el)
  if is_hash_or_token_str(el.text) then
    if not el.classes:includes("hash") then
      el.classes:insert("hash")
    end
  end
  return el
end

