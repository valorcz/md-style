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
  if s:match("^[Ee]vent%s*[Ii]?[Dd]?:?%s*%d+$") or s:match("^[Ee][Ii][Dd]:?%s*%d+$") then
    return true
  end
  local common_eids = {
    ["4624"]=true, ["4625"]=true, ["4672"]=true, ["4688"]=true,
    ["4697"]=true, ["7045"]=true, ["4720"]=true, ["4728"]=true,
    ["4732"]=true, ["4768"]=true, ["4769"]=true, ["4771"]=true,
    ["4776"]=true, ["1102"]=true, ["104"]=true,  ["4104"]=true
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

-- Process inline Code elements for MITRE, Hashes, and IoCs with data attributes
function Code(el)
  local text = el.text

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
    ensure_class(el, "eventid-pill")
    ensure_class(el, "cyber-ioc")
    el.attributes["data-ioc-type"] = "eventid"
    el.attributes["data-ioc-value"] = text
    collected_identifiers[text] = true
    return el
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

-- Transform Table elements (nowrap timestamps, timeline detection, malicious pulse)
local function process_table(tbl, preceding_header_text)
  local inferred_cols = {}
  local is_timeline = preceding_header_text and is_timeline_title(preceding_header_text)

  -- Scan header
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      for col_idx, cell in ipairs(row.cells) do
        local cell_text = pandoc.utils.stringify(cell)
        if is_timestamp_header(cell_text) then
          inferred_cols[col_idx] = true
          ensure_class(cell, "nowrap")
        end
      end
    end
  end

  -- Scan bodies for timestamps and malicious timeline actions
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
          if is_timestamp_str(cell_text) then
            inferred_cols[col_idx] = true
            ensure_class(cell, "nowrap")
          end
        end
      end
    end
  end

  -- Apply nowrap across all rows for inferred timestamp columns
  if next(inferred_cols) ~= nil then
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

  if is_timeline then
    ensure_class(tbl, "table-timeline")
  end

  -- Normalize crushed column widths
  if tbl.colspecs then
    local has_crushed = false
    for _, colspec in ipairs(tbl.colspecs) do
      local w = colspec[2]
      if type(w) == "number" and w > 0 and w < 0.12 then
        has_crushed = true
        break
      end
    end
    if has_crushed then
      for i, colspec in ipairs(tbl.colspecs) do
        tbl.colspecs[i] = {colspec[1], pandoc.ColWidthDefault}
      end
    end
  end

  return tbl
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
      table.insert(new_blocks, processed_tbl)

    else
      table.insert(new_blocks, block)
    end
  end

  -- Embed Enriched Knowledge Base if any identifiers were detected
  if next(collected_identifiers) then
    local ids_args = {}
    for id_val, _ in pairs(collected_identifiers) do
      table.insert(ids_args, string.format("%q", id_val))
    end
    local script_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE or ".")
    local enrich_py = pandoc.path.join({script_dir, "..", "scripts", "enrich-identifiers.py"})
    local cmd = string.format("python3 %q %s", enrich_py, table.concat(ids_args, " "))
    local h = io.popen(cmd)
    if h then
      local json_data = h:read("*a")
      h:close()
      if json_data and #json_data > 2 then
        local clean_json = json_data:gsub("^%s+", ""):gsub("%s+$", "")
        local kb_block = pandoc.RawBlock("html", string.format('<script id="cyber-kb-data" type="application/json">\n%s\n</script>', clean_json))
        table.insert(new_blocks, kb_block)
      end
    end
  end

  doc.blocks = new_blocks
  return doc
end

return {
  {
    Code = Code,
    BlockQuote = BlockQuote
  },
  {
    Pandoc = Pandoc
  }
}
