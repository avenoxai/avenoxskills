#!/usr/bin/env bash
set -euo pipefail

# GPTPro export.
# Splits a repo into logical, node_modules-free, secret-free zip bundles so a
# non-agentic model (GPT Pro on the ChatGPT front end, or any chat model with
# file upload) can be handed the codebase a part at a time and navigate it
# cleanly for review and feedback.
#
# Bundles are declared in bundles.conf — see bundles.example.conf.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/gptpro-bundles}"
BUNDLES_CONF="${BUNDLES_CONF:-$SCRIPT_DIR/../bundles.conf}"
BUNDLE_PREFIX="${BUNDLE_PREFIX:-$(basename "$PROJECT_ROOT")}"
ALLOW_SECRETS="${ALLOW_SECRETS:-0}"
AUTODETECT=0  # set when no bundles.conf exists; silences expected missing-source noise
TMP_DIR="${TMPDIR:-/tmp}/gptpro-export-$$"

log()  { printf '[gptpro] %s\n' "$1"; }
soft() { [ "$AUTODETECT" = "1" ] || printf '[gptpro] WARN: %s\n' "$1" >&2; }
warn() { printf '[gptpro] WARN: %s\n' "$1" >&2; }
die()  { printf '[gptpro] ERROR: %s\n' "$1" >&2; exit 1; }

command -v zip   >/dev/null 2>&1 || die "missing required command: zip"
command -v rsync >/dev/null 2>&1 || die "missing required command: rsync"

[ -d "$PROJECT_ROOT" ]  || die "PROJECT_ROOT does not exist: $PROJECT_ROOT"

# Global excludes: deps, build output, caches, secrets, vcs noise, binary assets.
EXCLUDES=(
  --exclude '.git'
  --exclude 'node_modules'
  --exclude '.next'
  --exclude '.turbo'
  --exclude 'dist'
  --exclude 'build'
  --exclude 'out'
  --exclude 'coverage'
  --exclude '.vercel'
  --exclude '*.tsbuildinfo'
  --exclude '.env'
  --exclude '.env.*'
  --exclude '*.log'
  --exclude '.DS_Store'
  --exclude 'Icon?'
  # Binary assets — noise for a code-review model; keep bundles light.
  --exclude '*.png'  --exclude '*.jpg'  --exclude '*.jpeg'
  --exclude '*.gif'  --exclude '*.webp' --exclude '*.avif'
  --exclude '*.ico'  --exclude '*.mp4'  --exclude '*.mov'
  --exclude '*.webm' --exclude '*.woff' --exclude '*.woff2'
  --exclude '*.ttf'  --exclude '*.otf'
)

BUNDLE_NAMES=()
BUNDLE_DESCS=()

# define_bundle <name> "<description>" <source>...
#   sources: dir:<path>[:<extra-exclude>] | file:<path>[:<subdir>]
define_bundle() {
  local name="$1"; local desc="$2"; shift 2
  local staged=0

  for src in "$@"; do
    local kind="${src%%:*}"
    local rest="${src#*:}"

    case "$kind" in
      dir)
        local path="${rest%%:*}"
        local extra=""
        [ "$rest" != "$path" ] && extra="${rest#*:}"
        local abs="$PROJECT_ROOT/$path"
        if [ ! -d "$abs" ]; then soft "skipping missing dir for '$name': $path"; continue; fi
        mkdir -p "$TMP_DIR/$name"
        if [ -n "$extra" ]; then
          rsync -a "${EXCLUDES[@]}" --exclude "$extra" "$abs/" "$TMP_DIR/$name/$(basename "$path")/"
        else
          rsync -a "${EXCLUDES[@]}" "$abs/" "$TMP_DIR/$name/$(basename "$path")/"
        fi
        staged=1
        ;;
      file)
        local path="${rest%%:*}"
        local sub=""
        [ "$rest" != "$path" ] && sub="${rest#*:}"
        local abs="$PROJECT_ROOT/$path"
        if [ ! -e "$abs" ]; then soft "skipping missing file for '$name': $path"; continue; fi
        mkdir -p "$TMP_DIR/$name/$sub"
        cp "$abs" "$TMP_DIR/$name/$sub/"
        staged=1
        ;;
      *)
        warn "unknown source type '$kind' in bundle '$name' (expected dir: or file:)"
        ;;
    esac
  done

  if [ "$staged" -eq 0 ]; then
    soft "bundle '$name' staged nothing — skipping"
    return
  fi
  BUNDLE_NAMES+=("$name")
  BUNDLE_DESCS+=("$desc")
  log "staged $name"
}

