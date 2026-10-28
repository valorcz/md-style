/**
 * viewer/scripts/render-diagram.mjs
 * Build-time CLI diagram renderer powered by beautiful-mermaid.
 * Reads Mermaid diagram source from stdin and writes JSON to stdout:
 * { "success": true, "svg": "<svg>..." }
 * or
 * { "success": false, "reason": "...", "error": "..." }
 */

import { renderMermaidSVG } from 'beautiful-mermaid';
import * as pele from 'pele';
import fs from 'fs';

const SUPPORTED_PREFIXES = [
  'graph', 'flowchart', 'sequencediagram', 'classdiagram',
  'statediagram', 'statediagram-v2', 'erdiagram', 'xychart-beta'
];

function isSupportedDiagram(code) {
  const clean = code.split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0 && !line.startsWith('%%'));
  if (clean.length === 0) return false;
  const firstToken = clean[0].toLowerCase().split(/\s+/)[0];
  return SUPPORTED_PREFIXES.some(prefix => firstToken.startsWith(prefix));
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    theme: 'zinc-light',
    transparent: true,
    font: 'Inter'
  };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--theme=')) {
      options.theme = args[i].split('=')[1];
    } else if (args[i] === '--theme' && args[i + 1]) {
      options.theme = args[++i];
    } else if (args[i] === '--transparent') {
      options.transparent = true;
    } else if (args[i] === '--no-transparent') {
      options.transparent = false;
    } else if (args[i].startsWith('--font=')) {
      options.font = args[i].split('=')[1];
    }
  }
  return options;
}

try {
  const input = fs.readFileSync(0, 'utf-8').trim();
  if (!input) {
    console.log(JSON.stringify({ success: false, reason: 'empty_input', error: 'Empty diagram content' }));
    process.exit(0);
  }

  const options = parseArgs();

  // 1. Attempt beautiful-mermaid for its high-aesthetic layout
  if (isSupportedDiagram(input)) {
    try {
      const svg = renderMermaidSVG(input, options);
      if (svg) {
        console.log(JSON.stringify({ success: true, svg, engine: 'beautiful-mermaid' }));
        process.exit(0);
      }
    } catch (_) {
      // Fall through to pele
    }
  }

  // 2. Fallback to pele for all other diagram types or if beautiful-mermaid failed
  try {
    const res = pele.render(input);
    if (res && res.svg) {
      console.log(JSON.stringify({ success: true, svg: res.svg, engine: 'pele' }));
      process.exit(0);
    }
  } catch (_) {
    // Both failed
  }

  console.log(JSON.stringify({
    success: false,
    reason: 'unsupported_schema',
    error: 'Diagram schema could not be rendered by beautiful-mermaid or pele'
  }));
} catch (err) {
  const msg = err.message || String(err);
  console.log(JSON.stringify({
    success: false,
    reason: 'render_error',
    error: msg
  }));
}
