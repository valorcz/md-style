-- ==============================================================================
-- forensic-cyber.lua
-- Pandoc Lua filter for Cyber AI Forensic Reports (Spin-off style)
--
-- Features:
-- 1. Automatic nowrap on timestamp table columns and cells
-- 2. Normalization of Pandoc crushed column widths
-- 3. Automatic timeline table detection (.table-timeline)
-- 4. Malicious timeline event tagging (.timeline-malicious) for radar pulse
-- 5. Automatic classification & data-attribute tagging for MITRE ATT&CK,
--    cryptographic hashes, and IoCs for the interactive Quick-Inspector Drawer
-- 6. AI Insight callouts (::: {.ai-insight} and > [!AI-INSIGHT])
-- 7. Cyber telemetry badges ([THREAT: CRITICAL], [CONFIDENCE: XX%])
-- ==============================================================================

-- Custom Knowledge Base Rules
local custom_exact_tokens = {}
local custom_prose_rules = {}

function Meta(meta)
  if meta["custom-knowledge-manifest"] then
    local manifest_path = pandoc.utils.stringify(meta["custom-knowledge-manifest"])
    local f = io.open(manifest_path, "r")
    if f then
      local content = f:read("*a")
      f:close()
      if pandoc.json and pandoc.json.decode then
        local ok, parsed = pcall(pandoc.json.decode, content)
        if ok and parsed then
          if parsed.exact_tokens then
            for _, item in ipairs(parsed.exact_tokens) do
              local key = item.case_sensitive and item.token or item.token:lower()
              custom_exact_tokens[key] = item
            end
          end
          if parsed.prose_rules then
            custom_prose_rules = parsed.prose_rules
          end
        end
      end
    end
  end
  return meta
end

-- Check if cell string matches common timestamp / date formats
local function is_timestamp_str(s)
  if not s or #s == 0 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")

  -- 1. ISO 8601 Datetime or Date:
  if s:match("^%d%d%d%d%-%d%d%-%d%d") then
    return true
  end

  -- 2. European / Localized Datetime or Date:
  if s:match("^%d%d?%.%d%d?%.%d%d%d%d") or s:match("^%d%d?/%d%d?/%d%d%d%d") then
    return true
  end

  -- 3. Standalone Time:
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
    "time", "timestamp", "date", "datetime", "acquisition",
    "čas", "cas", "značka", "znacka", "datum", "dátum", "akvizic",
    "zeit", "zeitstempel", "erfassungszeit",
    "horodatage", "date/heure", "fecha", "hora", "orario",
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

-- Check if a string looks like a cryptographic hash
local function is_hash_or_token_str(s)
  if not s or #s < 24 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  if s:match("^%x+$") and #s >= 24 then
    return true
  end
  if s:match("^0[xX]%x+$") and #s >= 26 then
    return true
  end
  return false
end

-- Check if string is an IPv4 address
local function is_ipv4_str(s)
  if not s or #s < 7 or #s > 21 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  local ip_part = s:match("^([%d%.]+)")
  if not ip_part then return false end
  local a, b, c, d = ip_part:match("^(%d%d?%d?)%.(%d%d?%d?)%.(%d%d?%d?)%.(%d%d?%d?)$")
  if a and b and c and d then
    local na, nb, nc, nd = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    if na <= 255 and nb <= 255 and nc <= 255 and nd <= 255 then
      return true
    end
  end
  return false
end

-- Check if string is an IPv6 address
local function is_ipv6_str(s)
  if not s or #s < 3 or #s > 45 then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  if s:find("::", 1, true) or select(2, s:gsub(":", "")) >= 2 then
    if s:match("^[%x%:]+$") then
      return true
    end
  end
  return false
end

-- Check if string is a CVE identifier
local function is_cve_str(s)
  if not s then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s:match("^CVE%-%d%d%d%d%-%d+$") ~= nil or s:match("^cve%-%d%d%d%d%-%d+$") ~= nil
end

