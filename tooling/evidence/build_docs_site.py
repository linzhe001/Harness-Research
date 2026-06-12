#!/usr/bin/env python3
"""Render source Markdown docs into a lightweight human docs site."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "0.1"
DEFAULT_SOURCE_ROOT = Path("docs")
DEFAULT_OUTPUT_ROOT = Path("docs/_site")
DEFAULT_PREVIEW_INDEX = Path("docs/_views/evidence_preview_index.json")
MANIFEST_NAME = "manifest.json"
MARKER_RE = re.compile(r"\[(F|U|D|L|E):([A-Za-z0-9_.:-]+)\]")
WIKI_REF_RE = re.compile(r"\[\[([A-Za-z][A-Za-z0-9_-]*:[^\]|]+)(?:\|([^\]]+))?\]\]")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STATUS_RE = re.compile(r"^Status:\s*(.+?)\s*$", re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
TERMINAL_CODE_LANGUAGES = {"bash", "console", "sh", "shell", "terminal", "zsh"}
DIAGRAM_CODE_LANGUAGES = {"plain", "plaintext", "text", "txt"}
DATA_CODE_LANGUAGES = {"json", "toml", "yaml", "yml"}

STYLE_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f7f4;
  --paper: #fffefa;
  --panel: #f2f6f6;
  --nav-bg: #edf3f2;
  --ink: #2e3436;
  --text: #313638;
  --muted: #61706f;
  --faint: #8d9995;
  --line: #dbe4df;
  --line-strong: #b7c7c0;
  --accent: #405f7c;
  --accent-strong: #244f67;
  --accent-soft: #e4f0ef;
  --accent-warm: #9f6740;
  --pass: #2f7d5f;
  --pending: #9a6a16;
  --fail: #a64242;
  --blocked: #6f4a8e;
  --code: #111827;
  --shadow: 0 18px 42px rgba(33, 40, 44, 0.16);
  --font-sans: Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei",
    -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --font-serif: "Charter", "Noto Serif SC", "Source Han Serif SC",
    "Songti SC", Georgia, serif;
  --font-mono: ui-monospace, "Cascadia Mono", "Segoe UI Mono", "SFMono-Regular",
    "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New",
    monospace;
}
* { box-sizing: border-box; }
html {
  scroll-behavior: smooth;
}
body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 1.7;
  background: var(--bg);
  color: var(--text);
  min-width: 0;
}
body:lang(zh-Hans) {
  line-height: 1.82;
}
a { color: var(--accent-strong); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout {
  display: grid;
  grid-template-columns: minmax(248px, 280px) minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  border-right: 1px solid var(--line);
  background: var(--nav-bg);
  padding: 24px 18px 28px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}
.sidebar-header {
  border-bottom: 1px solid var(--line);
  margin: 0 0 18px;
  padding-bottom: 16px;
}
.site-eyebrow {
  color: var(--muted);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0;
  line-height: 1.3;
  margin: 0 0 6px;
  text-transform: uppercase;
}
.sidebar h1 {
  color: var(--ink);
  font-size: 17px;
  font-weight: 650;
  letter-spacing: 0;
  line-height: 1.25;
  margin: 0;
  max-width: 18rem;
}
.nav-section {
  margin: 10px 0;
}
.nav-section > summary {
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0;
  list-style: none;
  margin: 0 0 7px;
  text-transform: uppercase;
}
.nav-section > summary::-webkit-details-marker,
.nav-folder > summary::-webkit-details-marker {
  display: none;
}
.nav-section > summary::before,
.nav-folder > summary::before {
  color: var(--faint);
  content: ">";
  display: inline-block;
  font-weight: 650;
  margin-right: 7px;
  transform: rotate(0deg);
  width: 10px;
}
.nav-section[open] > summary::before,
.nav-folder[open] > summary::before {
  transform: rotate(90deg);
}
.nav-section-body {
  padding: 1px 0 4px;
}
.nav-folder {
  margin: 2px 0;
}
.nav-folder > summary {
  cursor: pointer;
  list-style: none;
}
.nav-children {
  border-left: 1px solid var(--line);
  margin-left: 12px;
  padding-left: 9px;
}
.nav-section a,
.nav-folder > summary a {
  display: block;
  border-radius: 6px;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.35;
  padding: 7px 9px;
  transition: background 120ms ease, box-shadow 120ms ease, color 120ms ease;
}
.nav-section a.active,
.nav-section a:hover,
.nav-folder > summary a.active,
.nav-folder > summary a:hover {
  background: var(--paper);
  box-shadow: inset 3px 0 0 var(--accent);
  text-decoration: none;
}
.content {
  min-width: 0;
  padding: 52px 56px 84px;
}
.content-inner {
  margin: 0 auto;
  max-width: 1240px;
  width: 100%;
}
.page-grid {
  align-items: start;
  display: grid;
  gap: 36px;
  grid-template-columns: minmax(0, 820px) minmax(168px, 220px);
}
.doc-meta {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  gap: 8px;
  line-height: 1.45;
  margin-bottom: 16px;
  overflow-wrap: break-word;
}
.doc-meta code {
  background: transparent;
  border: 0;
  color: var(--ink);
  padding: 0;
}
.page-rail {
  border-left: 1px solid var(--line);
  color: var(--muted);
  padding: 6px 0 6px 16px;
  position: sticky;
  top: 28px;
}
.page-rail strong {
  color: var(--ink);
  display: block;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0;
  margin-bottom: 8px;
  text-transform: uppercase;
}
.page-rail a {
  color: var(--muted);
  display: block;
  font-size: 13px;
  line-height: 1.35;
  padding: 5px 0;
}
.page-rail a.h3 {
  padding-left: 12px;
}
article {
  background: transparent;
  border: 0;
  border-radius: 0;
  font-family: var(--font-serif);
  min-width: 0;
  overflow-wrap: break-word;
  padding: 0;
}
article h1, article h2, article h3 {
  color: var(--ink);
  font-family: var(--font-sans);
  letter-spacing: 0;
  line-height: 1.22;
}
article h1 {
  font-size: 42px;
  font-weight: 650;
  margin: 0 0 20px;
}
article h2 {
  border-top: 1px solid var(--line);
  font-size: 24px;
  font-weight: 630;
  margin: 42px 0 14px;
  padding-top: 26px;
}
article h3 {
  font-size: 18px;
  font-weight: 630;
  margin: 26px 0 10px;
}
article p, article li {
  line-height: 1.78;
}
article p {
  margin: 0 0 1.05em;
}
article ul,
article ol {
  padding-left: 1.35rem;
}
.callout,
blockquote {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 8px;
  font-family: var(--font-sans);
  margin: 18px 0;
  padding: 14px 16px;
}
.callout p:last-child,
blockquote p:last-child {
  margin-bottom: 0;
}
.callout-title {
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 650;
  margin: 0 0 8px;
  text-transform: uppercase;
}
.callout-tip,
.callout-note {
  border-left-color: var(--accent);
}
.callout-warning,
.callout-important {
  border-left-color: var(--pending);
}
.callout-danger,
.callout-caution {
  border-left-color: var(--fail);
}
.code-block {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 7px;
  margin: 16px 0;
  overflow: hidden;
}
.code-label {
  align-items: center;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  display: flex;
  font-size: 11px;
  font-weight: 650;
  gap: 8px;
  letter-spacing: 0;
  min-height: 32px;
  padding: 7px 14px;
  text-transform: uppercase;
}
.code-label::before {
  background: var(--accent);
  border-radius: 999px;
  content: "";
  flex: 0 0 auto;
  height: 8px;
  width: 8px;
}
.code-block pre {
  background: var(--panel);
  color: #111827;
  font-family: var(--font-mono);
  font-size: 13px;
  font-variant-ligatures: none;
  line-height: 1.55;
  margin: 0;
  overflow: auto;
  padding: 16px;
  tab-size: 2;
}
.code-block-source .code-label::before { background: var(--accent); }
.code-block-source pre { background: var(--panel); color: #111827; }
.code-block-data .code-label::before { background: var(--pass); }
.code-block-data pre { background: #f7fffb; color: #12312f; }
.code-block-diagram {
  background: #fbfcff;
}
.code-block-diagram .code-label {
  background: #f1f5f9;
}
.code-block-diagram .code-label::before { background: #64748b; }
.code-block-diagram pre {
  background: #fbfcff;
  color: #253044;
  line-height: 1.5;
  white-space: pre;
}
.code-block-terminal {
  background: #0b1220;
  border-color: #1f2a44;
}
.code-block-terminal .code-label {
  background: #111827;
  border-bottom-color: #1f2a44;
  color: #cbd5e1;
}
.code-block-terminal .code-label::before {
  background: #ef4444;
  box-shadow: 12px 0 0 #eab308, 24px 0 0 #22c55e;
  margin-right: 24px;
}
.code-block-terminal pre {
  background: #0b1220;
  color: #dbeafe;
}
code {
  background: #eef2f6;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-variant-ligatures: none;
  padding: 1px 4px;
  overflow-wrap: anywhere;
}
.code-block pre code {
  background: transparent;
  overflow-wrap: normal;
  padding: 0;
}
table {
  border-collapse: collapse;
  display: block;
  font-family: var(--font-sans);
  overflow-x: auto;
  width: 100%;
}
th, td {
  border: 1px solid var(--line);
  padding: 9px 11px;
  vertical-align: top;
}
th {
  background: var(--panel);
  color: var(--ink);
  font-weight: 650;
  text-align: left;
}
.evidence-marker,
.reference-marker {
  background: var(--accent-soft);
  border: 1px solid #b9d8e2;
  border-radius: 999px;
  color: var(--accent-strong);
  cursor: pointer;
  display: inline-block;
  font-size: 0.86em;
  margin: 0 2px;
  padding: 0 6px;
  text-decoration: none;
}
.evidence-marker:hover,
.reference-marker:hover { text-decoration: none; }
.evidence-popover {
  background: var(--paper);
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  box-shadow: var(--shadow);
  color: var(--ink);
  display: none;
  max-height: min(24rem, calc(100vh - 32px));
  max-width: min(34rem, calc(100vw - 32px));
  overflow: auto;
  padding: 12px 14px;
  position: fixed;
  width: min(34rem, calc(100vw - 32px));
  z-index: 1000;
}
.evidence-popover strong {
  display: block;
  font-family: var(--font-sans);
  margin-bottom: 6px;
}
.evidence-popover p { margin: 6px 0; }
.evidence-popover .muted {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 12px;
}
@media (max-width: 1180px) {
  .page-grid {
    grid-template-columns: minmax(0, 880px);
  }
  .page-rail {
    display: none;
  }
}
@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 236px minmax(0, 1fr);
  }
  .content {
    padding: 32px 28px 64px;
  }
}
@media (max-width: 860px) {
  .layout { display: block; }
  .sidebar {
    border-bottom: 1px solid var(--line);
    border-right: 0;
    height: auto;
    max-height: 48vh;
    position: static;
  }
  .sidebar h1 {
    margin-bottom: 12px;
  }
  .nav-section { margin: 14px 0; }
  .nav-section a,
  .nav-folder > summary a {
    display: inline-block;
    margin: 2px 4px 2px 0;
  }
  .nav-children {
    margin-left: 4px;
    padding-left: 8px;
  }
  .content { padding: 22px 14px 48px; }
  article { padding: 0; }
}
@media (max-width: 520px) {
  article {
    margin-left: -14px;
    margin-right: -14px;
    padding: 0 14px;
  }
  article h1 { font-size: 30px; }
  article h2 { font-size: 22px; }
}
""".strip()

