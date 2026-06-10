#!/usr/bin/env bash
# Install and wire the Termux/proot runtime for this repo.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TERMUX_HOME="${HOME:-/data/data/com.termux/files/home}"
BOOT_DIR="$TERMUX_HOME/.termux/boot"
LOCAL_BIN="$TERMUX_HOME/.local/bin"
LOG_DIR="$TERMUX_HOME/logs"
PROJECT_DIR="$TERMUX_HOME/projects/apps/service-outage-monitor"
BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/service-outage-monitor-install.XXXXXX")"
VENV_CREATED=0
CONFIG_CREATED=0
ENV_CREATED=0
BOOT_HELPER_CREATED=0
PROOT_HELPER_CREATED=0

export TERMUX_HOME BOOT_DIR LOCAL_BIN LOG_DIR PROJECT_DIR REPO_ROOT BACKUP_DIR
export VENV_CREATED CONFIG_CREATED ENV_CREATED BOOT_HELPER_CREATED PROOT_HELPER_CREATED

cleanup_on_error() {
  local exit_code=${1:-$?}
  if [[ $exit_code -eq 0 ]]; then
    return 0
  fi

  echo "[install] Setup failed (exit $exit_code); cleaning up partial changes..." >&2
  if [[ ${VENV_CREATED:-0} -eq 1 && -d "$REPO_ROOT/.venv" ]]; then
    rm -rf "$REPO_ROOT/.venv"
  fi
  if [[ ${CONFIG_CREATED:-0} -eq 1 && -f "$REPO_ROOT/config/config.yaml" ]]; then
    rm -f "$REPO_ROOT/config/config.yaml"
  fi
  if [[ ${ENV_CREATED:-0} -eq 1 && -f "$REPO_ROOT/.env" ]]; then
    rm -f "$REPO_ROOT/.env"
  fi
  if [[ ${BOOT_HELPER_CREATED:-0} -eq 1 ]]; then
    rm -f "$LOCAL_BIN/tt_notify_bridge.py" || true
    rm -f "$BOOT_DIR/start.sh" "$BOOT_DIR/00_start_ubuntu_sshd.sh" "$BOOT_DIR/01_notify_bridge.sh" || true
  fi
  if [[ ${PROOT_HELPER_CREATED:-0} -eq 1 ]]; then
    rm -f "$TERMUX_HOME/startup.sh" "$TERMUX_HOME/sshd_commands.sh" "$TERMUX_HOME/start-sshd-once.sh" || true
  fi
  rm -rf "$BACKUP_DIR"
}
trap 'cleanup_on_error $?' ERR

source "$SCRIPT_DIR/install/common.sh"
source "$SCRIPT_DIR/install/01_base_packages.sh"
source "$SCRIPT_DIR/install/02_boot_helpers.sh"
source "$SCRIPT_DIR/install/03_proot_helpers.sh"
source "$SCRIPT_DIR/install/04_proot_distro.sh"
source "$SCRIPT_DIR/install/05_python_env.sh"
source "$SCRIPT_DIR/install/06_local_config.sh"

require_termux

say "Detected Termux user: $(whoami)"
say "Repo root: $REPO_ROOT"

if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
  echo "[install] requirements.txt not found in $REPO_ROOT" >&2
  exit 1
fi

stage_base_packages
stage_boot_helpers
stage_proot_helpers
stage_proot_distro

say "Creating project directory if needed: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

if [[ -d "$REPO_ROOT/.git" ]]; then
  say "Repo already present at $REPO_ROOT"
else
  say "This installer expects the repo to already be cloned into $REPO_ROOT"
fi

stage_python_env
stage_local_config

say "Starting Termux SSHD for the first run"
if command -v sshd >/dev/null 2>&1; then
  sshd || true
  echo "[install] Termux sshd started on port 8022."
fi

say "Boot helper installed. Next steps:"
printf '  1. If this is your first time, run: passwd\n'
printf '  2. Open Termux once and allow the boot/notification permissions when prompted.\n'
printf '  3. Reopen Termux and run: termux-boot  (or just reboot the phone).\n'
printf '  4. Check the bridge with: python %s/tt_notify_bridge.py --token super-secret-change-me\n' "$LOCAL_BIN"
printf '  5. To verify the proot SSH endpoint, run: proot-distro login ubuntu -- bash -lc "bash /root/start-sshd-once.sh"\n'
printf '  6. To find your phone IP for SSH: ip addr show 2>/dev/null | grep -Eo "inet ([0-9]{1,3}\\.){3}[0-9]{1,3}" | grep -v 127.0.0.1\n'

say "Installer finished."
