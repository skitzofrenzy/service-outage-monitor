#!/usr/bin/env bash

say() {
  printf '\n[install] %s\n' "$1"
}

prompt_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  local answer=""

  while true; do
    if [[ "$default" == "y" ]]; then
      read -r -p "$prompt [Y/n]: " answer
      answer="${answer:-y}"
    else
      read -r -p "$prompt [y/N]: " answer
      answer="${answer:-n}"
    fi

    case "${answer,,}" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) echo "Please answer yes or no." ;;
    esac
  done
}

require_termux() {
  if ! command -v pkg >/dev/null 2>&1; then
    echo "[install] This installer must run inside Termux." >&2
    exit 1
  fi
}

ensure_cmd() {
  local name="$1"
  shift

  if command -v "$name" >/dev/null 2>&1; then
    return 0
  fi

  say "${name} is missing; installing it now..."
  pkg install -y "$@" || pkg install -y "$name"
}

ensure_dir() {
  mkdir -p "$1"
}

copy_file() {
  local src="$1"
  local dst="$2"

  ensure_dir "$(dirname "$dst")"
  cp "$src" "$dst"
  chmod +x "$dst" 2>/dev/null || true
}
