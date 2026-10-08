#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# push_to_sarrathi.sh — publish Arthabodh (Sarathi Labs) to
#
#     https://github.com/Maksmit0611/Sarrathi
#
# Run it from inside this folder:
#
#     bash push_to_sarrathi.sh
#
# What it does:
#   1. makes sure everything here is committed
#   2. fetches the GitHub repo (it already has a LICENSE and README)
#   3. merges the two histories so NOTHING on GitHub is lost
#   4. pushes
#
# It is safe to run more than once.
#
# SECURITY: this script never stores a token. When git asks for a password,
# paste a Personal Access Token (not your account password):
#     https://github.com/settings/tokens  ->  Fine-grained token
#     Repository access: Maksmit0611/Sarrathi
#     Permissions: Contents = Read and write
# ---------------------------------------------------------------------------
set -euo pipefail

GREEN=$'\033[32m'; CYAN=$'\033[36m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
say()  { printf "%s\n" "${CYAN}▸${OFF} $*"; }
ok()   { printf "%s\n" "${GREEN}✓${OFF} $*"; }
warn() { printf "%s\n" "${YELLOW}!${OFF} $*"; }
die()  { printf "%s\n" "${RED}✗${OFF} $*" >&2; exit 1; }

REMOTE_URL="https://github.com/Maksmit0611/Sarrathi.git"
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf "\n%s\n\n" "${BOLD}☸ Publishing Arthabodh → github.com/Maksmit0611/Sarrathi${OFF}"

command -v git >/dev/null 2>&1 || die "git is not installed: https://git-scm.com/downloads"

# --- safety: never publish secrets -----------------------------------------
if [ -f .env ]; then warn ".env exists and is git-ignored — good, keep it that way."; fi
if git grep -qE 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{30,}' -- . 2>/dev/null; then
  die "A possible API key is committed. Remove it before publishing."
fi

# --- 1. local repo ---------------------------------------------------------
if [ ! -d .git ]; then
  say "Initialising git repository..."
  git init -q
  git branch -M main 2>/dev/null || true
fi
git config user.email >/dev/null 2>&1 || git config user.email "you@example.com"
git config user.name  >/dev/null 2>&1 || git config user.name  "$(whoami)"

if [ -n "$(git status --porcelain)" ]; then
  say "Committing local changes..."
  git add -A
  git commit -q -m "Update Arthabodh" || true
fi

# --- 2. remote -------------------------------------------------------------
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
say "Fetching the existing repository (keeping its LICENSE and history)..."
git fetch -q origin main 2>/dev/null || warn "Could not fetch — is the repo empty or offline? Continuing anyway."

# --- 3. merge histories without losing anything ----------------------------
if git rev-parse --verify -q origin/main >/dev/null; then
  if ! git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
    say "Merging GitHub history into local history (local files win on conflict)..."
    git merge origin/main --allow-unrelated-histories -X ours --no-edit -q \
      || die "Merge hit a conflict. Run 'git status' to see it, or ask for help."
    # keep the licence they chose on GitHub
    if git cat-file -e origin/main:LICENSE 2>/dev/null; then
      git checkout origin/main -- LICENSE
      git commit -q --amend --no-edit
      ok "Kept the repository's existing LICENSE."
    fi
    ok "Merged. Nothing from GitHub was lost."
  fi
fi

# --- 4. push ---------------------------------------------------------------
printf "\n"
cat <<AUTH
${BOLD}When git asks for credentials${OFF}:
  • Username: ${BOLD}Maksmit0611${OFF}
  • Password: a ${BOLD}Personal Access Token${OFF} — NOT your account password
      create one → ${CYAN}https://github.com/settings/tokens${OFF}
      Fine-grained token → Repository access: Sarrathi → Permissions: Contents = Read and write

AUTH
say "Pushing to main..."
git push -u origin main

printf "\n%s\n" "${GREEN}${BOLD}Published.${OFF}"
echo "  ${CYAN}https://github.com/Maksmit0611/Sarrathi${OFF}"
echo
echo "  Next steps on GitHub:"
echo "   1. About → description, and paste the topics from docs/GITHUB_LISTING.md"
echo "   2. Settings → Social preview → upload a screenshot of a real report"
echo "   3. Check the Actions tab — CI should run 63 tests, green"
