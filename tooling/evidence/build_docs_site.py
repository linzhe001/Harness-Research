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

SCHEMA_VERSION = "0.1"
DEFAULT_SOURCE_ROOT = Path("docs")
DEFAULT_OUTPUT_ROOT = Path("docs/_site")
DEFAULT_PREVIEW_INDEX = Path("docs/_views/evidence_preview_index.json")
MANIFEST_NAME = "manifest.json"
MARKER_RE = re.compile(r"\[(F|U|E):([A-Za-z0-9_.:-]+)\]")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STATUS_RE = re.compile(r"^Status:\s*(.+?)\s*$", re.IGNORECASE)

STYLE_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f8fa;
  --panel: #ffffff;
  --text: #17202a;
  --muted: #5d6b7a;
  --line: #d9dee6;
  --accent: #0f766e;
  --accent-soft: #dff4f0;
  --code: #111827;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  min-height: 100vh;
}
.sidebar {
  border-right: 1px solid var(--line);
  background: #eef2f6;
  padding: 24px 18px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}
.sidebar h1 {
  font-size: 18px;
  line-height: 1.25;
  margin: 0 0 18px;
}
.nav-section { margin: 18px 0; }
.nav-section h2 {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  margin: 0 0 8px;
  text-transform: uppercase;
}
.nav-section a {
  display: block;
  border-radius: 6px;
  color: var(--text);
  font-size: 14px;
  line-height: 1.35;
  padding: 7px 8px;
}
.nav-section a.active,
.nav-section a:hover {
  background: var(--panel);
  text-decoration: none;
}
.content {
  max-width: 980px;
  width: 100%;
  padding: 36px 48px 72px;
}
.doc-meta {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 22px;
}
article {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 32px;
}
article h1, article h2, article h3 { line-height: 1.25; }
article h1 { font-size: 32px; margin-top: 0; }
article h2 { border-top: 1px solid var(--line); margin-top: 32px; padding-top: 24px; }
article p, article li { line-height: 1.65; }
pre {
  background: var(--code);
  border-radius: 6px;
  color: #f9fafb;
  overflow: auto;
  padding: 14px;
}
code {
  background: #edf0f4;
  border-radius: 4px;
  padding: 1px 4px;
}
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; display: block; overflow-x: auto; width: 100%; }
th, td { border: 1px solid var(--line); padding: 8px 10px; vertical-align: top; }
th { background: #f1f4f8; text-align: left; }
.evidence-marker {
  background: var(--accent-soft);
  border: 1px solid #9bd5cb;
  border-radius: 999px;
  color: #075e55;
  cursor: help;
  display: inline-block;
  font-size: 0.86em;
  margin: 0 2px;
  padding: 0 6px;
}
.evidence-popover {
  background: #101820;
  border-radius: 8px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.2);
  color: #f8fafc;
  display: none;
  max-width: min(440px, calc(100vw - 32px));
  padding: 12px 14px;
  position: fixed;
  z-index: 20;
}
.evidence-popover strong { display: block; margin-bottom: 6px; }
.evidence-popover p { margin: 6px 0; }
.evidence-popover .muted { color: #bfccd9; font-size: 12px; }
@media (max-width: 800px) {
  .layout { display: block; }
  .sidebar { height: auto; position: static; }
  .content { padding: 20px 14px 48px; }
  article { padding: 22px 18px; }
}
""".strip()

PREVIEW_JS = """
(function () {
  const dataEl = document.getElementById("evidence-preview-data");
  const popover = document.querySelector(".evidence-popover");
  if (!dataEl || !popover) return;

  let previews = {};
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

  function show(event) {
    const marker = event.currentTarget.getAttribute("data-marker");
    const preview = previewFor(marker);
    if (!preview) return;
    popover.innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = preview.title || marker;
    const excerpt = document.createElement("p");
    excerpt.textContent = preview.excerpt || "No excerpt recorded.";
    const meta = document.createElement("p");
    meta.className = "muted";
    meta.textContent = [preview.path, preview.support_relation]
      .filter(Boolean)
      .join(" | ");
    popover.append(title, excerpt, meta);
    popover.style.display = "block";
    const rect = event.currentTarget.getBoundingClientRect();
    const left = Math.min(rect.left, window.innerWidth - popover.offsetWidth - 16);
    const top = Math.min(
      rect.bottom + 8,
      window.innerHeight - popover.offsetHeight - 16
    );
    popover.style.left = Math.max(16, left) + "px";
    popover.style.top = Math.max(16, top) + "px";
  }

  function hide() {
    popover.style.display = "none";
  }

  document.querySelectorAll(".evidence-marker").forEach((el) => {
    el.addEventListener("mouseenter", show);
    el.addEventListener("focus", show);
    el.addEventListener("mouseleave", hide);
    el.addEventListener("blur", hide);
  });
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


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return fallback


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


def render_inline(text: str) -> str:
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
            lambda match: (
                '<span class="evidence-marker" tabindex="0" '
                f'data-marker="{match.group(1)}:{match.group(2)}">'
                f"{match.group(0)}</span>"
            ),
            escaped,
        )
        pieces.append(escaped)
    return "".join(pieces)


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index] and bool(re.match(r"^\s*\|?[\s:-]+\|", lines[index + 1]))


def render_table(lines: list[str], start: int) -> tuple[str, int]:
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
    html_rows = [
        "<table><thead><tr>"
        + "".join(f"<th>{render_inline(cell)}</th>" for cell in head)
        + "</tr></thead><tbody>"
    ]
    for row in body:
        cells = "".join(f"<td>{render_inline(cell)}</td>" for cell in row)
        html_rows.append(
            "<tr>" + cells + "</tr>"
        )
    html_rows.append("</tbody></table>")
    return "\n".join(html_rows), index


def render_markdown(markdown: str) -> str:
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
            language = stripped[3:].strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            class_attr = (
                f' class="language-{html.escape(language, quote=True)}"'
                if language
                else ""
            )
            rendered.append(
                f"<pre><code{class_attr}>"
                f"{html.escape(chr(10).join(code_lines))}</code></pre>"
            )
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            rendered.append(
                f'<h{level} id="{slugify(text)}">{render_inline(text)}</h{level}>'
            )
            index += 1
            continue

        if is_table_start(lines, index):
            table_html, index = render_table(lines, index)
            rendered.append(table_html)
            continue

        if stripped.startswith(("- ", "* ")):
            items: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(("- ", "* ")):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            rendered.append(
                "<ul>"
                + "".join(f"<li>{render_inline(item)}</li>" for item in items)
                + "</ul>"
            )
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
                or is_table_start(lines, index)
            ):
                break
            paragraph.append(next_line)
            index += 1
        rendered.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
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
            path.resolve().is_relative_to(excluded_path)
            for excluded_path in excluded
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