# --- autodetect --------------------------------------------------------------
# Zero-config fallback when no bundles.conf exists. One bundle per workspace
# package (apps/*, packages/*, services/*), a schema-only db bundle, a docs
# bundle, and a src bundle for a plain single-package repo.
autodetect_bundles() {
  local found=0 d name

  for parent in apps packages services libs; do
    [ -d "$PROJECT_ROOT/$parent" ] || continue
    for d in "$PROJECT_ROOT/$parent"/*/; do
      [ -d "$d" ] || continue
      name="$(basename "$d")"
      define_bundle "$name" "$parent/$name — workspace package" "dir:$parent/$name"
      found=1
    done
  done

  if [ "$found" -eq 0 ]; then
    # Single-package repo: ship source + config, skip the workspace walk.
    define_bundle src "application source" \
      dir:src dir:lib dir:app dir:test dir:tests \
      file:package.json file:tsconfig.json file:pyproject.toml \
      file:go.mod file:Cargo.toml
  fi

  # Schema construction only — never rows or seed data.
  define_bundle db "database architecture: migrations and schema map (no rows)" \
    dir:supabase/migrations dir:migrations dir:db/migrations dir:prisma \
    file:supabase/config.toml:supabase

  define_bundle docs "architecture, ADRs, and conventions" \
    dir:docs dir:adrs dir:doc dir:prds \
    file:README.md file:AGENTS.md file:CLAUDE.md \
    file:pnpm-workspace.yaml file:package.json
}

# --- secret scan -------------------------------------------------------------
# The whole point of these bundles is that they are safe to upload to a
# third-party chat UI. A bundle you have to remember to check by hand is not.
#
# Two tiers, because a one-tier scan on a real repo is all false positives and
# you end up passing ALLOW_SECRETS=1 every run — which is the same as no scan.
#   HARD  — provider-issued credential shapes. Aborts the export.
#   SOFT  — generic `secret = "..."` assignments. Printed for your eyes only.
# Test files and obvious placeholders are demoted to SOFT: a secret-handling
# test suite is *supposed* to contain credential-shaped strings.
scan_secrets() {
  local hard='BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{40,}|sk-[A-Za-z0-9]{40,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.'
  local soft='(password|passwd|secret|api_?key|access_?token)[[:space:]]*[=:][[:space:]]*["'\''][^"'\''[:space:]]{8,}'
  # Demoted: fixture markers, test paths, and env-indirection like env(FOO).
  local fixture='FAKE|EXAMPLE|PLACEHOLDER|DUMMY|REDACTED|SAMPLE|NOT_?A_?REAL|xxxxxxxx|XXXXXXXX|0123456789|abcdefghij|env\('
  local testpath='/(test|tests|__tests__|fixtures|spec)/|\.(test|spec)\.[a-z]+:'

  local soft_hits hard_hits
  soft_hits="$(grep -rInEo "$soft|$hard" "$TMP_DIR" 2>/dev/null || true)"
  hard_hits="$(printf '%s\n' "$soft_hits" | grep -E "$hard" 2>/dev/null | grep -Ev "$fixture" | grep -Ev "$testpath" || true)"

  if [ -n "$soft_hits" ]; then
    printf '\n[gptpro] credential-shaped strings found (review, not fatal):\n%s\n\n' \
      "$(printf '%s\n' "$soft_hits" | sed "s|$TMP_DIR/||" | head -25)" >&2
  fi

  if [ -n "$hard_hits" ]; then
    printf '\n[gptpro] LIVE-LOOKING CREDENTIALS — export aborted:\n\n%s\n\n' \
      "$(printf '%s\n' "$hard_hits" | sed "s|$TMP_DIR/||")" >&2
    if [ "$ALLOW_SECRETS" = "1" ]; then
      warn "ALLOW_SECRETS=1 set — continuing anyway. Verify every hit above is a fixture."
    else
      die "refusing to build bundles. Remove the values, or re-run with ALLOW_SECRETS=1 if these are fixtures."
    fi
  else
    log "secret scan clean (no live-looking credentials)"
  fi
}

zip_bundle() {
  local name="$1"
  ( cd "$TMP_DIR" && zip -rq "$BUNDLE_PREFIX-$name.zip" "$name/" )
  mv "$TMP_DIR/$BUNDLE_PREFIX-$name.zip" "$OUTPUT_DIR/"
}

trap 'rm -rf "$TMP_DIR"' EXIT

log "project: $PROJECT_ROOT"
log "output:  $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR" "$TMP_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f -name '*.zip' -delete 2>/dev/null || true

# --- bundle definitions ------------------------------------------------------
# A hand-written bundles.conf always wins: a split that matches your architecture
# beats anything inferred. Without one, fall back to autodetect so the skill is
# useful in a fresh repo on the first run.
if [ -f "$BUNDLES_CONF" ]; then
  log "bundles: $BUNDLES_CONF"
  # shellcheck disable=SC1090
  source "$BUNDLES_CONF"
else
  log "no bundles.conf — autodetecting layout (write one for a better split)"
  AUTODETECT=1
  autodetect_bundles
fi

[ "${#BUNDLE_NAMES[@]}" -gt 0 ] || die "no bundles staged — check $BUNDLES_CONF against your repo layout"

scan_secrets

for name in "${BUNDLE_NAMES[@]}"; do zip_bundle "$name"; done

log "done"
ls -lh "$OUTPUT_DIR"/*.zip

printf '\nSummary (%s, node_modules-free, secret-scanned):\n' "$BUNDLE_PREFIX"
for i in "${!BUNDLE_NAMES[@]}"; do
  printf -- '- %s-%s.zip : %s\n' "$BUNDLE_PREFIX" "${BUNDLE_NAMES[$i]}" "${BUNDLE_DESCS[$i]}"
done
