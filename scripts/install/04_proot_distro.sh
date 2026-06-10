#!/usr/bin/env bash

stage_proot_distro() {
  say "Stage 4/5: prepare the proot distro"

  if ! command -v proot-distro >/dev/null 2>&1; then
    echo "[install] proot-distro not found after package install; please reopen Termux and rerun." >&2
    exit 1
  fi

  distro_name="${TT_PROOT_DISTRO:-ubuntu}"
  if proot-distro list 2>/dev/null | grep -q "$distro_name"; then
    say "proot distro '$distro_name' is already installed."
    return 0
  fi

  say "Installing proot distro '$distro_name'..."
  say "This can take several minutes. Keep Termux open and do not close it while the image downloads."

  if ! proot-distro install "$distro_name" 2>/dev/null; then
    say "Primary distro install failed. Falling back to ubuntu-focal..."
    proot-distro install ubuntu-focal 2>/dev/null || true
    say "Falling back to ubuntu-jammy..."
    proot-distro install ubuntu-jammy 2>/dev/null || true
  fi
}
