-- ==============================================================================
-- i18n.lua
-- Pandoc Lua filter for Multi-language Report Localization
--
-- Normalizes `language` or `lang` from frontmatter, sets Pandoc metadata
-- defaults (toc-title, abstract-title), and supports per-document overrides
-- (classification, report-type, examiner-label, date-label) via CSS custom properties.
-- ==============================================================================

local function stringify_meta(val)
  if val == nil then return nil end
  if type(val) == "string" then return val end
  return pandoc.utils.stringify(val)
end

function Pandoc(doc)
  local meta = doc.meta

  -- 1. Detect language from frontmatter: `language` or standard `lang`
  local raw_lang = stringify_meta(meta.language) or stringify_meta(meta.lang) or "en"
  local lang_code = raw_lang:match("^(%a%a)"):lower()

  -- Ensure Pandoc template gets the normalized lang code (e.g. "cs" or "en")
  meta.lang = pandoc.MetaString(lang_code)

  -- 2. Localize built-in Pandoc structure headers if not explicitly specified by author
  if lang_code == "cs" or lang_code == "cz" then
    if not meta["abstract-title"] then
      meta["abstract-title"] = pandoc.MetaInlines{pandoc.Str("Abstrakt")}
    end
    if not meta["toc-title"] then
      meta["toc-title"] = pandoc.MetaInlines{pandoc.Str("Obsah")}
    end
  else
    if not meta["abstract-title"] then
      meta["abstract-title"] = pandoc.MetaInlines{pandoc.Str("Abstract")}
    end
    if not meta["toc-title"] then
      meta["toc-title"] = pandoc.MetaInlines{pandoc.Str("Table of contents")}
    end
  end

  -- 3. Check for optional frontmatter string overrides
  local custom_css = {}

  -- Classification override (e.g. classification: "DUVERNE" or classification: "RESTRICTED")
  local classification = stringify_meta(meta.classification) or stringify_meta(meta["confidentiality-label"])
  if classification and #classification > 0 then
    table.insert(custom_css, string.format('  --i18n-confidential: %q;', classification))
  end

  -- Report badge / title override (e.g. report-type: "AUDITNÍ ZPRÁVA")
  local report_type = stringify_meta(meta["report-type"]) or stringify_meta(meta["report-badge"])
  if report_type and #report_type > 0 then
    table.insert(custom_css, string.format('  --i18n-report-title: %q;', report_type))
  end

  -- Examiner / author label override (e.g. examiner-label: "Analytik:")
  local examiner_label = stringify_meta(meta["examiner-label"]) or stringify_meta(meta["author-label"])
  if examiner_label and #examiner_label > 0 then
    table.insert(custom_css, string.format('  --i18n-examiner: %q;', examiner_label))
  end

  -- Date label override (e.g. date-label: "Vystaveno:")
  local date_label = stringify_meta(meta["date-label"])
  if date_label and #date_label > 0 then
    table.insert(custom_css, string.format('  --i18n-date: %q;', date_label))
  end

  -- If any custom CSS overrides were found, inject them as a raw HTML style block
  if #custom_css > 0 then
    local style_block = "<style>\n:root {\n" .. table.concat(custom_css, "\n") .. "\n}\n</style>"
    table.insert(doc.blocks, 1, pandoc.RawBlock("html", style_block))
  end

  doc.meta = meta
  return doc
end