PREVIEW_JS = """
(function () {
  const dataEl = document.getElementById("evidence-preview-data");
  const popover = document.querySelector(".evidence-popover");
  if (!dataEl || !popover) return;

  let previews = {};
  let activeAnchor = null;
  let hideTimer = 0;
  try {
    previews = JSON.parse(dataEl.textContent || "{}");
  } catch (error) {
    return;
  }

  function previewFor(marker) {
    const item = (previews.markers || {})[marker];
    if (item && item.previews && item.previews.length) return item.previews[0];
    return (previews.evidence || {})[marker] || null;
  }

  function previewForAnchor(anchor) {
    const ref = anchor.getAttribute("data-ref");
    if (ref) return referencePreviewFor(ref);
    const marker = anchor.getAttribute("data-marker");
    if (marker) return previewFor(marker);
    const previewId = anchor.getAttribute("data-preview-id");
    if (!previewId) return null;
    return referencePreviewFor(previewId) || previewFor(previewId);
  }

  function place(anchor) {
    const rect = anchor.getBoundingClientRect();
    const gap = 10;
    const left = Math.min(
      rect.left,
      window.innerWidth - popover.offsetWidth - 16
    );
    const below = rect.bottom + gap;
    const above = rect.top - popover.offsetHeight - gap;
    const top =
      below + popover.offsetHeight <= window.innerHeight - 16
        ? below
        : Math.max(16, above);
    popover.style.left = Math.max(16, left) + "px";
    popover.style.top = Math.max(16, top) + "px";
  }

  function show(event) {
    const anchor = event.currentTarget;
    const marker =
      anchor.getAttribute("data-ref") ||
      anchor.getAttribute("data-marker") ||
      anchor.getAttribute("data-preview-id");
    const preview = previewForAnchor(anchor);
    if (!preview) return;
    activeAnchor = anchor;
    clearTimeout(hideTimer);
    popover.innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = preview.title || marker;
    const excerpt = document.createElement("p");
    excerpt.textContent = preview.excerpt || preview.body || "No preview recorded.";
    const meta = document.createElement("p");
    meta.className = "muted";
    meta.textContent = [
      preview.path,
      preview.support_relation,
      preview.kind,
      preview.truth_status
    ]
      .filter(Boolean)
      .join(" | ");
    popover.append(title, excerpt, meta);
    popover.style.display = "block";
    place(anchor);
  }

  function hide() {
    activeAnchor = null;
    popover.style.display = "none";
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 140);
  }

  document.querySelectorAll("[data-preview-id]").forEach((el) => {
    el.addEventListener("mouseenter", show);
    el.addEventListener("focus", show);
    el.addEventListener("mouseleave", scheduleHide);
    el.addEventListener("blur", scheduleHide);
  });

  popover.addEventListener("mouseenter", () => clearTimeout(hideTimer));
  popover.addEventListener("mouseleave", scheduleHide);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hide();
  });
  window.addEventListener("resize", () => {
    if (activeAnchor && popover.style.display === "block") place(activeAnchor);
  });

  function referencePreviewFor(ref) {
    const entry = (previews.entries || {})[ref];
    if (!entry) return null;
    const card = entry.preview || {};
    const paths = (entry.source_paths || []).map((item) => item.path).filter(Boolean);
    return {
      title: card.title || entry.title || ref,
      excerpt: card.body || entry.summary || "No preview recorded.",
      path: paths.join(", "),
      support_relation: [entry.kind, entry.truth_status, entry.owner]
        .filter(Boolean)
        .join(" | "),
    };
  }
})();
""".strip()


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def doc_id_for(source_path: Path, source_root: Path) -> str:
    relative = source_path.relative_to(source_root).with_suffix("")
    return "__".join(relative.parts)


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "section"


