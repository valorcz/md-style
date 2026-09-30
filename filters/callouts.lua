-- ==============================================================================
-- callouts.lua
-- Pandoc Lua filter for GitHub-style Alerts and Admonition Callout Boxes
--
-- Features:
-- 1. Standard GitHub alert blockquotes:
--    > [!NOTE]
--    > Content here...
--
--    Supported types: [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION],
--                     [!CRITICAL], [!INFO], [!SUCCESS], [!DANGER], [!EVIDENCE], [!FINDING]
--
-- 2. Clean, professional monochromatic vector SVG icons with currentColor
--    (Zero colored emojis; strictly matches header accent color)
--
-- 3. Multilingual title localization (Czech / Slovak, English default)
--
-- 4. Optional inline custom titles on the first line:
--    > [!NOTE] Custom Title Header
--    > Content here...
-- ==============================================================================

local script_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE)
local octicons = dofile(script_dir .. "/../vendor/octicons.lua")

local CALLOUT_CONFIG = {
  ["note"]      = { class = "note",      icon = "info",         cs_title = "POZNÁMKA",  en_title = "NOTE" },
  ["info"]      = { class = "note",      icon = "info",         cs_title = "INFORMACE", en_title = "INFO" },
  ["tip"]       = { class = "tip",       icon = "light-bulb",   cs_title = "TIP",       en_title = "TIP" },
  ["success"]   = { class = "tip",       icon = "check-circle", cs_title = "ÚSPĚCH",    en_title = "SUCCESS" },
  ["important"] = { class = "important", icon = "important",    cs_title = "DŮLEŽITÉ",  en_title = "IMPORTANT" },
  ["warning"]   = { class = "warning",   icon = "alert",        cs_title = "VAROVÁNÍ",  en_title = "WARNING" },
  ["caution"]   = { class = "caution",   icon = "stop",         cs_title = "POZOR",     en_title = "CAUTION" },
  ["critical"]  = { class = "critical",  icon = "shield-slash", cs_title = "KRITICKÉ",  en_title = "CRITICAL" },
  ["danger"]    = { class = "critical",  icon = "shield-slash", cs_title = "NEBEZPEČÍ", en_title = "DANGER" },
  ["evidence"]  = { class = "evidence",  icon = "search",       cs_title = "DŮKAZ",     en_title = "EVIDENCE" },
  ["finding"]   = { class = "finding",   icon = "checklist",    cs_title = "ZJIŠTĚNÍ",  en_title = "FINDING" },
}

local doc_lang = "en"

local function Meta(meta)
  if meta.lang then
    doc_lang = pandoc.utils.stringify(meta.lang):lower()
  elseif meta.language then
    doc_lang = pandoc.utils.stringify(meta.language):lower()
  end
  return meta
end

local function BlockQuote(bq)
  if not bq.content or #bq.content == 0 then return nil end

  local first_block = bq.content[1]
  if first_block.t ~= "Para" and first_block.t ~= "Plain" then return nil end
  if not first_block.content or #first_block.content == 0 then return nil end

  local first_inl = first_block.content[1]
  if first_inl.t ~= "Str" then return nil end

  -- Match [!TAG]
  local tag = first_inl.text:match("^%[!([%a_%-]+)%]$")
  if not tag then return nil end

  local tag_lower = tag:lower()
  local cfg = CALLOUT_CONFIG[tag_lower]
  local alert_class = cfg and cfg.class or tag_lower
  local is_cs = doc_lang:match("^cs") or doc_lang:match("^cz") or doc_lang:match("^sk")
  local default_title = cfg and (is_cs and cfg.cs_title or cfg.en_title) or tag:upper()
  local alert_icon_svg = cfg and cfg.icon and octicons.to_svg(cfg.icon, "callout-icon") or ""

  -- Remove the [!TAG] inline token
  table.remove(first_block.content, 1)

  -- Consume immediate whitespace following [!TAG]
  if #first_block.content > 0 and first_block.content[1].t == "Space" then
    table.remove(first_block.content, 1)
  end

  -- Check if there is an explicit custom title on the rest of the first line
  local custom_title_inlines = {}
  local has_line_break = false

  while #first_block.content > 0 do
    local inl = first_block.content[1]
    if inl.t == "SoftBreak" or inl.t == "LineBreak" then
      has_line_break = true
      table.remove(first_block.content, 1)
      break
    else
      table.insert(custom_title_inlines, inl)
      table.remove(first_block.content, 1)
    end
  end

  local title_inlines = {}
  if alert_icon_svg ~= "" then
    table.insert(title_inlines, pandoc.Span({ pandoc.RawInline("html", alert_icon_svg) }, pandoc.Attr("", { "callout-icon" })))
    table.insert(title_inlines, pandoc.Space())
  end

  if #custom_title_inlines > 0 and has_line_break then
    -- User explicitly provided a custom title on the header line
    for _, inl in ipairs(custom_title_inlines) do
      table.insert(title_inlines, inl)
    end
  else
    -- Standard alert without custom title
    table.insert(title_inlines, pandoc.Span({ pandoc.Str(default_title) }, pandoc.Attr("", { "callout-label" })))

    -- If all text was on one line and no line break occurred, restore custom_title_inlines as body text
    if #custom_title_inlines > 0 then
      for i = #custom_title_inlines, 1, -1 do
        table.insert(first_block.content, 1, custom_title_inlines[i])
      end
    end
  end

  local title_div = pandoc.Div(
    { pandoc.Para(title_inlines) },
    pandoc.Attr("", { "title" })
  )

  local div_blocks = { title_div }
  if #first_block.content > 0 then
    table.insert(div_blocks, first_block)
  end
  for i = 2, #bq.content do
    table.insert(div_blocks, bq.content[i])
  end

  return pandoc.Div(div_blocks, pandoc.Attr("", { "callout", alert_class }))
end

return {
  { Meta = Meta },
  { BlockQuote = BlockQuote }
}
