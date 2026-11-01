/**
 * viewer/scripts/render-diagram.mjs
 * Build-time CLI diagram renderer powered by pele.
 * Reads Mermaid diagram source from stdin and writes JSON to stdout:
 * { "success": true, "svg": "<svg>...", "engine": "pele" }
 * or
 * { "success": false, "reason": "...", "error": "..." }
 */

import * as pele from 'pele';
import fs from 'fs';

try {
  const input = fs.readFileSync(0, 'utf-8').trim();
  if (!input) {
    console.log(JSON.stringify({ success: false, reason: 'empty_input', error: 'Empty diagram content' }));
    process.exit(0);
  }

  const res = pele.render(input);
  if (res && res.svg) {
    console.log(JSON.stringify({ success: true, svg: res.svg, engine: 'pele' }));
    process.exit(0);
  }

  console.log(JSON.stringify({
    success: false,
    reason: 'render_error',
    error: 'Pele failed to produce SVG output'
  }));
} catch (err) {
  const msg = err.message || String(err);
  console.log(JSON.stringify({
    success: false,
    reason: 'render_error',
    error: msg
  }));
}
