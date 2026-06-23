#!/usr/bin/env node
/**
 * Convert docs/SYSTEM_REPORT.md → docs/SYSTEM_REPORT.pdf (Mermaid diagrams included).
 * Usage: node scripts/generate_report_pdf.mjs
 */

import { readFileSync, writeFileSync, unlinkSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const docsDir = join(root, "docs");
const mdPath = join(docsDir, "SYSTEM_REPORT.md");
const pdfPath = join(docsDir, "SYSTEM_REPORT.pdf");
const cssPath = join(docsDir, "report-pdf.css");

async function loadDeps() {
  const depsRoot = join(root, "scripts", "pdf-deps", "node_modules");
  const markedPath = join(depsRoot, "marked", "lib", "marked.esm.js");
  const puppeteerPath = join(depsRoot, "puppeteer", "lib", "esm", "puppeteer", "puppeteer.js");

  if (!existsSync(markedPath) || !existsSync(puppeteerPath)) {
    console.error(
      "Missing PDF dependencies. Run:\n" +
        "  npm install --prefix scripts/pdf-deps",
    );
    process.exit(1);
  }

  const { marked } = await import(pathToFileURL(markedPath).href);
  const { default: puppeteer } = await import(pathToFileURL(puppeteerPath).href);
  return { marked, puppeteer };
}

function mdToHtml(markdown, marked) {
  const withMermaid = markdown.replace(
    /```mermaid\n([\s\S]*?)```/g,
    (_m, diagram) => `<pre class="mermaid">${diagram.trim()}</pre>`,
  );

  return marked.parse(withMermaid, { gfm: true, breaks: false });
}

function buildHtml(bodyHtml, css) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>AI Scalping Trading Agent — System Report</title>
  <style>${css}</style>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
</head>
<body class="report-pdf">
${bodyHtml}
<script>
  mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
  mermaid.run({ querySelector: ".mermaid" }).catch(console.error);
</script>
</body>
</html>`;
}

async function main() {
  if (!existsSync(mdPath)) {
    console.error(`Not found: ${mdPath}`);
    process.exit(1);
  }

  const { marked, puppeteer } = await loadDeps();
  const markdown = readFileSync(mdPath, "utf8");
  const css = readFileSync(cssPath, "utf8");
  const bodyHtml = mdToHtml(markdown, marked);
  const html = buildHtml(bodyHtml, css);

  const tmpHtml = join(docsDir, ".SYSTEM_REPORT_pdf_temp.html");
  writeFileSync(tmpHtml, html);

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(tmpHtml).href, { waitUntil: "networkidle0" });
    await page.waitForFunction(
      () => {
        const nodes = document.querySelectorAll(".mermaid");
        if (nodes.length === 0) return true;
        return [...nodes].every((n) => n.querySelector("svg"));
      },
      { timeout: 60000 },
    );
    await page.pdf({
      path: pdfPath,
      format: "A4",
      printBackground: true,
      margin: { top: "18mm", right: "16mm", bottom: "18mm", left: "16mm" },
    });
    console.log(`PDF written: ${pdfPath}`);
  } finally {
    await browser.close();
    try {
      unlinkSync(tmpHtml);
    } catch {
      /* ignore */
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
