#!/usr/bin/env python3
"""Build targeted repository review prompts.

DeepSeek chat completion calls cannot read the workspace by themselves. This
builder packages the smallest useful local context for external review by
default, with an explicit full-repository mode only when the operator asks for
that higher-cost tradeoff.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from redaction import denied_review_path_reason, redact_secrets


class ReviewPromptError(RuntimeError):
    """Review prompt generation failed."""


DYNAMIC_MARKER = "# Dynamic Review Suffix"
REVIEW_SCOPES = ("changed", "full")
DEFAULT_MAX_FILE_BYTES = 200_000


@dataclass(frozen=True)
class GitReviewState:
    """Current Git state needed for a review prompt."""

    snapshot_ref: str
    head_files: tuple[str, ...]
    changed_files: tuple[str, ...]
    omitted_changed_files: tuple[str, ...]
    untracked_files: tuple[str, ...]
    status_short: str
    diff_from_snapshot: str


def build_review_prompt(
    *,
    workspace_root: Path,
    task: str,
    scope: str = "changed",
    snapshot_ref: str = "HEAD",
    include_paths: tuple[str, ...] = (),
    exclude_paths: tuple[str, ...] = (),
    context_files: tuple[str, ...] = (),
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    include_untracked_content: bool = False,
    include_untracked_paths: tuple[str, ...] = (),
) -> str:
    """Return a targeted repository review prompt."""
    root = workspace_root.resolve()
    if scope not in REVIEW_SCOPES:
        raise ReviewPromptError(f"scope must be one of: {', '.join(REVIEW_SCOPES)}")
    if max_file_bytes <= 0:
        raise ReviewPromptError("max_file_bytes must be positive")
    state = collect_git_review_state(
        root,
        snapshot_ref=snapshot_ref,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        include_untracked_paths=include_untracked_paths,
    )
    sections = [
        _review_header(scope),
        _format_scope_summary(
            state,
            scope=scope,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
            context_files=context_files,
            max_file_bytes=max_file_bytes,
        ),
    ]
    if scope == "full":
        sections.append(
            _format_head_snapshot(
                root,
                state.snapshot_ref,
                state.head_files,
                max_file_bytes=max_file_bytes,
            )
        )
    sections.extend([
        DYNAMIC_MARKER,
        _format_review_task(task),
        _format_git_state(state),
        _format_changed_worktree_files(
            root,
            state.changed_files,
            max_file_bytes=max_file_bytes,
        ),
        _format_context_files(
            root,
            context_files,
            max_file_bytes=max_file_bytes,
        ),
        _format_untracked_files(
            root,
            state.untracked_files,
            include_content=include_untracked_content,
            include_paths=include_untracked_paths,
            max_file_bytes=max_file_bytes,
        ),
    ])
    return "\n\n".join(section.rstrip() for section in sections if section) + "\n"


def collect_git_review_state(
    root: Path,
    *,
    snapshot_ref: str = "HEAD",
    include_paths: tuple[str, ...] = (),
    exclude_paths: tuple[str, ...] = (),
    include_untracked_paths: tuple[str, ...] = (),
) -> GitReviewState:
    """Collect deterministic repository state for prompt generation."""
    _require_git_worktree(root)
    resolved_ref = _resolve_snapshot_ref(root, snapshot_ref)
    all_changed_files = _changed_paths_from_snapshot(root, resolved_ref)
    reviewable_changed_files, denied_changed_files = _filter_reviewable_paths(
        all_changed_files
    )
    selected_changed_files = _filter_paths(
        reviewable_changed_files,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
    )
    selected_changed_set = set(selected_changed_files)
    omitted_changed_files = tuple(
        path
        for path in (*denied_changed_files, *reviewable_changed_files)
        if path not in selected_changed_set
    )
    head_files, _denied_head_files = _filter_reviewable_paths(
        tuple(
            sorted(_git_z(root, ["ls-tree", "-r", "--name-only", "-z", resolved_ref]))
        )
    )
    untracked_files = tuple(
        sorted(_git_z(root, ["ls-files", "--others", "--exclude-standard", "-z"]))
    )
    status_short, _untracked_omitted = _filter_status_short_for_prompt(
        _git_text(root, ["status", "--short"]),
        include_untracked_paths=include_untracked_paths,
    )
    return GitReviewState(
        snapshot_ref=resolved_ref,
        head_files=head_files,
        changed_files=selected_changed_files,
        omitted_changed_files=omitted_changed_files,
        untracked_files=untracked_files,
        status_short=status_short,
        diff_from_snapshot=_selected_diff_text(
            root,
            resolved_ref,
            selected_changed_files,
        ),
    )


def write_review_prompt(path: Path, prompt: str) -> None:
    """Atomically write a generated prompt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(prompt, encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a targeted repository review prompt"
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Repository root to package for review",
    )
    parser.add_argument("--output", required=True, help="Write prompt here")
    parser.add_argument(
        "--scope",
        choices=REVIEW_SCOPES,
        default="changed",
        help=(
            "Prompt scope. 'changed' sends only diff, changed files, and "
            "operator-selected context files. 'full' also sends the tracked "
            "snapshot and should be used only when explicitly needed."
        ),
    )
    parser.add_argument(
        "--task",
        help="Review task text. Use --task-file for longer instructions.",
    )
    parser.add_argument("--task-file", help="Read review task text from this file")
    parser.add_argument(
        "--snapshot-ref",
        default="HEAD",
        help=(
            "Git ref used as the diff base and, in --scope full, the stable "
            "repository snapshot."
        ),
    )
    parser.add_argument(
        "--context-file",
        action="append",
        default=[],
        help="Additional workspace file to include. May be passed multiple times.",
    )
    parser.add_argument(
        "--include-path",
        action="append",
        default=[],
        help=(
            "Changed file or directory prefix to include. May be passed multiple "
            "times. Defaults to all changed tracked files."
        ),
    )
    parser.add_argument(
        "--exclude-path",
        action="append",
        default=[],
        help="Changed file or directory prefix to omit from the prompt.",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=DEFAULT_MAX_FILE_BYTES,
        help="Maximum text bytes to include per file before truncation.",
    )
    parser.add_argument(
        "--include-untracked-content",
        action="store_true",
        help=(
            "Include explicitly selected untracked text file content in the "
            "dynamic suffix. Requires --include-untracked-path."
        ),
    )
    parser.add_argument(
        "--include-untracked-path",
        action="append",
        default=[],
        help=(
            "Untracked workspace file to include when "
            "--include-untracked-content is set. May be passed multiple times."
        ),
    )
    args = parser.parse_args(argv)

    try:
        task = _resolve_task(args.task, args.task_file)
        prompt = build_review_prompt(
            workspace_root=Path(args.workspace_root),
            task=task,
            scope=args.scope,
            snapshot_ref=args.snapshot_ref,
            include_paths=tuple(args.include_path),
            exclude_paths=tuple(args.exclude_path),
            context_files=tuple(args.context_file),
            max_file_bytes=args.max_file_bytes,
            include_untracked_content=args.include_untracked_content,
            include_untracked_paths=tuple(args.include_untracked_path),
        )
        write_review_prompt(Path(args.output), prompt)
    except ReviewPromptError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def _review_header(scope: str) -> str:
    return f"""# Targeted Repository Review Packet

scope: {scope}

This prompt is arranged to avoid sending unnecessary repository content.
DeepSeek cannot read omitted workspace files unless the caller supplies them in
the prompt or implements a separate tool-call loop.

## Stable Reviewer Contract

You are an external reviewer for the Harness Research repository.

Review goals:
- find workflow, hook, controller, evidence, and model API defects
- prioritize concrete bugs, regressions, missing tests, and unsafe assumptions
- cite repository paths and line-level evidence when possible
- separate verified findings from inferences and open questions
- do not edit files; return review findings only

Codex hook model to account for:

```text
UserPromptSubmit -> infer route hint and workspace capsule
PreToolUse       -> warn for missing context; block narrow boundary violations
PostToolUse      -> silently record read/write/pending metadata
Stop             -> clear compatible pending state; no default read/Gate block
```

Harness workflow to account for:

```text
WF1 survey -> WF2 idea-debate -> WF3 refine-idea -> WF4 data
-> WF5 baseline -> WF6 arch -> WF7 plan -> WF8 code
-> WF9 validate -> WF10 iterate -> WF11 final-exp -> WF12 release
```

WF10 loop:

```text
$iterate plan -> $iterate code -> $iterate run -> $iterate eval
-> NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
```
"""