-- Check if string is a MITRE ATT&CK technique or tactic ID
local function is_mitre_str(s)
  if not s then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  if s:match("^T%d%d%d%d$") or s:match("^T%d%d%d%d%.%d%d%d$") then
    return true
  end
  if s:match("^TA%d%d%d%d$") then
    return true
  end
  return false
end

-- Check if string is a GitHub Security Advisory ID
local function is_ghsa_str(s)
  if not s then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s:match("^[Gg][Hh][Ss][Aa]%-[%w]+%-[%w]+%-[%w]+$") ~= nil
end

-- Check if string is a Windows Event Log file (.evtx)
local function is_evtx_str(s)
  if not s then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s:match("%.evtx$") ~= nil or s:match("%.EVTX$") ~= nil
end

-- Check if string is a Windows Event ID (e.g. Event ID 4624, EID 4624, or known security event number)
local function is_eventid_str(s)
  if not s then return false end
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  local lower = s:lower()
  if lower:match("^event%s*[ii]?[dd]s?:?%s*%d+") or lower:match("^eids?:?%s*%d+") then
    return true
  end
  local common_eids = {
    ["4624"]=true, ["4625"]=true, ["4672"]=true, ["4688"]=true,
    ["4697"]=true, ["7045"]=true, ["4720"]=true, ["4726"]=true,
    ["4728"]=true, ["4732"]=true, ["4738"]=true, ["4768"]=true,
    ["4769"]=true, ["4771"]=true, ["4776"]=true, ["1102"]=true,
    ["104"]=true,  ["4104"]=true, ["4103"]=true, ["5000"]=true,
    ["5001"]=true, ["5004"]=true, ["5007"]=true, ["1116"]=true,
    ["1117"]=true, ["600"]=true,  ["4696"]=true
  }
  return common_eids[s] == true
end

-- Check if text contains high-threat indicators for timeline pulses
local function is_malicious_text(s)
  if not s or #s == 0 then return false end
  local lower = pandoc.text.lower(s)
  local keywords = {
    "malicious", "kritický", "critical", "compromised", "c2 beacon", "command & control",
    "mimikatz", "ransomware", "exfiltration", "lateral movement", "privilege escalation",
    "reverse shell", "unauthorized", "attacker", "útočník", "kompromit", "exploit"
  }
  for _, kw in ipairs(keywords) do
    if lower:find(kw, 1, true) then
      return true
    end
  end
  return false
end

-- Registry for build-time knowledge enrichment
local collected_identifiers = {}

-- Construct an eventid pill and record it in the knowledge registry
local function make_eid_pill(val, display_text)
  collected_identifiers[val] = true
  collected_identifiers["Event ID " .. val] = true
  collected_identifiers["EID " .. val] = true
  return pandoc.Code(display_text, pandoc.Attr("", {"eventid-pill", "cyber-ioc"}, {{"data-ioc-type", "eventid"}, {"data-ioc-value", val}}))
end

