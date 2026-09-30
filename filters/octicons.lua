-- ==============================================================================
-- filters/octicons.lua
-- Pandoc Lua filter for GitHub Primer Octicons in Markdown
--
-- Supports:
-- 1. Shortcodes in text, headings, and tables:
--    :octicon-shield:
--    :octicon-terminal:
--    :octicon-database:
--    :octicon-key:
--    :octicon-alert:
--
-- 2. Spans:
--    [terminal]{.octicon}
--    []{.octicon .octicon-terminal}
-- ==============================================================================

local script_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE)
local octicons = dofile(script_dir .. "/../vendor/octicons.lua")

function Str(el)
  if not el.text:find(":") then return nil end

  local inlines = {}
  local last_pos = 1
  local text = el.text

  for match_start, tag, icon_name, match_end in text:gmatch("()(:([%a%d%-_]+):)()") do
    local clean_name = icon_name:match("^octicon%-(.+)$") or icon_name:match("^icon%-(.+)$")
    if clean_name and octicons.icons[clean_name] then
      if match_start > last_pos then
        table.insert(inlines, pandoc.Str(text:sub(last_pos, match_start - 1)))
      end
      local svg = octicons.to_svg(clean_name)
      table.insert(inlines, pandoc.RawInline("html", svg))
      last_pos = match_end
    end
  end

  if #inlines > 0 then
    if last_pos <= #text then
      table.insert(inlines, pandoc.Str(text:sub(last_pos)))
    end
    return inlines
  end

  return nil
end

function Span(el)
  if el.classes:includes("octicon") then
    local icon_name = nil
    for _, cls in ipairs(el.classes) do
      local name = cls:match("^octicon%-(.+)$")
      if name then
        icon_name = name
        break
      end
    end
    if not icon_name and #el.content > 0 then
      icon_name = pandoc.utils.stringify(el.content):gsub("^%s+", ""):gsub("%s+$", "")
    end
    if icon_name and octicons.icons[icon_name] then
      local svg = octicons.to_svg(icon_name)
      return pandoc.RawInline("html", svg)
    end
  end
  return el
end
