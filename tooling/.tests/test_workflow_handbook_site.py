from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "codex_hooks"))

import generate_stage_cards  # noqa: E402


def load_evidence_tool(name: str):
    path = REPO_ROOT / "tooling" / "evidence" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_workflow_handbook_schema_files_parse() -> None:
    for schema_path in [
        REPO_ROOT / "schemas" / "workflow_handbook_page.schema.json",
        REPO_ROOT / "schemas" / "workflow_handbook_nav.schema.json",
        REPO_ROOT / "schemas" / "workflow_handbook_reference_index.schema.json",
    ]:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert data["type"] == "object"
        assert data["required"]


def test_workflow_handbook_validator_accepts_current_sources() -> None:
    validator = load_evidence_tool("validate_workflow_handbook")

    assert validator.validate_workflow_handbook(REPO_ROOT) == []


def test_render_markdown_classifies_code_blocks_by_language() -> None:
    site_builder = load_evidence_tool("build_docs_site")

    rendered = site_builder.render_markdown(
        "> [!TIP] Reading path\n"
        "> Start with the visible alias.\n\n"
        "- Read the current source artifacts,\n"
        "  then run the owning tool.\n\n"
        "```text\n"
        "workflow -> gate\n"
        "```\n\n"
        "```bash\n"
        "python -m pytest\n"
        "```\n\n"
        "```json\n"
        '{"ok": true}\n'
        "```\n\n"
        "```python\n"
        "print('ok')\n"
        "```\n"
    )

    assert '<aside class="callout callout-tip">' in rendered
    assert '<p class="callout-title">Reading path</p>' in rendered
    assert (
        "<li>Read the current source artifacts, then run the owning tool.</li>"
        in rendered
    )
    assert 'class="code-block code-block-diagram" data-language="text"' in rendered
    assert 'class="code-block code-block-terminal" data-language="bash"' in rendered
    assert 'class="code-block code-block-data" data-language="json"' in rendered
    assert 'class="code-block code-block-source" data-language="python"' in rendered
    assert 'class="language-python"' in rendered


def test_generated_stage_and_skill_pages_match_contracts() -> None:
    expected = {}
    expected.update(generate_stage_cards.render_skill_pages(REPO_ROOT))
    expected.update(generate_stage_cards.render_stage_pages(REPO_ROOT))

    for relative_path, rendered in expected.items():
        path = REPO_ROOT / "workflow_handbook" / relative_path
        assert path.exists()
        assert path.read_text(encoding="utf-8") == rendered


def test_reference_index_resolves_handbook_markers() -> None:
    builder = load_evidence_tool("build_workflow_handbook_reference_index")

    index = builder.build_reference_index(REPO_ROOT)
    errors = builder.validate_reference_index(REPO_ROOT, index)

    assert errors == []
    assert "skill:docs-site" in index["entries"]
    assert "stage:WF10" in index["entries"]
    assert "page:stage_cards" in index["entries"]
    assert "page:markdown_to_html_preview_chain" in index["entries"]
    assert all(
        link["status"] == "resolved"
        for links in index["links_by_doc"].values()
        for link in links
    )


