#!/bin/bash
set -e

echo "=== Harness Research Loop Bootstrap ==="
echo ""

# ── 1. Copy templates to actual files (only if not already present) ──────────
for tmpl in *.template; do
    [ -f "$tmpl" ] || continue
    target="${tmpl%.template}"
    if [ ! -f "$target" ]; then
        cp "$tmpl" "$target"
        echo "  [created] $target  (from $tmpl)"
    else
        echo "  [skipped] $target  (already exists)"
    fi
done

# settings.local.json → .claude/
if [ -f "settings.local.json.template" ] && [ ! -f ".claude/settings.local.json" ]; then
    cp settings.local.json.template .claude/settings.local.json
    echo "  [created] .claude/settings.local.json"
elif [ -f ".claude/settings.local.json" ]; then
    echo "  [skipped] .claude/settings.local.json  (already exists)"
fi

echo ""

# ── 2. Create project directory structure ────────────────────────────────────
for dir in src scripts configs baselines experiments docs docs/iterations tests; do
    mkdir -p "$dir"
done
echo "  [created] project directories (src/ scripts/ configs/ baselines/ experiments/ docs/ tests/)"

# State directories for iteration context
mkdir -p .claude/iterations
mkdir -p .agents/state/iterations
echo "  [created] iteration state directories"

echo ""

# ── 3. Initialize research project git (if not already present) ──────────────
if [ ! -d ".git" ]; then
    git init
    echo "  [created] research repo (.git)"
else
    echo "  [skipped] research repo (.git already exists)"
fi

echo ""

# ── 4. Generate research project .gitignore ──────────────────────────────────
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'GITIGNORE'
# === Harness framework (managed by hgit) ===
.harness

# === Build / Runtime ===
__pycache__/
*.pyc
*.egg-info/
*.so
build/
dist/

# === Experiments (large binary files) ===
experiments/checkpoints/
*.ckpt
*.pth
*.pt
wandb/

# === System ===
.DS_Store
*.swp
*~
GITIGNORE
    echo "  [created] .gitignore for research repo"
else
    echo "  [skipped] .gitignore  (already exists)"
fi

echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md — replace {{placeholders}} with project info"
echo "     or run:  /orchestrator init   (Claude Code)"
echo "              \$orchestrator init   (Codex)"
echo ""
echo "  2. Set research repo remote:"
echo "     git remote add origin <your-research-repo-url>"
echo ""
echo "  3. Set up hgit alias (add to ~/.bashrc or ~/.zshrc):"
echo "     alias hgit='git --git-dir=.harness --work-tree=.'"
echo ""