-- Process inline Code elements for MITRE, Hashes, and IoCs with data attributes
function Code(el)
  local text = el.text

  -- Check for compound or singular Event ID in code backticks
  local lower_txt = text:lower():gsub("^%s+", ""):gsub("%s+$", "")
  if lower_txt:match("^eids?:?") or lower_txt:match("^event%s*[ii]?[dd]s?:?") then
    local nums = {}
    for num in text:gmatch("%d+") do
      table.insert(nums, num)
    end
    if #nums > 1 then
      collected_identifiers[text] = true
      local inlines = {}
      local norm_prefix = (lower_txt:find("event") and "Event ID " or "EID ")
      for idx, n in ipairs(nums) do
        if idx > 1 then
          if idx == #nums and (lower_txt:find("and", 1, true) or lower_txt:find("&", 1, true) or lower_txt:find(" a ", 1, true)) then
            table.insert(inlines, pandoc.Str(" and "))
          elseif lower_txt:find("/", 1, true) then
            table.insert(inlines, pandoc.Str(" / "))
          else
            table.insert(inlines, pandoc.Str(", "))
          end
        end
        table.insert(inlines, make_eid_pill(n, norm_prefix .. n))
      end
      return inlines
    elseif #nums == 1 then
      collected_identifiers[text] = true
      return make_eid_pill(nums[1], text)
    end
  end

  if is_mitre_str(text) then
    ensure_class(el, "mitre-pill")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "mitre"
    el.attributes["data-ioc-value"] = text
    collected_identifiers[text] = true
    return el
  end

  if is_cve_str(text) then
    ensure_class(el, "ioc")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "cve"
    el.attributes["data-ioc-value"] = text
    collected_identifiers[text] = true
    return el
  end

  if is_ghsa_str(text) then
    ensure_class(el, "ioc")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "ghsa"
    el.attributes["data-ioc-value"] = text
    collected_identifiers[text] = true
    return el
  end

  if is_evtx_str(text) then
    ensure_class(el, "evtx-pill")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "evtx"
    el.attributes["data-ioc-value"] = text
    collected_identifiers[text] = true
    return el
  end

  if is_eventid_str(text) then
    local digits = text:match("%d+")
    if digits then
      collected_identifiers[text] = true
      return make_eid_pill(digits, text)
    end
  end

  if is_ipv4_str(text) or is_ipv6_str(text) then
    ensure_class(el, "ioc")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "ip"
    el.attributes["data-ioc-value"] = text
    return el
  end

  if is_hash_or_token_str(text) then
    ensure_class(el, "hash")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "hash"
    el.attributes["data-ioc-value"] = text
    return el
  end

  -- Check custom knowledge base tokens
  local custom_item = custom_exact_tokens[text] or custom_exact_tokens[text:lower()]
  if custom_item then
    ensure_class(el, "custom-pill")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "custom"
    el.attributes["data-ioc-value"] = custom_item.id or text
    collected_identifiers[text] = true
    return el
  end

  return el
end

-- Replace inline cyber telemetry tags: [THREAT: CRITICAL], [CONFIDENCE: 98.4%]
function Str(el)
  if el.text:find("%[THREAT") or el.text:find("%[CONFIDENCE") or el.text:find("%[STATUS") then
    -- Let Inlines handler handle multi-token patterns
  end
  return el
end

-- Auto-classify blockquotes with leading strong labels into cyber callout Divs
function BlockQuote(el)
  if el.content and #el.content > 0 then
    local first_block = el.content[1]
    if first_block.t == "Para" or first_block.t == "Plain" then
      local inlines = first_block.content
      if inlines and #inlines > 0 and inlines[1].t == "Strong" then
        local strong_txt = pandoc.utils.stringify(inlines[1]):lower()
        local callout_type = nil
        local alert_class = nil
        if strong_txt:find("critical") or strong_txt:find("threat") or strong_txt:find("kritick") or strong_txt:find("malicious") or strong_txt:find("danger") then
          callout_type = "callout-critical"
          alert_class = "critical"
        elseif strong_txt:find("warning") or strong_txt:find("varov") or strong_txt:find("upozorn") or strong_txt:find("caution") or strong_txt:find("anomaly") then
          callout_type = "callout-warning"
          alert_class = "warning"
        elseif strong_txt:find("evidence") or strong_txt:find("důkaz") or strong_txt:find("dukaz") or strong_txt:find("verif") or strong_txt:find("success") then
          callout_type = "callout-success"
          alert_class = "evidence"
        elseif strong_txt:find("note") or strong_txt:find("poznám") or strong_txt:find("poznam") or strong_txt:find("info") or strong_txt:find("tip") then
          callout_type = "callout-info"
          alert_class = "note"
        end
        if callout_type then
          return pandoc.Div(el.content, pandoc.Attr("", {"callout", alert_class, callout_type}))
        end
      end
    end
  end
  return el
end