def code_block_kind(language: str) -> str:
    language_name = language.strip().split(maxsplit=1)[0] if language.strip() else ""
    language_key = slugify(language_name or "text")
    if language_key in TERMINAL_CODE_LANGUAGES:
        return "terminal"
    if language_key in DIAGRAM_CODE_LANGUAGES:
        return "diagram"
    if language_key in DATA_CODE_LANGUAGES:
        return "data"
    return "source"


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return fallback


def extract_page_headings(markdown: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        if level not in {2, 3}:
            continue
        text = match.group(2).strip()
        headings.append({"level": level, "text": text, "slug": slugify(text)})
    return headings


def split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    loaded = yaml.safe_load(match.group(1)) if match.group(1).strip() else {}
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter must be a mapping")
    return loaded, markdown[match.end() :]


def extract_status(markdown: str) -> str | None:
    for line in markdown.splitlines():
        match = STATUS_RE.match(line)
        if match:
            return match.group(1).strip()
    return None


def doc_kind_for(source_path: Path, source_root: Path) -> str:
    relative = source_path.relative_to(source_root)
    first = relative.parts[0] if relative.parts else ""
    if first == "10_contract":
        return "contract_doc"
    if first == "20_facts":
        return "fact_doc"
    if first == "30_evidence":
        return "conclusion_evidence"
    if first == "35_protocol":
        return "protocol_doc"
    if first == "40_iterations":
        return "iteration_doc"
    if first == "50_memory":
        return "memory_doc"
    return "current_doc"


def workflow_ref_target(
    ref: str,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> str | None:
    if current_html is None or workspace_root is None:
        return None
    entries = preview_data.get("entries", {})
    if not isinstance(entries, dict):
        return None
    target: str | None = None
    if ref.startswith("skill:"):
        target = f"docs/_site/workflow_handbook/skills/{ref.split(':', 1)[1]}.html"
    elif ref.startswith("stage:"):
        stages = {
            "WF0": "wf0_init",
            "WF1": "wf1_survey_idea",
            "WF2": "wf2_idea_debate",
            "WF3": "wf3_refine_idea",
            "WF4": "wf4_data_prep",
            "WF5": "wf5_baseline_repro",
            "WF6": "wf6_refine_arch",
            "WF7": "wf7_build_plan",
            "WF8": "wf8_code_expert",
            "WF9": "wf9_validate_run",
            "WF10": "wf10_iterate",
            "WF11": "wf11_final_exp",
            "WF12": "wf12_release",
        }
        page_id = stages.get(ref.split(":", 1)[1])
        if page_id:
            target = f"docs/_site/workflow_handbook/stages/{page_id}.html"
    elif ref.startswith("term:"):
        target = (
            "docs/_site/workflow_handbook/pages/workflow_terms.html#"
            + slugify(ref.split(":", 1)[1])
        )
    elif ref.startswith("source:"):
        source_ref = ref.split(":", 1)[1]
        source_path = source_ref.split("#", 1)[0]
        if (workspace_root / source_path).exists():
            target = source_ref
    elif ref.startswith("artifact:"):
        artifact_path = ref.split(":", 1)[1]
        if (workspace_root / artifact_path).exists():
            target = artifact_path
    elif ref.startswith("page:"):
        entry = entries.get(ref, {})
        source_paths = entry.get("source_paths", [])
        if isinstance(source_paths, list) and source_paths:
            source_path = source_paths[0].get("path")
            if isinstance(source_path, str) and source_path.startswith(
                "workflow_handbook/"
            ):
                relative = Path(source_path).relative_to("workflow_handbook")
                target = (
                    Path("docs/_site/workflow_handbook") / relative.with_suffix(".html")
                ).as_posix()
    if not target:
        return None
    return href_between(current_html, workspace_root / target)


def marker_preview_for(
    marker: str,
    preview_data: dict[str, Any],
) -> dict[str, Any] | None:
    item = (preview_data.get("markers") or {}).get(marker)
    if isinstance(item, dict):
        previews = item.get("previews")
        if isinstance(previews, list) and previews and isinstance(previews[0], dict):
            return previews[0]
    evidence = (preview_data.get("evidence") or {}).get(marker)
    return evidence if isinstance(evidence, dict) else None


def marker_target_path(
    marker: str,
    preview_data: dict[str, Any],
) -> str:
    item = (preview_data.get("markers") or {}).get(marker)
    if isinstance(item, dict):
        target_path = item.get("target_path")
        if isinstance(target_path, str) and target_path.strip():
            return target_path.strip()
    preview = marker_preview_for(marker, preview_data)
    if preview is None:
        return ""
    return str(preview.get("path", ""))


def html_target_for_source_path(
    source_path: str,
    *,
    current_html: Path | None,
    workspace_root: Path | None,
) -> str | None:
    if current_html is None or workspace_root is None or not source_path:
        return None
    normalized = source_path.replace("\\", "/").split("#", 1)[0]
    if normalized.startswith("docs/") and normalized.endswith(".md"):
        relative_doc = Path(normalized).relative_to("docs")
        target = workspace_root / "docs" / "_site" / relative_doc.with_suffix(".html")
        return href_between(current_html, target)
    return href_between(current_html, workspace_root / normalized)


def marker_href(
    marker: str,
    *,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> str:
    source_path = marker_target_path(marker, preview_data)
    if not source_path:
        return "#"
    href = html_target_for_source_path(
        source_path,
        current_html=current_html,
        workspace_root=workspace_root,
    )
    return href or "#"


def render_evidence_marker(
    match: re.Match[str],
    *,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> str:
    marker = f"{match.group(1)}:{match.group(2)}"
    href = marker_href(
        marker,
        preview_data=preview_data,
        current_html=current_html,
        workspace_root=workspace_root,
    )
    return (
        '<a class="evidence-marker" tabindex="0" '
        f'data-marker="{html.escape(marker, quote=True)}" '
        f'data-preview-id="{html.escape(marker, quote=True)}" '
        f'href="{html.escape(href, quote=True)}">'
        f"{match.group(0)}</a>"
    )


def render_inline(
    text: str,
    *,
    reference_mode: str = "project-evidence",
    preview_data: dict[str, Any] | None = None,
    current_html: Path | None = None,
    workspace_root: Path | None = None,
) -> str:
    preview_data = preview_data or {}
    pieces: list[str] = []
    for part in re.split(r"(`[^`]*`)", text):
        if part.startswith("`") and part.endswith("`"):
            pieces.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        escaped = html.escape(part)
        escaped = LINK_RE.sub(
            lambda match: (
                f'<a href="{html.escape(match.group(2), quote=True)}">'
                f"{match.group(1)}</a>"
            ),
            escaped,
        )
        escaped = MARKER_RE.sub(
            lambda match: render_evidence_marker(
                match,
                preview_data=preview_data,
                current_html=current_html,
                workspace_root=workspace_root,
            ),
            escaped,
        )
        if reference_mode == "workflow-handbook":
            escaped = WIKI_REF_RE.sub(
                lambda match: render_workflow_ref(
                    match,
                    preview_data=preview_data,
                    current_html=current_html,
                    workspace_root=workspace_root,
                ),
                escaped,
            )
        pieces.append(escaped)
    return "".join(pieces)


def render_workflow_ref(
    match: re.Match[str],
    *,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> str:
    ref = match.group(1).strip()
    label = match.group(2).strip() if match.group(2) else ref
    href = workflow_ref_target(ref, preview_data, current_html, workspace_root) or "#"
    return (
        '<a class="reference-marker" tabindex="0" '
        f'data-ref="{html.escape(ref, quote=True)}" '
        f'data-preview-id="{html.escape(ref, quote=True)}" '
        f'href="{html.escape(href, quote=True)}">'
        f"{html.escape(label)}</a>"
    )


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index] and bool(re.match(r"^\s*\|?[\s:-]+\|", lines[index + 1]))


def render_table(
    lines: list[str],
    start: int,
    *,
    reference_mode: str,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> tuple[str, int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and "|" in lines[index].strip():
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        rows.append(cells)
        index += 1
    if len(rows) >= 2:
        rows.pop(1)
    if not rows:
        return "", index
    head = rows[0]
    body = rows[1:]
    inline_kwargs = {
        "reference_mode": reference_mode,
        "preview_data": preview_data,
        "current_html": current_html,
        "workspace_root": workspace_root,
    }
    html_rows = [
        "<table><thead><tr>"
        + "".join(f"<th>{render_inline(cell, **inline_kwargs)}</th>" for cell in head)
        + "</tr></thead><tbody>"
    ]
    for row in body:
        cells = "".join(
            f"<td>{render_inline(cell, **inline_kwargs)}</td>"
            for cell in row
        )
        html_rows.append("<tr>" + cells + "</tr>")
    html_rows.append("</tbody></table>")
    return "\n".join(html_rows), index


def render_blockquote(
    lines: list[str],
    start: int,
    *,
    reference_mode: str,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> tuple[str, int]:
    quote_lines: list[str] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith(">"):
        quote_lines.append(lines[index].strip()[1:].lstrip())
        index += 1
    if not quote_lines:
        return "", index

    first = quote_lines[0].strip()
    callout_match = re.match(r"^\[!([A-Za-z0-9_-]+)\]\s*(.*)$", first)
    inner_markdown = "\n".join(quote_lines)
    if not callout_match:
        inner = render_markdown(
            inner_markdown,
            reference_mode=reference_mode,
            preview_data=preview_data,
            current_html=current_html,
            workspace_root=workspace_root,
        )
        return f"<blockquote>{inner}</blockquote>", index

    callout_kind = slugify(callout_match.group(1))
    title = callout_match.group(2).strip() or callout_match.group(1).title()
    body_markdown = "\n".join(quote_lines[1:]).strip()
    body = (
        render_markdown(
            body_markdown,
            reference_mode=reference_mode,
            preview_data=preview_data,
            current_html=current_html,
            workspace_root=workspace_root,
        )
        if body_markdown
        else ""
    )
    inline_title = render_inline(
        title,
        reference_mode=reference_mode,
        preview_data=preview_data,
        current_html=current_html,
        workspace_root=workspace_root,
    )
    return (
        f'<aside class="callout callout-{callout_kind}">'
        f'<p class="callout-title">{inline_title}</p>'
        f"{body}</aside>",
        index,
    )


def render_unordered_list(
    lines: list[str],
    start: int,
    *,
    reference_mode: str,
    preview_data: dict[str, Any],
    current_html: Path | None,
    workspace_root: Path | None,
) -> tuple[str, int]:
    items: list[str] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith(("- ", "* ")):
        item_parts = [lines[index].strip()[2:].strip()]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if (
                not next_line
                or next_line.startswith(("- ", "* "))
                or next_line.startswith("```")
                or next_line.startswith(">")
                or HEADING_RE.match(next_line)
                or is_table_start(lines, index)
            ):
                break
            item_parts.append(next_line)
            index += 1
        items.append(" ".join(item_parts))

    inline_kwargs = {
        "reference_mode": reference_mode,
        "preview_data": preview_data,
        "current_html": current_html,
        "workspace_root": workspace_root,
    }
    return (
        "<ul>"
        + "".join(f"<li>{render_inline(item, **inline_kwargs)}</li>" for item in items)
        + "</ul>",
        index,
    )


def render_markdown(
    markdown: str,
    *,
    reference_mode: str = "project-evidence",
    preview_data: dict[str, Any] | None = None,
    current_html: Path | None = None,
    workspace_root: Path | None = None,
) -> str:
    preview_data = preview_data or {}
    inline_kwargs = {
        "reference_mode": reference_mode,
        "preview_data": preview_data,
        "current_html": current_html,
        "workspace_root": workspace_root,
    }
    lines = markdown.splitlines()
    rendered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip() or "text"
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            language_class = slugify(language)
            block_kind = code_block_kind(language)
            block_class = f"code-block code-block-{block_kind}"
            escaped_language = html.escape(language)
            escaped_language_class = html.escape(language_class, quote=True)
            class_attr = (
                f' class="language-{escaped_language_class}"'
                if language
                else ""
            )
            rendered.append(
                f'<div class="{block_class}" data-language="{escaped_language_class}">'
                f'<div class="code-label">{escaped_language}</div>'
                f"<pre><code{class_attr}>"
                f"{html.escape(chr(10).join(code_lines))}</code></pre>"
                "</div>"
            )
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            rendered.append(
                f'<h{level} id="{slugify(text)}">'
                f"{render_inline(text, **inline_kwargs)}</h{level}>"
            )
            index += 1
            continue

        if is_table_start(lines, index):
            table_html, index = render_table(
                lines,
                index,
                reference_mode=reference_mode,
                preview_data=preview_data,
                current_html=current_html,
                workspace_root=workspace_root,
            )
            rendered.append(table_html)
            continue

        if stripped.startswith(">"):
            blockquote_html, index = render_blockquote(
                lines,
                index,
                reference_mode=reference_mode,
                preview_data=preview_data,
                current_html=current_html,
                workspace_root=workspace_root,
            )
            rendered.append(blockquote_html)
            continue

        if stripped.startswith(("- ", "* ")):
            list_html, index = render_unordered_list(
                lines,
                index,
                reference_mode=reference_mode,
                preview_data=preview_data,
                current_html=current_html,
                workspace_root=workspace_root,
            )
            rendered.append(list_html)
            continue

        paragraph: list[str] = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if (
                not next_line
                or next_line.startswith("```")
                or HEADING_RE.match(next_line)
                or next_line.startswith(("- ", "* "))
                or next_line.startswith(">")
                or is_table_start(lines, index)
            ):
                break
            paragraph.append(next_line)
            index += 1
        rendered.append(
            "<p>"
            + render_inline(
                " ".join(paragraph),
                reference_mode=reference_mode,
                preview_data=preview_data,
                current_html=current_html,
                workspace_root=workspace_root,
            )
            + "</p>"
        )
    return "\n".join(rendered)


def discover_markdown(source_root: Path, output_root: Path) -> list[Path]:
    excluded = {
        output_root.resolve(),
        (source_root / "_site").resolve(),
        (source_root / "_views").resolve(),
    }
    paths: list[Path] = []
    for path in source_root.rglob("*.md"):
        if any(
            path.resolve().is_relative_to(excluded_path) for excluded_path in excluded
        ):
            continue
        paths.append(path)
    return sorted(paths)


def href_between(from_path: Path, target_path: Path) -> str:
    return os.path.relpath(target_path, from_path.parent).replace(os.sep, "/")


def navigation_for(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for page in pages:
        source = Path(str(page["source_path"]))
        label = source.parent.as_posix()
        if label == ".":
            label = "Root"
        groups.setdefault(label, []).append(str(page["doc_id"]))
    return [
        {"label": label, "pages": pages_for_label}
        for label, pages_for_label in sorted(groups.items())
    ]


def load_nav_config(
    workspace_root: Path, nav_config_path: Path | None
) -> dict[str, Any] | None:
    if nav_config_path is None:
        return None
    path = workspace_root / nav_config_path
    if not path.exists():
        raise FileNotFoundError(f"navigation config not found: {nav_config_path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{nav_config_path} must contain a JSON object")
    return data


def flatten_nav_items(items: list[Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        flattened.append(item)
        children = item.get("children", [])
        if isinstance(children, list):
            flattened.extend(flatten_nav_items(children))
    return flattened


def nav_item_for_config(
    item: dict[str, Any],
    by_source: dict[str, str],
) -> dict[str, Any] | None:
    source_path = item.get("source_path")
    if not isinstance(source_path, str) or source_path not in by_source:
        return None
    children: list[dict[str, Any]] = []
    raw_children = item.get("children", [])
    if isinstance(raw_children, list):
        for child in raw_children:
            if isinstance(child, dict):
                rendered = nav_item_for_config(child, by_source)
                if rendered is not None:
                    children.append(rendered)
    return {
        "doc_id": by_source[source_path],
        "label": str(item.get("label", by_source[source_path])),
        "source_path": source_path,
        "children": children,
    }


def nav_doc_ids(items: list[dict[str, Any]]) -> list[str]:
    doc_ids: list[str] = []
    for item in items:
        doc_ids.append(str(item["doc_id"]))
        children = item.get("children", [])
        if isinstance(children, list):
            doc_ids.extend(nav_doc_ids(children))
    return doc_ids


def navigation_for_config(
    pages: list[dict[str, Any]],
    nav_config: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if nav_config is None:
        return navigation_for(pages)
    by_source = {str(page["source_path"]): str(page["doc_id"]) for page in pages}
    navigation: list[dict[str, Any]] = []
    sections = nav_config.get("sections", [])
    if not isinstance(sections, list):
        raise ValueError("navigation config sections must be a list")
    for section in sorted(
        [item for item in sections if isinstance(item, dict)],
        key=lambda item: int(item.get("position", 0)),
    ):
        nav_items: list[dict[str, Any]] = []
        for item in section.get("items", []):
            if not isinstance(item, dict):
                continue
            rendered = nav_item_for_config(item, by_source)
            if rendered is not None:
                nav_items.append(rendered)
        doc_ids = nav_doc_ids(nav_items)
        navigation.append(
            {
                "label": str(section.get("title", section.get("id", "Section"))),
                "pages": doc_ids,
                "section_id": section.get("id"),
                "items": nav_items,
            }
        )
    return navigation


def nav_item_contains_doc(item: dict[str, Any], current_doc_id: str | None) -> bool:
    if current_doc_id is None:
        return False
    if str(item.get("doc_id")) == current_doc_id:
        return True
    children = item.get("children", [])
    if not isinstance(children, list):
        return False
    return any(
        nav_item_contains_doc(child, current_doc_id)
        for child in children
        if isinstance(child, dict)
    )


def render_nav_item(
    item: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    current_doc_id: str | None,
    current_html: Path,
    workspace_root: Path,
) -> str:
    doc_id = str(item["doc_id"])
    page = by_id[doc_id]
    target = workspace_root / str(page["html_path"])
    css = ' class="active"' if doc_id == current_doc_id else ""
    href = html.escape(href_between(current_html, target), quote=True)
    label = html.escape(str(item.get("label") or page["title"]))
    link = f'<a{css} href="{href}">{label}</a>'
    children = item.get("children", [])
    if not isinstance(children, list) or not children:
        return link
    open_attr = " open" if nav_item_contains_doc(item, current_doc_id) else ""
    children_html = "".join(
        render_nav_item(child, by_id, current_doc_id, current_html, workspace_root)
        for child in children
        if isinstance(child, dict)
    )
    return (
        f'<details class="nav-folder"{open_attr}>'
        f"<summary>{link}</summary>"
        f'<div class="nav-children">{children_html}</div>'
        "</details>"
    )


def render_nav(
    pages: list[dict[str, Any]],
    navigation: list[dict[str, Any]],
    current_doc_id: str | None,
    current_html: Path,
    workspace_root: Path,
) -> str:
    by_id = {page["doc_id"]: page for page in pages}
    sections: list[str] = []
    for index, group in enumerate(navigation):
        section_open = current_doc_id in group["pages"] or (
            current_doc_id is None and index == 0
        )
        open_attr = " open" if section_open else ""
        items = group.get("items")
        if isinstance(items, list) and items:
            body = "".join(
                render_nav_item(
                    item,
                    by_id,
                    current_doc_id,
                    current_html,
                    workspace_root,
                )
                for item in items
                if isinstance(item, dict)
            )
        else:
            links: list[str] = []
            for doc_id in group["pages"]:
                page = by_id[doc_id]
                target = workspace_root / str(page["html_path"])
                css = ' class="active"' if doc_id == current_doc_id else ""
                href = html.escape(href_between(current_html, target), quote=True)
                links.append(
                    f'<a{css} href="{href}">{html.escape(str(page["title"]))}</a>'
                )
            body = "".join(links)
        sections.append(
            f'<details class="nav-section"{open_attr}>'
            f"<summary>{html.escape(str(group['label']))}</summary>"
            f'<div class="nav-section-body">{body}</div>'
            "</details>"
        )
    return "".join(sections)


def render_index_item(
    item: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    index_path: Path,
    workspace_root: Path,
) -> str:
    doc_id = str(item["doc_id"])
    page = by_id[doc_id]
    target = workspace_root / str(page["html_path"])
    href = html.escape(href_between(index_path, target), quote=True)
    label = html.escape(str(item.get("label") or page["title"]))
    link = f'<a href="{href}">{label}</a>'
    children = item.get("children", [])
    if not isinstance(children, list) or not children:
        return f"<li>{link}</li>"
    child_items = "".join(
        render_index_item(child, by_id, index_path, workspace_root)
        for child in children
        if isinstance(child, dict)
    )
    return (
        "<li>"
        f"<details><summary>{link}</summary><ul>{child_items}</ul></details>"
        "</li>"
    )


def render_index_body(
    *,
    site_title: str,
    pages: list[dict[str, Any]],
    navigation: list[dict[str, Any]],
    index_path: Path,
    workspace_root: Path,
) -> str:
    by_id = {str(page["doc_id"]): page for page in pages}
    sections: list[str] = []
    for group in navigation:
        items = group.get("items")
        if isinstance(items, list) and items:
            body = "".join(
                render_index_item(item, by_id, index_path, workspace_root)
                for item in items
                if isinstance(item, dict)
            )
        else:
            body = "".join(
                "<li>"
                + '<a href="'
                + html.escape(
                    href_between(
                        index_path,
                        workspace_root / str(by_id[doc_id]["html_path"]),
                    ),
                    quote=True,
                )
                + '">'
                + html.escape(str(by_id[doc_id]["title"]))
                + "</a></li>"
                for doc_id in group["pages"]
            )
        sections.append(
            f"<h2>{html.escape(str(group['label']))}</h2><ul>{body}</ul>"
        )
    return f"<h1>{html.escape(site_title)}</h1>{''.join(sections)}"


def homepage_doc_id(navigation: list[dict[str, Any]]) -> str | None:
    for group in navigation:
        pages = group.get("pages", [])
        if isinstance(pages, list) and pages:
            return str(pages[0])
    return None


def render_page_rail(headings: list[dict[str, Any]]) -> str:
    if not headings:
        return ""
    links: list[str] = []
    for heading in headings:
        level = int(heading.get("level", 2))
        text = str(heading.get("text", "Section"))
        slug = str(heading.get("slug", slugify(text)))
        css = "h3" if level == 3 else "h2"
        links.append(
            f'<a class="{css}" href="#{html.escape(slug, quote=True)}">'
            f"{html.escape(text)}</a>"
        )
    return '<nav class="page-rail"><strong>On this page</strong>' + "".join(
        links
    ) + "</nav>"


def page_html(
    *,
    title: str,
    body: str,
    headings: list[dict[str, Any]],
    source_path: str,
    status: str | None,
    nav_html: str,
    preview_data: dict[str, Any],
    site_title: str,
    style_href: str,
    script_href: str,
) -> str:
    preview_json = json.dumps(preview_data, ensure_ascii=False).replace("</", "<\\/")
    status_text = f"Status: {html.escape(status)} | " if status else ""
    page_rail = render_page_rail(headings)
    return (
        "<!doctype html>\n"
        '<html lang="zh-Hans">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{html.escape(title)} - {html.escape(site_title)}</title>\n"
        f'  <link rel="stylesheet" href="{html.escape(style_href, quote=True)}">\n'
        "</head>\n"
        "<body>\n"
        '<div class="layout">\n'
        '<aside class="sidebar"><div class="sidebar-header">'
        '<p class="site-eyebrow">Static handbook</p>'
        f"<h1>{html.escape(site_title)}</h1></div>{nav_html}</aside>\n"
        '<main class="content">\n'
        '<div class="content-inner">\n'
        f'<div class="doc-meta">{status_text}Source: '
        f"<code>{html.escape(source_path)}</code></div>\n"
        '<div class="page-grid">\n'
        f"<article>{body}</article>\n"
        f"{page_rail}\n"
        "</div>\n"
        "</div>\n"
        "</main>\n"
        "</div>\n"
        '<div class="evidence-popover" role="tooltip"></div>\n'
        '<script type="application/json" id="evidence-preview-data">'
        f"{preview_json}</script>\n"
        f'<script src="{html.escape(script_href, quote=True)}"></script>\n'
        "</body>\n"
        "</html>\n"
    )


def root_entry_html(*, site_title: str, target_href: str) -> str:
    safe_title = html.escape(site_title)
    safe_href = html.escape(target_href, quote=True)
    return (
        "<!doctype html>\n"
        '<html lang="zh-Hans">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'  <meta http-equiv="refresh" content="0; url={safe_href}">\n'
        f"  <title>{safe_title}</title>\n"
        "  <style>\n"
        "    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "
        '"Segoe UI", sans-serif; background: #f5f7fb; color: #2f3337; }\n'
        "    main { max-width: 720px; margin: 18vh auto; padding: 0 24px; }\n"
        "    a { color: #1f5f7a; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main>\n"
        f"    <h1>{safe_title}</h1>\n"
        "    <p>Opening the rendered handbook.</p>\n"
        f'    <p><a href="{safe_href}">Open {safe_title}</a></p>\n'
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def load_preview_index(
    workspace_root: Path,
    preview_index_path: Path,
) -> dict[str, Any]:
    path = workspace_root / preview_index_path
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{preview_index_path} must contain a JSON object")
    return data


def reset_output_root(output: Path, workspace: Path, source: Path) -> None:
    if output == workspace:
        raise ValueError("output root must not be the workspace root")
    if output == source:
        raise ValueError("output root must not be the source root")
    if not output.resolve().is_relative_to(workspace.resolve()):
        raise ValueError("output root must stay inside the workspace")
    if source.resolve().is_relative_to(output.resolve()):
        raise ValueError("output root must not contain the source root")
    if output.exists() and not output.is_dir():
        raise ValueError(
            f"output root is not a directory: {relpath(output, workspace)}"
        )
    if output.exists():
        shutil.rmtree(output)


def root_entry_path(output: Path) -> Path | None:
    if output.name == "_site" or output.parent.name != "_site":
        return None
    return output.parent / "index.html"


def build_docs_site(
    workspace_root: Path,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    preview_index_path: Path = DEFAULT_PREVIEW_INDEX,
    nav_config_path: Path | None = None,
    site_title: str = "Project Docs",
    reference_mode: str = "project-evidence",
    dry_run: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    source = (workspace / source_root).resolve()
    output = (workspace / output_root).resolve()
    if not source.exists():
        raise FileNotFoundError(f"source root not found: {relpath(source, workspace)}")
    if reference_mode not in {"project-evidence", "workflow-handbook"}:
        raise ValueError("reference_mode must be project-evidence or workflow-handbook")

    nav_config = load_nav_config(workspace, nav_config_path)
    preview_data = load_preview_index(workspace, preview_index_path)
    markdown_paths = discover_markdown(source, output)
    pages: list[dict[str, Any]] = []
    markdown_by_id: dict[str, str] = {}

    for path in markdown_paths:
        text = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        doc_id = doc_id_for(path, source)
        relative_source = path.relative_to(workspace).as_posix()
        html_relative = Path(output_root) / path.relative_to(source).with_suffix(
            ".html"
        )
        doc_kind = str(metadata.get("kind") or doc_kind_for(path, source))
        pages.append(
            {
                "doc_id": doc_id,
                "doc_kind": doc_kind,
                "title": str(
                    metadata.get("title")
                    or extract_title(body, path.stem.replace("_", " "))
                ),
                "source_path": relative_source,
                "html_path": html_relative.as_posix(),
                "status": metadata.get("status") or extract_status(body),
                "evidence_chain_path": None,
                "preview_index_path": (
                    preview_index_path.as_posix() if preview_data else None
                ),
                "related_pages": [],
                "page_id": metadata.get("page_id"),
                "page_kind": metadata.get("kind"),
                "source_type": metadata.get("source_type"),
                "summary": metadata.get("summary"),
                "references": metadata.get("references", []),
            }
        )
        markdown_by_id[doc_id] = body

    navigation = navigation_for_config(pages, nav_config)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source_root": Path(source_root).as_posix(),
        "output_root": Path(output_root).as_posix(),
        "site_title": site_title,
        "reference_mode": reference_mode,
        "nav_config_path": nav_config_path.as_posix() if nav_config_path else None,
        "pages": pages,
        "navigation": navigation,
    }

    if dry_run:
        return manifest

    reset_output_root(output, workspace, source)
    assets = output / "assets"
    atomic_write_text(assets / "site.css", STYLE_CSS + "\n")
    atomic_write_text(assets / "evidence-preview.js", PREVIEW_JS + "\n")
    atomic_write_json(output / MANIFEST_NAME, manifest)

    for page in pages:
        html_path = workspace / str(page["html_path"])
        nav_html = render_nav(
            pages,
            navigation,
            str(page["doc_id"]),
            html_path,
            workspace,
        )
        style_href = href_between(html_path, assets / "site.css")
        script_href = href_between(html_path, assets / "evidence-preview.js")
        page_text = page_html(
            title=str(page["title"]),
            body=render_markdown(
                markdown_by_id[str(page["doc_id"])],
                reference_mode=reference_mode,
                preview_data=preview_data,
                current_html=html_path,
                workspace_root=workspace,
            ),
            headings=extract_page_headings(markdown_by_id[str(page["doc_id"])]),
            source_path=str(page["source_path"]),
            status=page.get("status"),
            nav_html=nav_html,
            preview_data=preview_data,
            site_title=site_title,
            style_href=style_href,
            script_href=script_href,
        )
        atomic_write_text(html_path, page_text)

    index_path = output / "index.html"
    pages_by_id = {str(page["doc_id"]): page for page in pages}
    home_doc_id = homepage_doc_id(navigation)
    if home_doc_id and home_doc_id in markdown_by_id and home_doc_id in pages_by_id:
        home_page = pages_by_id[home_doc_id]
        index_markdown = markdown_by_id[home_doc_id]
        index_body = render_markdown(
            index_markdown,
            reference_mode=reference_mode,
            preview_data=preview_data,
            current_html=index_path,
            workspace_root=workspace,
        )
        index_title = str(home_page["title"])
        index_source = str(home_page["source_path"])
        index_status = home_page.get("status")
        index_nav_doc_id: str | None = home_doc_id
    else:
        index_body = render_index_body(
            site_title=site_title,
            pages=pages,
            navigation=navigation,
            index_path=index_path,
            workspace_root=workspace,
        )
        index_title = "Index"
        index_source = Path(source_root).as_posix()
        index_status = None
        index_nav_doc_id = None
        index_markdown = ""
    index_html = page_html(
        title=index_title,
        body=index_body,
        headings=extract_page_headings(index_markdown),
        source_path=index_source,
        status=index_status,
        nav_html=render_nav(pages, navigation, index_nav_doc_id, index_path, workspace),
        preview_data=preview_data,
        site_title=site_title,
        style_href=href_between(index_path, assets / "site.css"),
        script_href=href_between(index_path, assets / "evidence-preview.js"),
    )
    atomic_write_text(index_path, index_html)
    root_index_path = root_entry_path(output)
    if root_index_path is not None:
        atomic_write_text(
            root_index_path,
            root_entry_html(
                site_title=site_title,
                target_href=href_between(root_index_path, index_path),
            ),
        )
    return manifest


def docs_site_summary(
    manifest: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    output_root = str(manifest.get("output_root") or "")
    manifest_path = (Path(output_root) / MANIFEST_NAME).as_posix()
    return {
        "ok": True,
        "manifest": manifest_path,
        "dry_run": dry_run,
        "source_root": manifest.get("source_root"),
        "output_root": manifest.get("output_root"),
        "reference_mode": manifest.get("reference_mode"),
        "page_count": len(manifest.get("pages", [])),
        "navigation_group_count": len(manifest.get("navigation", [])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render source Markdown docs into docs/_site HTML."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--preview-index", type=Path, default=DEFAULT_PREVIEW_INDEX)
    parser.add_argument("--nav-config", type=Path)
    parser.add_argument("--site-title", default="Project Docs")
    parser.add_argument(
        "--reference-mode",
        choices=["project-evidence", "workflow-handbook"],
        default="project-evidence",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--json-full",
        action="store_true",
        help=(
            "Print the full generated docs-site manifest instead of a concise "
            "summary."
        ),
    )
    args = parser.parse_args(argv)

    try:
        manifest = build_docs_site(
            args.workspace_root,
            source_root=args.source_root,
            output_root=args.output_root,
            preview_index_path=args.preview_index,
            nav_config_path=args.nav_config,
            site_title=args.site_title,
            reference_mode=args.reference_mode,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json_full:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    elif args.json:
        print(
            json.dumps(
                docs_site_summary(manifest, dry_run=args.dry_run),
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"PASS {Path(args.output_root) / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
