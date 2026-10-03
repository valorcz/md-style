-- ==============================================================================
-- styles/svj/ballot.lua
-- Dedicated Lua filter for the svj-ballot style.
-- Dynamically appends interactive/printable ballot options to proposal callouts.
-- Isolated strictly to svj-ballot to prevent bleed into any other themes.
-- ==============================================================================

function Div(div)
  if div.classes:includes("proposal-callout") then
    local ballot_div = pandoc.Div({
      pandoc.Span({ pandoc.Str("HLASOVÁNÍ:") }, pandoc.Attr("", { "ballot-prompt" })),
      pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" PRO") }, pandoc.Attr("", { "ballot-option", "ballot-pro" })),
      pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" PROTI") }, pandoc.Attr("", { "ballot-option", "ballot-con" })),
      pandoc.Span({ pandoc.Span({ pandoc.Str("☐") }, pandoc.Attr("", { "ballot-box-icon" })), pandoc.Str(" ZDRŽEL SE") }, pandoc.Attr("", { "ballot-option", "ballot-abs" }))
    }, pandoc.Attr("", { "proposal-ballot" }))

    table.insert(div.content, ballot_div)
    return div
  end
  return nil
end
