import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { compile } from 'svelte/compiler';

/**
 * build-components.mjs
 * Pure Svelte 5 component compiler for md-style interactive documents.
 * 
 * Usage:
 *   node build-components.mjs <config-json-path-or-stdin>
 * 
 * Config schema:
 *   [
 *     { "name": "LogicalPhysicalMap", "path": "/path/to/LogicalPhysicalMap.svelte" }
 *   ]
 */

async function readInput() {
  const arg = process.argv[2];
  if (arg && arg !== '-') {
    return fs.readFileSync(arg, 'utf-8');
  }
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function transformSvelteClientJs(code, componentName) {
  // Strip disclose-version or side-effect internal imports
  let transformed = code.replace(/import\s+['\"][^'\"]+['\"];?\s*/g, '');

  // Strip `import * as $ from '...'`
  transformed = transformed.replace(/import\s+\*\s+as\s+\$\s+from\s+['\"][^'\"]+['\"];?\s*/g, '');

  // Convert `import { a, b, c } from 'svelte';` to `const { a, b, c } = viewer;`
  transformed = transformed.replace(/import\s+\{([^}]+)\}\s+from\s+['\"]svelte['\"];?\s*/g, (_, named) => {
    return `const { ${named.trim()} } = viewer;\n`;
  });

  // Convert `export default function <Name>` or `export default <Name>`
  let defaultIdentifier = componentName;
  if (/export\s+default\s+function\s+([A-Za-z0-9_$]+)/.test(transformed)) {
    transformed = transformed.replace(/export\s+default\s+function\s+([A-Za-z0-9_$]+)/, (_, fnName) => {
      defaultIdentifier = fnName;
      return `function ${fnName}`;
    });
  } else if (/export\s+default\s+([A-Za-z0-9_$]+);?/.test(transformed)) {
    transformed = transformed.replace(/export\s+default\s+([A-Za-z0-9_$]+);?/, (_, id) => {
      defaultIdentifier = id;
      return '';
    });
  }

  const iife = `/** [md-style dynamic component: ${componentName}] **/
(function() {
  const viewer = window.MdStyleViewer || {};
  const $ = viewer.svelteInternal || {};
  ${transformed}
  window.__MD_STYLE_COMPONENTS__ = window.__MD_STYLE_COMPONENTS__ || {};
  window.__MD_STYLE_COMPONENTS__[${JSON.stringify(componentName)}] = ${defaultIdentifier};
  if (viewer.mountDocumentComponents) {
    try { viewer.mountDocumentComponents(); } catch(e) {}
  }
})();
`;
  return iife;
}

async function main() {
  try {
    const rawInput = await readInput();
    if (!rawInput.trim()) {
      console.error(JSON.stringify({ success: false, error: 'Empty input configuration' }));
      process.exit(1);
    }

    const items = JSON.parse(rawInput);
    const results = {};
    let aggregatedCss = '';

    for (const item of items) {
      const { name, path: filePath } = item;
      if (!fs.existsSync(filePath)) {
        throw new Error(`Component file not found: ${filePath}`);
      }

      const source = fs.readFileSync(filePath, 'utf-8');
      const hash = crypto.createHash('sha256').update(source).digest('hex');

      const compiled = compile(source, {
        filename: path.basename(filePath),
        generate: 'client',
        dev: false
      });

      const clientJs = transformSvelteClientJs(compiled.js.code, name);
      const css = compiled.css ? compiled.css.code : '';
      if (css) {
        aggregatedCss += `/* [md-style component: ${name}] */\n${css}\n`;
      }

      results[name] = {
        name,
        filePath,
        hash,
        js: clientJs,
        css
      };
    }

    const output = {
      success: true,
      components: results,
      aggregatedCss
    };

    process.stdout.write(JSON.stringify(output, null, 2));
  } catch (err) {
    const errorOutput = {
      success: false,
      error: err.message,
      stack: err.stack
    };
    process.stderr.write(JSON.stringify(errorOutput));
    process.exit(1);
  }
}

main();