def _format_scope_summary(
    state: GitReviewState,
    *,
    scope: str,
    include_paths: tuple[str, ...],
    exclude_paths: tuple[str, ...],
    context_files: tuple[str, ...],
    max_file_bytes: int,
) -> str:
    parts = [
        "## Scope Summary",
        "",
        f"scope: {scope}",
        f"snapshot_ref: {state.snapshot_ref}",
        f"max_file_bytes: {max_file_bytes}",
        f"include_paths: {', '.join(include_paths) if include_paths else '[all]'}",
        f"exclude_paths: {', '.join(exclude_paths) if exclude_paths else '[none]'}",
        "",
        "Changed tracked files:",
    ]
    parts.extend(_format_path_list(state.changed_files))
    parts.append("")
    parts.append("Omitted changed tracked files:")
    parts.extend(_format_path_list(state.omitted_changed_files))
    parts.append("")
    parts.append("Operator-selected context files:")
    parts.extend(_format_path_list(context_files))
    if scope == "changed":
        parts.extend([
            "",
            "Unchanged repository files are intentionally omitted. Treat missing",
            "context as an open question instead of inventing facts.",
        ])
    return "\n".join(parts)


def _format_head_snapshot(
    root: Path,
    snapshot_ref: str,
    head_files: tuple[str, ...],
    *,
    max_file_bytes: int,
) -> str:
    parts = [
        "## Stable Repository Snapshot",
        "",
        f"snapshot_ref: {snapshot_ref}",
        "",
        "This section contains tracked files from snapshot_ref, sorted by path.",
        "It is intentionally placed before volatile review details so repeated",
        "review requests can reuse the same input prefix while working-tree",
        "changes move into the dynamic suffix.",
    ]
    if not head_files:
        parts.append("")
        parts.append("[no tracked snapshot files]")
        return "\n".join(parts)

    for rel_path in head_files:
        _assert_reviewable_for_prompt(rel_path, "snapshot file")
        content = _git_bytes(root, ["show", f"{snapshot_ref}:{rel_path}"])
        parts.append("")
        parts.append(
            _format_file_record(
                rel_path,
                content,
                source=f"snapshot:{snapshot_ref}",
                max_file_bytes=max_file_bytes,
            )
        )
    return "\n".join(parts)


