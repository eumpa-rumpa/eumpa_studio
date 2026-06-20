#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT_DIR/.env.1password.tpl"
OUTPUT="$ROOT_DIR/.env"
FORCE=0

usage() {
  cat <<'EOF'
Usage: bash scripts/setup-env.sh [--force] [--template PATH] [--output PATH]

Generate a local .env file by resolving 1Password secret references with
`op inject`. The generated file is mode 0600 and is ignored by Git.

Options:
  --force          Overwrite the output file if it already exists.
  --template PATH  Template to inject. Defaults to .env.1password.tpl.
  --output PATH    Output dotenv file. Defaults to .env.
  --help           Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    --template)
      TEMPLATE="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v op >/dev/null 2>&1; then
  cat >&2 <<'EOF'
1Password CLI (`op`) was not found.
Install it with:
  brew install --cask 1password-cli
Then sign in with:
  op signin
EOF
  exit 1
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Template file not found: $TEMPLATE" >&2
  exit 1
fi

if [[ -e "$OUTPUT" && "$FORCE" -ne 1 ]]; then
  echo "Output file already exists: $OUTPUT" >&2
  echo "Pass --force to regenerate it." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
TMP_OUTPUT="$(mktemp "${OUTPUT}.tmp.XXXXXX")"
cleanup() {
  rm -f "$TMP_OUTPUT"
}
trap cleanup EXIT

if ! op inject --in-file "$TEMPLATE" --out-file "$TMP_OUTPUT" --file-mode 0600 --force; then
  cat >&2 <<'EOF'
Failed to resolve 1Password references.
Check that you are signed in (`op signin`) and that the vault/item/fields in
.env.1password.tpl exist.
EOF
  exit 1
fi

mv "$TMP_OUTPUT" "$OUTPUT"
chmod 600 "$OUTPUT"
trap - EXIT

DATA_ROOT="$(sed -n 's/^EUMPA_DATA_ROOT=//p' "$OUTPUT" | tail -n 1)"
DATA_ROOT="${DATA_ROOT%\"}"
DATA_ROOT="${DATA_ROOT#\"}"
DATA_ROOT="${DATA_ROOT%\'}"
DATA_ROOT="${DATA_ROOT#\'}"
if [[ -n "$DATA_ROOT" ]]; then
  if [[ "$DATA_ROOT" = /* ]]; then
    mkdir -p "$DATA_ROOT"
  else
    mkdir -p "$ROOT_DIR/$DATA_ROOT"
  fi
fi

echo "Wrote $OUTPUT"
