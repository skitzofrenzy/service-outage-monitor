#!/usr/bin/env bash

stage_base_packages() {
  say "Stage 1/5: base Termux packages"

  if prompt_yes_no "Install/update required Termux packages (pkg update + git/python/proot-distro/termux-api/termux-tools/tmux/openssh/curl/libxml2/libxslt/pkg-config/clang/make)?"; then
    say "Running pkg update..."
    pkg update -y
    pkg install -y \
      git python proot-distro termux-api termux-tools tmux openssh curl \
      libxml2 libxslt pkg-config clang make
  fi

  ensure_cmd git git
  ensure_cmd sshd openssh

  if prompt_yes_no "Install optional termux-boot support too?"; then
    if pkg list termux-boot >/dev/null 2>&1; then
      pkg install -y termux-boot || true
    else
      say "termux-boot package is not available in this environment; skipping that optional step."
    fi
  fi
}