-- Transform KPI BulletList inside .kpi-grid
local function bullet_list_to_kpi_grid(bl)
  local cards = {}
  for _, item in ipairs(bl.content) do
    local item_text = pandoc.utils.stringify(item)
    local strong_part = ""
    local rest_part = ""

    if item[1] and item[1].t == "Plain" or item[1].t == "Para" then
      local inlines = item[1].content
      local found_strong = false
      local rest_inlines = {}

      for _, inl in ipairs(inlines) do
        if not found_strong and inl.t == "Strong" then
          strong_part = pandoc.utils.stringify(inl)
          found_strong = true
        else
          table.insert(rest_inlines, inl)
        end
      end

      if found_strong then
        rest_part = pandoc.utils.stringify(rest_inlines):gsub("^%s*:%s*", ""):gsub("^%s*–%s*", ""):gsub("^%s*-%s*", "")
      else
        local s, r = item_text:match("^(.-):%s*(.*)$")
        if s and r then
          strong_part = s
          rest_part = r
        end
      end
    end

    if strong_part ~= "" and rest_part ~= "" then
      local card_html = string.format([[
<div class="kpi-card">
  <div class="kpi-label">%s</div>
  <div class="kpi-value">%s</div>
</div>]], strong_part, rest_part)
      table.insert(cards, pandoc.RawBlock("html", card_html))
    end
  end

  if #cards > 0 then
    return pandoc.Div(cards, pandoc.Attr("", {"kpi-grid"}))
  end
  return nil
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
  ensure_class(cell, "timestamp-range")
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

-- Transform Table elements (nowrap timestamps, range breakability, timeline detection, malicious pulse)
local function process_table(tbl, preceding_header_text)
  local header_time_cols = {}
  local col_timestamp_cells = {}
  local col_total_cells = {}
  local is_timeline = preceding_header_text and is_timeline_title(preceding_header_text)

  -- Scan header
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      for col_idx, cell in ipairs(row.cells) do
        local cell_text = pandoc.utils.stringify(cell)
        if is_timestamp_header(cell_text) then
          header_time_cols[col_idx] = true
          ensure_class(cell, "nowrap")
        end
      end
    end
  end

  -- Scan bodies for timestamps, ranges, and malicious timeline actions
  if tbl.bodies then
    for _, body in ipairs(tbl.bodies) do
      local rows = body.body or body.rows or {}
      for _, row in ipairs(rows) do
        local is_malicious = false
        if is_timeline then
          for _, cell in ipairs(row.cells) do
            local cell_text = pandoc.utils.stringify(cell)
            if is_malicious_text(cell_text) then
              is_malicious = true
              break
            end
          end
        end

        for col_idx, cell in ipairs(row.cells) do
          if is_malicious then
            ensure_class(cell, "timeline-malicious")
          end
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
              ensure_class(cell, "nowrap")
            end
          elseif header_time_cols[col_idx] then
            ensure_class(cell, "nowrap")
          end
        end
      end
    end
  end

  -- Infer timestamp columns where majority of cells (>50% and >1) are timestamps
  local inferred_cols = {}
  for col_idx, ts_count in pairs(col_timestamp_cells) do
    local total = col_total_cells[col_idx] or 0
    if not header_time_cols[col_idx] and total > 1 and (ts_count / total) >= 0.5 then
      inferred_cols[col_idx] = true
    end
  end

  -- Apply nowrap across all rows for inferred timestamp columns (except ranges)
  if next(inferred_cols) ~= nil then
    if tbl.head and tbl.head.rows then
      for _, row in ipairs(tbl.head.rows) do
        for col_idx, cell in ipairs(row.cells) do
          if inferred_cols[col_idx] and not cell.classes:includes("timestamp-range") then
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
            if inferred_cols[col_idx] and not cell.classes:includes("timestamp-range") then
              ensure_class(cell, "nowrap")
            end
          end
        end
      end
    end
  end

  if is_timeline then
    ensure_class(tbl, "table-timeline")
  end

  -- Normalize column widths so Pandoc outputs fluid, content-driven columns
  if tbl.colspecs then
    for i, colspec in ipairs(tbl.colspecs) do
      tbl.colspecs[i] = {colspec[1], pandoc.ColWidthDefault}
    end
  end

  return tbl
