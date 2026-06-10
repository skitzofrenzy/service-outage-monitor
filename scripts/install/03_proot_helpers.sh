#!/usr/bin/env bash

stage_proot_helpers() {
  say "Stage 3/5: install proot helper shells"

  copy_file "$REPO_ROOT/scripts/proot_startup.sh" "$TERMUX_HOME/startup.sh"
  copy_file "$REPO_ROOT/scripts/proot_sshd_commands.sh" "$TERMUX_HOME/sshd_commands.sh"
  copy_file "$REPO_ROOT/scripts/proot_start-sshd-once.sh" "$TERMUX_HOME/start-sshd-once.sh"
  PROOT_HELPER_CREATED=1
}