def _format_review_task(task: str) -> str:
    return "\n".join([
        "## Review Task",
        "",
        redact_secrets(task.strip() or "Review the repository for defects."),
    ])


def _format_git_state(state: GitReviewState) -> str:
    status = state.status_short.rstrip() or "[clean]"
    diff = state.diff_from_snapshot.rstrip() or "[no diff from snapshot_ref]"
    return "\n".join([
        "## Git Snapshot",
        "",
        f"snapshot_ref: {state.snapshot_ref}",
        "",
        "### status --short",
        "",
        "```text",
        redact_secrets(status),
        "```",
        "",
        "### diffs",
        "",
        "```diff",
        redact_secrets(diff),
        "```",
    ])


def _format_changed_worktree_files(
    root: Path,
    changed_files: tuple[str, ...],
    *,
    max_file_bytes: int,
) -> str:
    parts = [
        "## Changed Tracked Working-Tree Files",
        "",
        "These files override the stable snapshot for the current review.",
    ]
    if not changed_files:
        parts.append("")
        parts.append("[no changed tracked files]")
        return "\n".join(parts)

    for rel_path in changed_files:
        _assert_reviewable_for_prompt(rel_path, "changed file")
        path = _safe_workspace_path(root, rel_path)
        parts.append("")
        if not path.exists():
            parts.append(f"### FILE: {rel_path}")
            parts.append("")
            parts.append("[deleted from working tree]")
            continue
        parts.append(
            _format_file_record(
                rel_path,
                path.read_bytes(),
                source="working-tree",
                max_file_bytes=max_file_bytes,
            )
        )
    return "\n".join(parts)


def _format_context_files(
    root: Path,
    context_files: tuple[str, ...],
    *,
    max_file_bytes: int,
) -> str:
    parts = ["## Additional Context Files"]
    if not context_files:
        parts.append("")
        parts.append("[none]")
        return "\n".join(parts)

    for rel_path in context_files:
        _assert_reviewable_for_prompt(rel_path, "context file")
        path = _safe_workspace_path(root, rel_path)
        parts.append("")
        if not path.is_file():
            raise ReviewPromptError(f"context file is not a file: {rel_path}")
        parts.append(
            _format_file_record(
                rel_path,
                path.read_bytes(),
                source="context-file",
                max_file_bytes=max_file_bytes,
            )
        )
    return "\n".join(parts)


