-- ==============================================================================
-- filters/mermaid.lua
-- Pandoc Lua Filter for Static Build-Time Mermaid Diagram Rendering
-- Powered by beautiful-mermaid with seamless client fallback & i18n captions
-- ==============================================================================

local json = pandoc.json

-- Determine the absolute directory where this filter resides
local filter_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE or "")
local root_dir = pandoc.path.normalize(pandoc.path.join({filter_dir, ".."}))
local bundle_path = pandoc.path.join({root_dir, "vendor", "beautiful-mermaid.bundle.mjs"})

-- Multi-language figure label dictionary
local FIGURE_LABELS = {
    en = "Figure",
    cs = "Obrázek",
    cz = "Obrázek",
    sk = "Obrázok",
    de = "Abbildung",
    fr = "Figure",
    es = "Figura",
    it = "Figura",
    pl = "Rysunek"
}

-- Locate available JS runtime (bun preferred, node fallback)
local js_runtime = nil
local function detect_runtime()
    if js_runtime ~= nil then return js_runtime end

    -- Check if bun exists
    local bun_check = pcall(function()
        return pandoc.pipe("bun", {"--version"}, "")
    end)
    if bun_check then
        js_runtime = "bun"
        return js_runtime
    end

    -- Check if node exists
    local node_check = pcall(function()
        return pandoc.pipe("node", {"--version"}, "")
    end)
    if node_check then
        js_runtime = "node"
        return js_runtime
    end

    js_runtime = false
    return js_runtime
end

-- Escape HTML special characters for attributes and text
local function escape_html(str)
    return str:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;")
end

local function file_exists(path)
    local f = io.open(path, "r")
    if f then
        f:close()
        return true
    end
    return false
end

-- State tracked across passes
local current_lang = "en"
local figure_count = 0
local has_fallback = false

-- Format figure caption with localized label & number
local function format_caption(caption_text, lang, count)
    if not caption_text or caption_text == "" then
        return ""
    end

    local default_label = FIGURE_LABELS[lang] or "Figure"

    -- Match patterns like "Figure 1: Title", "Figure 1 - Title", "Obrázek 1: Title"
    local prefix_pattern = "^([%a%u%l\192-\255]+)%s+(%d+)%s*[:%-%–%—%.]%s*(.*)$"
    local prefix_word, num, rest = caption_text:match(prefix_pattern)

    if prefix_word and num then
        local lower_prefix = prefix_word:lower()
        if lower_prefix == "figure" or lower_prefix == "obrazek" or lower_prefix == "obrázek"
           or lower_prefix == "obrazok" or lower_prefix == "obrázok" or lower_prefix == "abbildung"
           or lower_prefix == "figura" or lower_prefix == "rysunek" then
            return string.format(
                '\n  <figcaption class="mermaid-caption"><span class="figure-label">%s %s:</span> %s</figcaption>',
                escape_html(default_label), escape_html(num), escape_html(rest)
            )
        else
            -- Custom author prefix like "Diagram 1:" or "Graf 1:"
            return string.format(
                '\n  <figcaption class="mermaid-caption"><span class="figure-label">%s %s:</span> %s</figcaption>',
                escape_html(prefix_word), escape_html(num), escape_html(rest)
            )
        end
    end

    -- Caption without number prefix: auto-assign sequential number
    return string.format(
        '\n  <figcaption class="mermaid-caption"><span class="figure-label">%s %d:</span> %s</figcaption>',
        escape_html(default_label), count, escape_html(caption_text)
    )
end

return {
    -- Pass 1: Extract document language & reset figure counter
    {
        Pandoc = function(doc)
            local raw_lang = doc.meta.language or doc.meta.lang or "en"
            local str_lang = pandoc.utils.stringify(raw_lang):lower():match("^(%a%a)")
            if str_lang and FIGURE_LABELS[str_lang] then
                current_lang = str_lang
            else
                current_lang = "en"
            end
            figure_count = 0
            has_fallback = false
            return doc
        end
    },

    -- Pass 2: Process Mermaid codeblocks
    {
        CodeBlock = function(el)
            if not el.classes:includes("mermaid") then
                return nil
            end

            figure_count = figure_count + 1

            local code = el.text
            local id_attr = el.identifier ~= "" and string.format(' id="%s"', escape_html(el.identifier)) or ""
            local caption = el.attributes["caption"] or el.attributes["title"] or ""
            local caption_html = format_caption(caption, current_lang, figure_count)

            local runtime = detect_runtime()

            -- If no JS runtime or bundle is missing, emit client fallback
            if not runtime or not file_exists(bundle_path) then
                has_fallback = true
                return pandoc.RawBlock("html", string.format(
                    '<figure class="mermaid-diagram mermaid-fallback" data-engine="client"%s>\n  <div class="mermaid-svg-wrapper">\n    <pre class="mermaid">\n%s\n    </pre>\n  </div>%s\n</figure>',
                    id_attr, escape_html(code), caption_html
                ))
            end

            -- Run through beautiful-mermaid bundle
            local ok, raw_output = pcall(function()
                return pandoc.pipe(runtime, {bundle_path, "--theme=zinc-light", "--transparent"}, code)
            end)

            if ok and raw_output and raw_output ~= "" then
                local decode_ok, res = pcall(json.decode, raw_output)
                if decode_ok and res and res.success and res.svg then
                    -- Successfully rendered static SVG
                    return pandoc.RawBlock("html", string.format(
                        '<figure class="mermaid-diagram" data-engine="beautiful-mermaid"%s>\n  <div class="mermaid-svg-wrapper">\n%s\n  </div>%s\n</figure>',
                        id_attr, res.svg, caption_html
                    ))
                elseif decode_ok and res and res.reason == "unsupported_schema" then
                    -- Diagram type not supported by beautiful-mermaid: fall back to client mermaid
                    has_fallback = true
                    return pandoc.RawBlock("html", string.format(
                        '<figure class="mermaid-diagram mermaid-fallback" data-engine="client"%s>\n  <div class="mermaid-svg-wrapper">\n    <pre class="mermaid">\n%s\n    </pre>\n  </div>%s\n</figure>',
                        id_attr, escape_html(code), caption_html
                    ))
                else
                    -- Render syntax error or warning
                    local err_msg = (res and res.error) or "Failed to parse Mermaid diagram"
                    io.stderr:write(string.format("[WARNING] beautiful-mermaid render error: %s\n", err_msg))
                    has_fallback = true
                    return pandoc.RawBlock("html", string.format(
                        '<figure class="mermaid-diagram mermaid-fallback" data-engine="client"%s>\n  <div class="mermaid-svg-wrapper">\n    <pre class="mermaid">\n%s\n    </pre>\n  </div>%s\n</figure>',
                        id_attr, escape_html(code), caption_html
                    ))
                end
            else
                has_fallback = true
                return pandoc.RawBlock("html", string.format(
                    '<figure class="mermaid-diagram mermaid-fallback" data-engine="client"%s>\n  <div class="mermaid-svg-wrapper">\n    <pre class="mermaid">\n%s\n    </pre>\n  </div>%s\n</figure>',
                    id_attr, escape_html(code), caption_html
                ))
            end
        end
    },

    -- Pass 3: Flag fallback in document metadata
    {
        Pandoc = function(doc)
            if has_fallback then
                doc.meta["has-mermaid-fallback"] = true
            end
            return doc
        end
    }
}
