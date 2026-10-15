#!/usr/bin/env node
/**
 * viewer/scripts/print-pdf.mjs
 * High-fidelity Headless Chromium PDF Generator using Chrome DevTools Protocol (CDP).
 * Generates vector PDFs with native headers, footers, page numbering, and bookmarks.
 */

import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const BROWSER_CANDIDATES = [
  process.env.CHROME_BIN,
  "chromium-browser",
  "chromium",
  "google-chrome",
  "google-chrome-stable",
  "brave-browser",
  "microsoft-edge",
].filter(Boolean);

async function findBrowserBinary() {
  for (const bin of BROWSER_CANDIDATES) {
    try {
      const proc = spawn("which", [bin]);
      const code = await new Promise((res) => proc.on("close", res));
      if (code === 0) return bin;
    } catch {
      // Continue searching
    }
  }
  // Check common absolute paths
  const commonPaths = [
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
  ];
  for (const p of commonPaths) {
    try {
      await fs.access(p);
      return p;
    } catch {}
  }
  return null;
}

async function printPdf(htmlPath, pdfPath, optionsArg = null) {
  const browserBin = await findBrowserBinary();
  if (!browserBin) {
    throw new Error("No suitable Chromium browser found (chromium-browser, google-chrome, brave).");
  }

  let options = {};
  if (optionsArg) {
    try {
      if (optionsArg.startsWith("{")) {
        options = JSON.parse(optionsArg);
      } else {
        const fileContent = await fs.readFile(optionsArg, "utf-8");
        options = JSON.parse(fileContent);
      }
    } catch (err) {
      console.warn(`[CDP Printer] Failed to parse options JSON: ${err.message}`);
    }
  }

  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "md-style-print-"));
  // Pick random high port between 9230 and 9990
  const port = Math.floor(9230 + Math.random() * 700);

  const chromeProc = spawn(browserBin, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-extensions",
    "--disable-dev-shm-usage",
    `--user-data-dir=${tmpDir}`,
    `--remote-debugging-port=${port}`,
    "about:blank",
  ]);

  let ws = null;

  try {
    // 1. Wait for CDP target endpoint
    let pageWsUrl = null;
    const maxRetries = 40;
    for (let i = 0; i < maxRetries; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json`);
        if (res.ok) {
          const targets = await res.json();
          const page = targets.find((t) => t.type === "page");
          if (page && page.webSocketDebuggerUrl) {
            pageWsUrl = page.webSocketDebuggerUrl;
            break;
          }
        }
      } catch {
        // Chromium still starting
      }
      await new Promise((r) => setTimeout(r, 100));
    }

    if (!pageWsUrl) {
      throw new Error(`Failed to connect to Chromium CDP endpoint on port ${port}`);
    }

    // 2. Connect via WebSocket
    ws = new WebSocket(pageWsUrl);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    let msgId = 1;
    const pending = new Map();

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id && pending.has(data.id)) {
        const { resolve, reject } = pending.get(data.id);
        pending.delete(data.id);
        if (data.error) reject(new Error(data.error.message));
        else resolve(data.result);
      }
    };

    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        pending.set(id, { resolve, reject });
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    // 3. Enable Page domain and navigate to target HTML
    await send("Page.enable");
    const absHtml = path.resolve(htmlPath);
    const fileUrl = "file://" + absHtml;
    await send("Page.navigate", { url: fileUrl });

    // Wait for network idle, font rendering, and layout stabilization
    const waitMs = options.waitMs ?? 700;
    await new Promise((r) => setTimeout(r, waitMs));

    // 4. Configure Page.printToPDF parameters
    const printParams = {
      printBackground: true,
      displayHeaderFooter: Boolean(options.headerTemplate || options.footerTemplate),
      headerTemplate: options.headerTemplate || "<div></div>",
      footerTemplate: options.footerTemplate || "<div></div>",
      marginTop: typeof options.marginTop === "number" ? options.marginTop : 0.8,
      marginBottom: typeof options.marginBottom === "number" ? options.marginBottom : 0.8,
      marginLeft: typeof options.marginLeft === "number" ? options.marginLeft : 0.6,
      marginRight: typeof options.marginRight === "number" ? options.marginRight : 0.6,
      landscape: Boolean(options.landscape),
      preferCSSPageSize: true,
      generateTaggedPDF: true,
      generateDocumentOutline: true,
    };

    const result = await send("Page.printToPDF", printParams);
    if (!result || !result.data) {
      throw new Error("Page.printToPDF returned empty response");
    }

    // 5. Write binary PDF
    const buffer = Buffer.from(result.data, "base64");
    const absPdf = path.resolve(pdfPath);
    await fs.mkdir(path.dirname(absPdf), { recursive: true });
    await fs.writeFile(absPdf, buffer);

    console.log(JSON.stringify({
      status: "success",
      output: absPdf,
      bytes: buffer.length,
      browser: browserBin,
    }));
  } finally {
    if (ws) {
      try { ws.close(); } catch {}
    }
    chromeProc.kill("SIGTERM");
    await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
  }
}

const [,, htmlArg, pdfArg, optArg] = process.argv;
if (!htmlArg || !pdfArg) {
  console.error("Usage: node print-pdf.mjs <input.html> <output.pdf> [optionsJson|optionsPath]");
  process.exit(1);
}

printPdf(htmlArg, pdfArg, optArg).catch((err) => {
  console.error(JSON.stringify({ status: "error", message: err.message }));
  process.exit(1);
});