def test_reference_index_cli_json_is_concise(capsys) -> None:
    builder = load_evidence_tool("build_workflow_handbook_reference_index")

    code = builder.main(
        [
            "--workspace-root",
            str(REPO_ROOT),
            "--dry-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["entry_count"] > 0
    assert "entries" not in payload
    assert len(json.dumps(payload)) < 500


def test_reference_index_cli_json_full_keeps_manifest(capsys) -> None:
    builder = load_evidence_tool("build_workflow_handbook_reference_index")

    code = builder.main(
        [
            "--workspace-root",
            str(REPO_ROOT),
            "--dry-run",
            "--json-full",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert "entries" in payload
    assert "links_by_doc" in payload


def test_docs_site_cli_json_is_concise(tmp_path: Path, capsys) -> None:
    site_builder = load_evidence_tool("build_docs_site")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Index.md").write_text("# Index\n\nBody.\n", encoding="utf-8")

    code = site_builder.main(
        [
            "--workspace-root",
            str(tmp_path),
            "--source-root",
            "docs",
            "--output-root",
            "docs/_site",
            "--dry-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["ok"] is True
    assert payload["page_count"] == 1
    assert "pages" not in payload
    assert len(json.dumps(payload)) < 500


def test_docs_site_cli_json_full_keeps_manifest(tmp_path: Path, capsys) -> None:
    site_builder = load_evidence_tool("build_docs_site")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Index.md").write_text("# Index\n\nBody.\n", encoding="utf-8")

    code = site_builder.main(
        [
            "--workspace-root",
            str(tmp_path),
            "--source-root",
            "docs",
            "--output-root",
            "docs/_site",
            "--dry-run",
            "--json-full",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["pages"][0]["source_path"] == "docs/Index.md"


def test_codebase_title_uses_metadata_or_fallback(tmp_path: Path) -> None:
    site_builder = load_evidence_tool("build_docs_site")

    assert site_builder.codebase_title_for(tmp_path) == "harness research"

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample-codebase"\n',
        encoding="utf-8",
    )

    assert site_builder.codebase_title_for(tmp_path) == "sample-codebase"


def test_docs_site_renders_workflow_handbook_references(tmp_path: Path) -> None:
    builder = load_evidence_tool("build_workflow_handbook_reference_index")
    site_builder = load_evidence_tool("build_docs_site")

    shutil.copytree(REPO_ROOT / "workflow_handbook", tmp_path / "workflow_handbook")
    preview_path = (
        tmp_path / "docs" / "_views" / "workflow_handbook_reference_index.json"
    )
    preview_path.parent.mkdir(parents=True)
    preview_path.write_text(
        json.dumps(builder.build_reference_index(REPO_ROOT), indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = site_builder.build_docs_site(
        tmp_path,
        source_root=Path("workflow_handbook"),
        output_root=Path("docs/_site/workflow_handbook"),
        preview_index_path=Path("docs/_views/workflow_handbook_reference_index.json"),
        nav_config_path=Path("workflow_handbook/config/navigation.json"),
        site_title="Harness Workflow Handbook",
        reference_mode="workflow-handbook",
    )

    html_path = (
        tmp_path
        / "docs"
        / "_site"
        / "workflow_handbook"
        / "pages"
        / "04_markdown_to_html_preview_chain.html"
    )
    html = html_path.read_text(encoding="utf-8")
    stage_cards_html = (
        tmp_path / "docs" / "_site" / "workflow_handbook" / "Workflow_Stage_Cards.html"
    ).read_text(encoding="utf-8")
    layers_html = (
        tmp_path
        / "docs"
        / "_site"
        / "workflow_handbook"
        / "pages"
        / "workflow_layers.html"
    ).read_text(encoding="utf-8")
    index_html = (
        tmp_path / "docs" / "_site" / "workflow_handbook" / "index.html"
    ).read_text(encoding="utf-8")
    handbook_html = (
        tmp_path
        / "docs"
        / "_site"
        / "workflow_handbook"
        / "Workflow_Operator_Handbook.html"
    ).read_text(encoding="utf-8")
    codebase_html = (
        tmp_path
        / "docs"
        / "_site"
        / "workflow_handbook"
        / "pages"
        / "codebase.html"
    ).read_text(encoding="utf-8")
    cli_html = (
        tmp_path / "docs" / "_site" / "workflow_handbook" / "pages" / "cli.html"
    ).read_text(encoding="utf-8")
    codebase_shell = codebase_html.split(
        '<script type="application/json" id="evidence-preview-data">',
        1,
    )[0]
    cli_shell = cli_html.split(
        '<script type="application/json" id="evidence-preview-data">',
        1,
    )[0]
    root_index_html = (tmp_path / "docs" / "_site" / "index.html").read_text(
        encoding="utf-8"
    )
    css = (
        tmp_path / "docs" / "_site" / "workflow_handbook" / "assets" / "site.css"
    ).read_text(encoding="utf-8")
    js = (
        tmp_path
        / "docs"
        / "_site"
        / "workflow_handbook"
        / "assets"
        / "evidence-preview.js"
    ).read_text(encoding="utf-8")

    assert manifest["reference_mode"] == "workflow-handbook"
    assert manifest["site_title"] == "Harness Workflow Handbook"
    assert manifest["codebase_title"] == "harness research"
    assert [item["label"] for item in manifest["topbar"]] == [
        "Overview",
        "Codebase",
        "CLI",
        "Handbook",
    ]
    assert manifest["navigation"][1]["label"] == "Operate"
    assert manifest["navigation"][1]["items"][0]["label"] == "Action Index"
    assert manifest["navigation"][1]["items"][1]["label"] == "Runtime Routing"
    assert manifest["navigation"][1]["items"][1]["children"]
    assert [
        child["label"] for child in manifest["navigation"][1]["items"][1]["children"]
    ] == ["grill contract", "workflow-supervisor runtime"]
    assert manifest["navigation"][2]["label"] == "Detailed Reference"
    assert [
        item["label"] for item in manifest["navigation"][2]["items"][:4]
    ] == [
        "Detailed Workflow Map",
        "Research Supervision Assets",
        "Stage Reference",
        "Skill Reference",
    ]
    assert 'href="assets/site.css"' in index_html
    assert 'src="assets/evidence-preview.js"' in index_html
    assert '<body class="has-topbar">' in index_html
    assert '<nav class="topbar" aria-label="Primary">' in index_html
    assert (
        '<a class="topbar-brand" href="index.html">harness research</a>'
        in index_html
    )
    assert '<a class="active" href="index.html">Overview</a>' in index_html
    assert '<a href="pages/codebase.html">Codebase</a>' in index_html
    assert '<a href="pages/cli.html">CLI</a>' in index_html
    assert '<a href="Workflow_Operator_Handbook.html">Handbook</a>' in index_html
    assert '<p class="site-eyebrow">Section</p><h1>Overview</h1>' in index_html
    assert '<nav class="section-nav" aria-label="Sections">' in index_html
    assert '<details class="nav-section"' not in index_html
    assert '<nav class="topbar" aria-label="Primary">' in html
    assert '<a href="../index.html">Overview</a>' in html
    assert '<a href="codebase.html">Codebase</a>' in html
    assert '<a href="cli.html">CLI</a>' in html
    handbook_link = (
        '<a class="active" href="../Workflow_Operator_Handbook.html">Handbook</a>'
    )
    assert handbook_link in html
    assert '<details class="nav-section" open>' in handbook_html
    assert 'class="nav-folder"' in handbook_html
    assert "<title>Overview - Harness Workflow Handbook</title>" in index_html
    assert "<title>Workflow Operator Handbook - Harness Workflow Handbook</title>" in (
        handbook_html
    )
    assert (
        "Source: <code>workflow_handbook/Workflow_Operator_Handbook.md</code>"
        in handbook_html
    )
    assert "Source: <code>workflow_handbook/pages/overview.md</code>" in index_html
    assert '<h2 id="start-here">Start Here</h2>' in index_html
    assert '<h2 id="mental-model">Mental Model</h2>' in index_html
    assert '<h2 id="quick-action-index">Quick Action Index</h2>' in handbook_html
    assert '<h2 id="visible-aliases">Visible Aliases</h2>' in handbook_html
    assert '<aside class="callout callout-tip">' in handbook_html
    assert '<nav class="page-rail"><strong>On this page</strong>' in index_html
    assert 'href="#start-here"' in index_html
    assert 'content="0; url=workflow_handbook/index.html"' in root_index_html
    assert 'href="workflow_handbook/index.html"' in root_index_html
    assert "Opening the rendered handbook." in root_index_html
    assert 'href="Workflow_Stage_Cards.html"' in handbook_html
    assert "Operate" in handbook_html
    assert "Action Index" in handbook_html
    assert "Runtime Routing" in handbook_html
    assert "Detailed Reference" in handbook_html
    assert "Stage Reference" in handbook_html
    assert "Codebase" in index_html
    assert "Detailed Reference" not in codebase_shell
    assert "Stage Reference" not in codebase_shell
    assert "Detailed Reference" not in cli_shell
    assert "Stage Reference" not in cli_shell
    assert 'class="web-terminal" data-terminal' in cli_html
    assert 'data-terminal-current' in cli_html
    assert 'data-terminal-output' in cli_html
    assert 'data-terminal-data' in cli_html
    assert "tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json" in (
        cli_html
    )
    assert "Static example output, not Gate Evidence" in cli_html
    assert "Workflow Details" not in index_html
    assert "Stage Details" not in index_html
    assert "Run The Workflow" not in index_html
    assert "Detailed Workflow Map" in handbook_html
    assert "<summary>Maintenance</summary>" not in handbook_html
    assert 'href="plans/HTML_Rendering_Handbook_Plan.html"' not in handbook_html
    assert 'href="../assets/site.css"' in html
    assert 'src="../assets/evidence-preview.js"' in html
    assert 'data-ref="skill:docs-site"' in html
    assert 'data-preview-id="skill:docs-site"' in html
    assert 'href="../skills/docs-site.html"' in html
    assert '<h2 id="explore">Explore</h2>' in stage_cards_html
    assert '<h2 id="contract-plan">Contract &amp; Plan</h2>' in stage_cards_html
    assert '<h3 id="wf12-release">WF12 Release</h3>' in stage_cards_html
    assert 'data-ref="term:Gate Evidence"' in layers_html
    assert 'href="workflow_terms.html#gate-evidence"' in layers_html
    assert "workflow_handbook/pages/codebase.md" in codebase_html
    assert "workflow_handbook/pages/cli.md" in cli_html
    assert "Harness Workflow Handbook" in html
    assert "harness research" in html
    assert "grid-template-columns: minmax(248px, 280px) minmax(0, 1fr)" in css
    assert ".topbar" in css
    assert ".topbar-links a.active" in css
    assert ".section-nav" in css
    assert "body.has-topbar .layout" in css
    assert "body.has-topbar .sidebar" in css
    assert ".content-inner" in css
    assert ".page-grid" in css
    assert ".page-rail" in css
    assert ".callout" in css
    assert ".nav-folder" in css
    assert ".code-block" in css
    assert ".code-label" in css
    assert ".code-block-diagram" in css
    assert ".code-block-terminal" in css
    assert ".code-block-data" in css
    assert ".code-block-source" in css
    assert ".web-terminal" in css
    assert ".terminal-shell" in css
    assert ".terminal-command-list" in css
    assert ".terminal-screen" in css
    assert "[data-terminal]" in js
    assert "navigator.clipboard.writeText" in js
    assert "letter-spacing: 0" in css
    assert "--font-mono: ui-monospace" in css
    assert '"Cascadia Mono"' in css
    assert "font-family: var(--font-mono)" in css
    assert "font-variant-ligatures: none" in css
    assert ".code-block pre code" in css
    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 860px)" in css
    assert "max-height: 48vh" in css
    assert "overflow-wrap: anywhere" in css