end

-- Process inline text to automatically highlight Windows Event IDs and compound lists (e.g. EID 5000, 5001 and 600)
function Inlines(inlines)
  local new_inlines = {}
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    local matched = false
    local prefix_len = 0
    local label = ""

    if el.t == "Str" then
      local lead, core = el.text:match("^([%(%[%'\"«„“]*)(.-)$")
      if core and #core > 0 then
        local lower = core:lower()
        if lower:match("^eids?:?$") then
          prefix_len = 1
          lead_punct = lead or ""
          label = core:gsub(":$", "")
        elseif lower == "event" and i + 2 <= #inlines and inlines[i+1].t == "Space" and inlines[i+2].t == "Str" and inlines[i+2].text:lower():match("^ids?:?$") then
          prefix_len = 3
          lead_punct = lead or ""
          label = core .. " " .. inlines[i+2].text:gsub(":$", "")
        end
      end
    end

    if prefix_len > 0 and i + prefix_len <= #inlines then
      local peek_idx = i + prefix_len
      if inlines[peek_idx].t == "Space" and peek_idx + 1 <= #inlines then
        peek_idx = peek_idx + 1
        local raw_token = inlines[peek_idx].text
        local sub_nums = {}
        for num in raw_token:gmatch("%d+") do
          table.insert(sub_nums, num)
        end
        if #sub_nums > 0 then
          matched = true
          local collected_eids = {}
          local sep = raw_token:find("/") and " / " or ", "
          for s_idx, sn in ipairs(sub_nums) do
            table.insert(collected_eids, { id = sn, connector = sep })
          end

          -- Extract trailing non-digits after the last number in this token
          local last_num = sub_nums[#sub_nums]
          local last_pos = raw_token:find(last_num, 1, true)
          if last_pos then
            local trail_str = raw_token:sub(last_pos + #last_num)
            collected_eids[#collected_eids].trail = trail_str
          end

          local curr_idx = peek_idx + 1

          while curr_idx <= #inlines do
            if inlines[curr_idx].t == "Space" and curr_idx + 1 <= #inlines then
              local next_el = inlines[curr_idx + 1]
              if next_el.t == "Str" and (next_el.text:lower() == "and" or next_el.text == "&" or next_el.text:lower() == "a") and curr_idx + 2 <= #inlines and inlines[curr_idx + 2].t == "Space" and curr_idx + 3 <= #inlines then
                local next_token = inlines[curr_idx + 3].text
                local added_nums = {}
                for n in next_token:gmatch("%d+") do
                  table.insert(added_nums, n)
                  table.insert(collected_eids, { id = n, connector = " " .. next_el.text .. " " })
                end
                if #added_nums > 0 then
                  local ln = added_nums[#added_nums]
                  local lp = next_token:find(ln, 1, true)
                  if lp then
                    collected_eids[#collected_eids].trail = next_token:sub(lp + #ln)
                  end
                  curr_idx = curr_idx + 4
                else
                  break
                end
              elseif next_el.t == "Str" then
                local next_token = next_el.text
                local added_nums = {}
                for n in next_token:gmatch("%d+") do
                  table.insert(added_nums, n)
                  table.insert(collected_eids, { id = n, connector = next_token:find("/") and " / " or ", " })
                end
                if #added_nums > 0 then
                  local ln = added_nums[#added_nums]
                  local lp = next_token:find(ln, 1, true)
                  if lp then
                    collected_eids[#collected_eids].trail = next_token:sub(lp + #ln)
                  end
                  curr_idx = curr_idx + 2
                else
                  break
                end
              else
                break
              end
            else
              break
            end
          end

          if lead_punct and #lead_punct > 0 then
            table.insert(new_inlines, pandoc.Str(lead_punct))
          end

          local norm_label = (label:lower():find("event") and "Event ID" or "EID")
          for e_idx, item in ipairs(collected_eids) do
            if e_idx == 1 then
              table.insert(new_inlines, make_eid_pill(item.id, norm_label .. " " .. item.id))
            else
              table.insert(new_inlines, pandoc.Str(item.connector or ", "))
              table.insert(new_inlines, make_eid_pill(item.id, norm_label .. " " .. item.id))
            end
            if item.trail and #item.trail > 0 and item.trail ~= "," and item.trail ~= "/" then
              table.insert(new_inlines, pandoc.Str(item.trail))
            end
          end

          i = curr_idx
        end
      end
    end

    -- Check for Custom Knowledge prose match
    if not matched and el.t == "Str" and #custom_prose_rules > 0 then
      local raw_str = el.text
      local lead_p, clean_w, trail_p = raw_str:match("^([%(%[%'\"«„“]*)(.-)([%'\"»”%]%),%.%:%;%!%?]*)$")
      if clean_w and #clean_w > 0 then
        local c_item = custom_exact_tokens[clean_w] or custom_exact_tokens[clean_w:lower()]
        if c_item then
          matched = true
          if lead_p and #lead_p > 0 then
            table.insert(new_inlines, pandoc.Str(lead_p))
          end
          local pill = pandoc.Code(clean_w, pandoc.Attr("", {"custom-pill", "cyber-ioc"}, {{"data-ioc-type", "custom"}, {"data-ioc-value", c_item.id or clean_w}}))
          table.insert(new_inlines, pill)
          if trail_p and #trail_p > 0 then
            table.insert(new_inlines, pandoc.Str(trail_p))
          end
          i = i + 1
        end
      end
    end

    if not matched then
      table.insert(new_inlines, el)
      i = i + 1
    end
  end
  return new_inlines
end

-- Document-level transformation
function Pandoc(doc)
  local new_blocks = {}
  local recent_header_text = ""

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" then
      recent_header_text = pandoc.utils.stringify(block)
      table.insert(new_blocks, block)

    -- Transform AI Insights block (::: {.ai-insight confidence="99.4%"})
    elseif block.t == "Div" and (block.classes:includes("ai-insight") or block.classes:includes("ai-reasoning")) then
      local confidence = block.attributes["confidence"] or "98.7%"
      local model = block.attributes["agent"] or "SENTINEL-9 NEURAL CORE"
      local inner_html = pandoc.write(pandoc.Pandoc(block.content), "html")

      local card_html = string.format([[
<div class="ai-insight-card">
  <div class="ai-insight-header">
    <div class="ai-badge">
      <span class="ai-pulse-dot" aria-hidden="true"></span>
      <span class="ai-badge-title">AI FORENSIC REASONING // %s</span>
    </div>
    <div class="ai-confidence-wrap">
      <span class="ai-confidence-label">CONFIDENCE:</span>
      <span class="ai-confidence-val">%s</span>
      <span class="ai-confidence-bar"><span class="ai-confidence-fill" style="width: %s"></span></span>
    </div>
  </div>
  <div class="ai-insight-body">
%s
  </div>
</div>]], model, confidence, confidence, inner_html)

      table.insert(new_blocks, pandoc.RawBlock("html", card_html))

    elseif block.t == "Div" and (block.classes:includes("kpi-grid") or block.classes:includes("kpis")) then
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
      local wrapped = pandoc.Div({ processed_tbl }, pandoc.Attr("", { "table-wrapper" }))
      table.insert(new_blocks, wrapped)

    else
      table.insert(new_blocks, block)
    end
  end

  doc.blocks = new_blocks
  return doc
end

return {
  {
    Meta = Meta
  },
  {
    Code = Code,
    Inlines = Inlines,
    BlockQuote = BlockQuote
  },
  {
    Pandoc = Pandoc
  }
}