def _format_untracked_files(
    root: Path,
    untracked_files: tuple[str, ...],
    *,
    include_content: bool,
    include_paths: tuple[str, ...],
    max_file_bytes: int,
) -> str:
    parts = ["## Untracked Files"]
    if not untracked_files:
        parts.append("")
        parts.append("[none]")
        return "\n".join(parts)

    parts.append("")
    if include_content:
        selected = _selected_untracked_paths(untracked_files, include_paths)
        if not selected:
            raise ReviewPromptError(
                "--include-untracked-content requires at least one "
                "--include-untracked-path"
            )
        parts.append("Selected untracked text file content is included.")
        for rel_path in selected:
            _assert_bulk_untracked_reviewable(rel_path)
            path = _safe_workspace_path(root, rel_path)
            parts.append("")
            if path.is_file():
                parts.append(
                    _format_file_record(
                        rel_path,
                        path.read_bytes(),
                        source="untracked",
                        max_file_bytes=max_file_bytes,
                    )
                )
            else:
                parts.append(f"- {rel_path} [non-file]")
    else:
        parts.append(
            "Content and names omitted by default; pass "
            "--include-untracked-content with --include-untracked-path to "
            "include selected files."
        )
        parts.append(f"omitted_count: {len(untracked_files)}")
    return "\n".join(parts)


def _format_file_record(
    rel_path: str,
    content: bytes,
    *,
    source: str,
    max_file_bytes: int,
) -> str:
    digest = hashlib.sha256(content).hexdigest()
    header = [
        f"### FILE: {rel_path}",
        "",
        f"source: {source}",
        f"bytes: {len(content)}",
        f"sha256: {digest}",
        f"--- BEGIN FILE {rel_path} ---",
    ]
    footer = [f"--- END FILE {rel_path} ---"]
    if _is_binary(content):
        body = [f"[binary content omitted: {len(content)} bytes, sha256={digest}]"]
    else:
        text = redact_secrets(content.decode("utf-8", errors="replace")).rstrip()
        encoded = text.encode("utf-8")
        if len(encoded) > max_file_bytes:
            text = encoded[:max_file_bytes].decode("utf-8", errors="ignore").rstrip()
            body = [
                text,
                (
                    f"[truncated after {max_file_bytes} bytes; "
                    f"original bytes={len(content)}, sha256={digest}]"
                ),
            ]
        else:
            body = [text]
    return "\n".join(header + body + footer)


def _format_path_list(paths: tuple[str, ...]) -> list[str]:
    if not paths:
        return ["- [none]"]
    return [f"- {path}" for path in paths]


def _resolve_task(task: str | None, task_file: str | None) -> str:
    if task and task_file:
        raise ReviewPromptError("Use either --task or --task-file, not both")
    if task_file:
        return Path(task_file).read_text(encoding="utf-8")
    return task or "Review this repository and report concrete defects."


def _require_git_worktree(root: Path) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewPromptError(f"Not a Git worktree: {root} ({stderr})")


def _resolve_snapshot_ref(root: Path, snapshot_ref: str) -> str:
    if not snapshot_ref.strip():
        raise ReviewPromptError("snapshot_ref must not be empty")
    return _git_text(
        root,
        ["rev-parse", "--verify", f"{snapshot_ref.strip()}^{{commit}}"],
    ).strip()


def _selected_diff_text(
    root: Path,
    snapshot_ref: str,
    changed_files: tuple[str, ...],
) -> str:
    if not changed_files:
        return ""
    sections: list[str] = []
    commands = [
        (
            f"snapshot_ref {snapshot_ref} -> worktree",
            ["diff", "--no-ext-diff", "--no-color", snapshot_ref, "--", *changed_files],
        ),
        (
            f"snapshot_ref {snapshot_ref} -> index (staged)",
            [
                "diff",
                "--cached",
                "--no-ext-diff",
                "--no-color",
                snapshot_ref,
                "--",
                *changed_files,
            ],
        ),
        (
            "index -> worktree (unstaged)",
            ["diff", "--no-ext-diff", "--no-color", "--", *changed_files],
        ),
    ]
    for label, command in commands:
        diff = _git_text(root, command).rstrip()
        if diff:
            sections.extend([f"### {label}", diff])
    return "\n\n".join(sections)


