#!/usr/bin/env bash

stage_boot_helpers() {
  say "Stage 2/5: install Termux boot + notification helpers"

  ensure_dir "$BOOT_DIR"
  ensure_dir "$LOCAL_BIN"
  ensure_dir "$LOG_DIR"

  say "Installing bridge helper to $LOCAL_BIN/tt_notify_bridge.py"
  copy_file "$REPO_ROOT/scripts/tt_notify_bridge.py" "$LOCAL_BIN/tt_notify_bridge.py"
  BOOT_HELPER_CREATED=1

  say "Installing Termux boot files to $BOOT_DIR"
  copy_file "$REPO_ROOT/scripts/termux_boot_start.sh" "$BOOT_DIR/start.sh"
  copy_file "$REPO_ROOT/scripts/termux_boot_00_start_ubuntu_sshd.sh" "$BOOT_DIR/00_start_ubuntu_sshd.sh"
  copy_file "$REPO_ROOT/scripts/termux_boot_01_notify_bridge.sh" "$BOOT_DIR/01_notify_bridge.sh"
}
