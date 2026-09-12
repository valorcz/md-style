-- ==============================================================================
-- svj-prep.lua
-- Pandoc filter for SVJ Invitations & Agenda Documents
--
-- 1. Inlines dynamic Table of Contents at [[TOC]] with clickable links.
-- 2. Normalizes Google Docs '1. ### Heading' into clean, numbered <h3> headers.
-- 3. Automatically transforms '***Návrh výboru:***' paragraphs into callouts.
-- ==============================================================================

local function stringify(inlines)
  return pandoc.utils.stringify(inlines)
end

-- Document-level transformation
function Pandoc(doc)
  local agenda_items = {}
  local toc_placeholder_idx = nil
  local in_detaily = false
  local awaiting_meeting_info = false
  local agenda_counter = 0
  local new_blocks = {}

  for idx, block in ipairs(doc.blocks) do
    -- Detect [[TOC]] placeholder
    if block.t == "Para" and stringify(block.content):match("^%s*%[%[TOC%]%]%s*$") then
      toc_placeholder_idx = #new_blocks + 1
      table.insert(new_blocks, block) -- will be replaced in pass 2

    -- Detect "Detaily jednání" H2 and "Termín a místo" H2
    elseif block.t == "Header" and block.level == 2 then
      local h2_text = stringify(block.content):lower()
      if h2_text:find("detaily") or h2_text:find("podrobnosti") then
        in_detaily = true
        block.identifier = "detaily-jednání"
      elseif h2_text:find("termín") or h2_text:find("termin") or h2_text:find("místo") or h2_text:find("misto") then
        awaiting_meeting_info = true
      end
      table.insert(new_blocks, block)

    -- Wrap meeting info bullet list into a key-info container
    elseif awaiting_meeting_info and block.t == "BulletList" then
      awaiting_meeting_info = false
      local card_div = pandoc.Div({ block }, pandoc.Attr("", { "meeting-key-info" }))
      table.insert(new_blocks, card_div)

    -- Case A: Google Docs exported "1. ### Heading" (OrderedList containing Header 3)
    elseif in_detaily and block.t == "OrderedList" then
      local unrolled = false
      local items_to_insert = {}

      for _, list_item in ipairs(block.content) do
        if #list_item > 0 and list_item[1].t == "Header" and list_item[1].level == 3 then
          unrolled = true
          agenda_counter = agenda_counter + 1
          local h3 = list_item[1]
          local raw_title = stringify(h3.content):gsub("^%d+%.%s*", "")
          local item_id = h3.identifier
          if not item_id or item_id == "" then
            item_id = pandoc.text.lower(raw_title):gsub("%s+", "-"):gsub("[^%w%-]", "")
          end

          table.insert(agenda_items, {
            num = agenda_counter,
            title = raw_title,
            id = item_id
          })

          local inlines = {
            pandoc.Span({ pandoc.Str(tostring(agenda_counter) .. ".") }, pandoc.Attr("", { "agenda-num" })),
            pandoc.Space()
          }
          for _, inl in ipairs(h3.content) do
            table.insert(inlines, inl)
          end

          local numbered_header = pandoc.Header(3, inlines, pandoc.Attr(item_id, { "agenda-heading" }))
          table.insert(items_to_insert, numbered_header)

          for b_i = 2, #list_item do
            table.insert(items_to_insert, list_item[b_i])
          end
        end
      end

      if unrolled then
        for _, b in ipairs(items_to_insert) do
          table.insert(new_blocks, b)
        end
      else
        table.insert(new_blocks, block)
      end

    -- Case B: Standard Header 3 under Detaily jednání
    elseif in_detaily and block.t == "Header" and block.level == 3 then
      agenda_counter = agenda_counter + 1
      local raw_title = stringify(block.content):gsub("^%d+%.%s*", "")
      local item_id = block.identifier
      if not item_id or item_id == "" then
        item_id = pandoc.text.lower(raw_title):gsub("%s+", "-"):gsub("[^%w%-]", "")
      end

      table.insert(agenda_items, {
        num = agenda_counter,
        title = raw_title,
        id = item_id
      })

      local inlines = {
        pandoc.Span({ pandoc.Str(tostring(agenda_counter) .. ".") }, pandoc.Attr("", { "agenda-num" })),
        pandoc.Space()
      }
      for _, inl in ipairs(block.content) do
        table.insert(inlines, inl)
      end

      local numbered_header = pandoc.Header(3, inlines, pandoc.Attr(item_id, { "agenda-heading" }))
      table.insert(new_blocks, numbered_header)

    -- Case C: Proposal paragraph ("***Návrh výboru:***")
    elseif block.t == "Para" and #block.content > 0 then
      local inls = block.content
      local is_proposal = false
      if inls[1].t == "Strong" or inls[1].t == "Emph" then
        local txt = stringify(inls[1]):lower()
        if txt:find("návrh výboru") or txt:find("navrh vyboru") then
          is_proposal = true
        end
      end

      if is_proposal then
        local rest = {}
        for i = 2, #inls do
          if not (#rest == 0 and inls[i].t == "Space") then
            table.insert(rest, inls[i])
          end
        end

        local ballot_div = pandoc.Div({
          pandoc.Span({ pandoc.Str("HLASOVÁNÍ:") }, pandoc.Attr("", { "ballot-prompt" })),
          pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" PRO") }, pandoc.Attr("", { "ballot-option", "ballot-pro" })),
          pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" PROTI") }, pandoc.Attr("", { "ballot-option", "ballot-con" })),
          pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" ZDRŽEL SE") }, pandoc.Attr("", { "ballot-option", "ballot-abs" }))
        }, pandoc.Attr("", { "proposal-ballot" }))

        local callout = pandoc.Div({
          pandoc.Para({
            pandoc.Span({ pandoc.Str("NÁVRH VÝBORU") }, pandoc.Attr("", { "proposal-label" })),
            pandoc.LineBreak(),
            pandoc.Span(rest, pandoc.Attr("", { "proposal-content" }))
          }),
          ballot_div
        }, pandoc.Attr("", { "proposal-callout" }))

        table.insert(new_blocks, callout)
      else
        table.insert(new_blocks, block)
      end

    else
      table.insert(new_blocks, block)
    end
  end

  -- Pass 2: Replace [[TOC]] with generated agenda list
  if toc_placeholder_idx and #agenda_items > 0 then
    local toc_list_items = {}
    for _, item in ipairs(agenda_items) do
      local link = pandoc.Link({ pandoc.Str(item.title) }, "#" .. item.id)
      table.insert(toc_list_items, { pandoc.Plain({ link }) })
    end

    local toc_ordered_list = pandoc.OrderedList(toc_list_items)

    local toc_div = pandoc.Div({
      toc_ordered_list
    }, pandoc.Attr("", { "agenda-toc-container" }))

    new_blocks[toc_placeholder_idx] = toc_div
  end

  doc.blocks = new_blocks
  return doc
end