def _changed_paths_from_snapshot(root: Path, snapshot_ref: str) -> tuple[str, ...]:
    """Return paths changed in worktree or index relative to ``snapshot_ref``."""
    paths: set[str] = set()
    path_commands = [
        ["diff", "--name-only", "-z", snapshot_ref, "--"],
        ["diff", "--cached", "--name-only", "-z", snapshot_ref, "--"],
        ["diff", "--name-only", "-z", "--"],
    ]
    for command in path_commands:
        paths.update(_git_z(root, command))
    return tuple(sorted(paths))


def _filter_paths(
    paths: tuple[str, ...],
    *,
    include_paths: tuple[str, ...],
    exclude_paths: tuple[str, ...],
) -> tuple[str, ...]:
    includes = tuple(_normalize_path_filter(path) for path in include_paths)
    excludes = tuple(_normalize_path_filter(path) for path in exclude_paths)
    selected: list[str] = []
    for path in paths:
        if includes and not any(_path_matches_filter(path, item) for item in includes):
            continue
        if any(_path_matches_filter(path, item) for item in excludes):
            continue
        selected.append(path)
    return tuple(selected)


def _filter_reviewable_paths(
    paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    reviewable: list[str] = []
    denied: list[str] = []
    for path in paths:
        if denied_review_path_reason(path):
            denied.append(path)
        else:
            reviewable.append(path)
    return tuple(reviewable), tuple(denied)


def _normalize_path_filter(path: str) -> str:
    cleaned = path.strip().strip("/")
    if not cleaned:
        raise ReviewPromptError("path filters must not be empty")
    if cleaned.startswith("../") or "/../" in cleaned:
        raise ReviewPromptError(f"path filter escapes workspace: {path}")
    return cleaned


def _path_matches_filter(path: str, path_filter: str) -> bool:
    return path == path_filter or path.startswith(path_filter.rstrip("/") + "/")


def _git_text(root: Path, args: list[str]) -> str:
    return _git_bytes(root, args).decode("utf-8", errors="replace")


def _git_z(root: Path, args: list[str]) -> list[str]:
    raw = _git_bytes(root, args)
    return [
        entry.decode("utf-8", errors="surrogateescape")
        for entry in raw.split(b"\0")
        if entry
    ]


def _git_bytes(root: Path, args: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewPromptError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def _safe_workspace_path(root: Path, rel_path: str) -> Path:
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReviewPromptError(f"Git path escapes workspace: {rel_path}") from exc
    return candidate


def _assert_bulk_untracked_reviewable(rel_path: str) -> None:
    reason = denied_review_path_reason(rel_path)
    if reason:
        raise ReviewPromptError(
            f"untracked file is not safe for bulk inclusion: {rel_path} ({reason})"
        )


def _selected_untracked_paths(
    untracked_files: tuple[str, ...],
    include_paths: tuple[str, ...],
) -> tuple[str, ...]:
    untracked = set(untracked_files)
    selected: list[str] = []
    for value in include_paths:
        rel_path = _normalize_path_filter(value)
        if rel_path not in untracked:
            raise ReviewPromptError(f"selected untracked file not found: {rel_path}")
        selected.append(rel_path)
    return tuple(dict.fromkeys(selected))


def _filter_status_short_for_prompt(
    status: str,
    *,
    include_untracked_paths: tuple[str, ...],
) -> tuple[str, int]:
    included = {path.strip().strip("/") for path in include_untracked_paths}
    lines: list[str] = []
    omitted = 0
    omitted_marker_added = False
    for line in status.splitlines():
        if line.startswith("?? "):
            rel_path = line[3:].strip()
            if rel_path not in included:
                omitted += 1
                if not omitted_marker_added:
                    lines.append("?? [untracked files omitted unless selected]")
                    omitted_marker_added = True
                continue
        lines.append(line)
    return "\n".join(lines), omitted


def _assert_reviewable_for_prompt(rel_path: str, label: str) -> None:
    reason = denied_review_path_reason(rel_path)
    if reason:
        raise ReviewPromptError(
            f"{label} is not safe for external review: {rel_path} ({reason})"
        )


def _is_binary(content: bytes) -> bool:
    return b"\0" in content


if __name__ == "__main__":
    raise SystemExit(main())