def render_nav(
    pages: list[dict[str, Any]],
    navigation: list[dict[str, Any]],
    current_doc_id: str | None,
    current_html: Path,
    workspace_root: Path,
) -> str:
    by_id = {page["doc_id"]: page for page in pages}
    sections: list[str] = []
    for group in navigation:
        links: list[str] = [f"<h2>{html.escape(str(group['label']))}</h2>"]
        for doc_id in group["pages"]:
            page = by_id[doc_id]
            target = workspace_root / str(page["html_path"])
            css = ' class="active"' if doc_id == current_doc_id else ""
            href = html.escape(href_between(current_html, target), quote=True)
            links.append(
                f'<a{css} href="{href}">{html.escape(str(page["title"]))}</a>'
            )
        sections.append(f'<div class="nav-section">{"".join(links)}</div>')
    return "".join(sections)


def page_html(
    *,
    title: str,
    body: str,
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
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{html.escape(title)} - {html.escape(site_title)}</title>\n"
        f'  <link rel="stylesheet" href="{html.escape(style_href, quote=True)}">\n'
        "</head>\n"
        "<body>\n"
        '<div class="layout">\n'
        f'<aside class="sidebar"><h1>{html.escape(site_title)}</h1>{nav_html}</aside>\n'
        '<main class="content">\n'
        f'<div class="doc-meta">{status_text}Source: '
        f"<code>{html.escape(source_path)}</code></div>\n"
        f"<article>{body}</article>\n"
        "</main>\n"
        "</div>\n"
        '<div class="evidence-popover" role="tooltip"></div>\n'
        '<script type="application/json" id="evidence-preview-data">'
        f"{preview_json}</script>\n"
        f'<script src="{html.escape(script_href, quote=True)}"></script>\n'
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


def build_docs_site(
    workspace_root: Path,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    preview_index_path: Path = DEFAULT_PREVIEW_INDEX,
    dry_run: bool = False,
) -> dict[str, Any]:
    workspace = workspace_root.resolve()
    source = (workspace / source_root).resolve()
    output = (workspace / output_root).resolve()
    if not source.exists():
        raise FileNotFoundError(f"source root not found: {relpath(source, workspace)}")

    preview_data = load_preview_index(workspace, preview_index_path)
    markdown_paths = discover_markdown(source, output)
    pages: list[dict[str, Any]] = []
    markdown_by_id: dict[str, str] = {}

    for path in markdown_paths:
        text = path.read_text(encoding="utf-8")
        doc_id = doc_id_for(path, source)
        relative_source = path.relative_to(workspace).as_posix()
        html_relative = (
            Path(output_root) / path.relative_to(source).with_suffix(".html")
        )
        pages.append(
            {
                "doc_id": doc_id,
                "doc_kind": doc_kind_for(path, source),
                "title": extract_title(text, path.stem.replace("_", " ")),
                "source_path": relative_source,
                "html_path": html_relative.as_posix(),
                "status": extract_status(text),
                "evidence_chain_path": None,
                "preview_index_path": (
                    preview_index_path.as_posix() if preview_data else None
                ),
                "related_pages": [],
            }
        )
        markdown_by_id[doc_id] = text

    navigation = navigation_for(pages)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source_root": Path(source_root).as_posix(),
        "output_root": Path(output_root).as_posix(),
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
            body=render_markdown(markdown_by_id[str(page["doc_id"])]),
            source_path=str(page["source_path"]),
            status=page.get("status"),
            nav_html=nav_html,
            preview_data=preview_data,
            site_title="Project Docs",
            style_href=style_href,
            script_href=script_href,
        )
        atomic_write_text(html_path, page_text)

    index_path = output / "index.html"
    index_items = "".join(
        '<li><a href="'
        + html.escape(
            href_between(index_path, workspace / str(page["html_path"])),
            quote=True,
        )
        + '">'
        f"{html.escape(str(page['title']))}</a></li>"
        for page in pages
    )
    index_html = page_html(
        title="Index",
        body=f"<h1>Project Docs</h1><ul>{index_items}</ul>",
        source_path=Path(source_root).as_posix(),
        status=None,
        nav_html=render_nav(pages, navigation, None, index_path, workspace),
        preview_data=preview_data,
        site_title="Project Docs",
        style_href=href_between(index_path, assets / "site.css"),
        script_href=href_between(index_path, assets / "evidence-preview.js"),
    )
    atomic_write_text(index_path, index_html)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render source Markdown docs into docs/_site HTML."
    )
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--preview-index", type=Path, default=DEFAULT_PREVIEW_INDEX)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = build_docs_site(
            args.workspace_root,
            source_root=args.source_root,
            output_root=args.output_root,
            preview_index_path=args.preview_index,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        print(f"PASS {Path(args.output_root) / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
