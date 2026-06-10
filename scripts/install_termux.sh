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

if ! command -v pkg >/dev/null 2>&1; then
  echo "[install] This installer must run inside Termux." >&2
  exit 1
fi

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

say() { printf '\n[install] %s\n' "$1"; }

say "Detected Termux user: $(whoami)"
say "Repo root: $REPO_ROOT"

if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
  echo "[install] requirements.txt not found in $REPO_ROOT" >&2
  exit 1
fi

if prompt_yes_no "Install/update required Termux packages (pkg update + git/python/proot-distro/termux-api/termux-tools/tmux/openssh/curl)?"; then
  say "Running pkg update..."
  pkg update -y
  pkg install -y git python proot-distro termux-api termux-tools tmux openssh curl
fi

if prompt_yes_no "Install Termux boot support package too?"; then
  pkg install -y termux-boot || true
fi

mkdir -p "$BOOT_DIR" "$LOCAL_BIN" "$LOG_DIR"

say "Installing bridge helper to $LOCAL_BIN/tt_notify_bridge.py"
cp "$REPO_ROOT/scripts/tt_notify_bridge.py" "$LOCAL_BIN/tt_notify_bridge.py"
chmod +x "$LOCAL_BIN/tt_notify_bridge.py"

say "Installing Termux boot files to $BOOT_DIR"
cp "$REPO_ROOT/scripts/termux_boot_start.sh" "$BOOT_DIR/start.sh"
cp "$REPO_ROOT/scripts/termux_boot_00_start_ubuntu_sshd.sh" "$BOOT_DIR/00_start_ubuntu_sshd.sh"
cp "$REPO_ROOT/scripts/termux_boot_01_notify_bridge.sh" "$BOOT_DIR/01_notify_bridge.sh"
chmod +x "$BOOT_DIR"/*.sh

say "Installing proot helper shells into $TERMUX_HOME"
cp "$REPO_ROOT/scripts/proot_startup.sh" "$TERMUX_HOME/startup.sh"
cp "$REPO_ROOT/scripts/proot_sshd_commands.sh" "$TERMUX_HOME/sshd_commands.sh"
cp "$REPO_ROOT/scripts/proot_start-sshd-once.sh" "$TERMUX_HOME/start-sshd-once.sh"
chmod +x "$TERMUX_HOME/startup.sh" "$TERMUX_HOME/sshd_commands.sh" "$TERMUX_HOME/start-sshd-once.sh"

say "Checking proot distro availability"
if command -v proot-distro >/dev/null 2>&1; then
  if ! proot-distro list 2>/dev/null | grep -q 'ubuntu-jammy'; then
    say "Installing proot distro 'ubuntu-jammy'..."
    proot-distro install ubuntu-jammy
  else
    say "proot distro 'ubuntu-jammy' is already installed."
  fi
else
  echo "[install] proot-distro not found after package install; please reopen Termux and rerun." >&2
  exit 1
fi

say "Creating project directory if needed: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

if [[ -d "$REPO_ROOT/.git" ]]; then
  say "Repo already present at $REPO_ROOT"
else
  say "This installer expects the repo to already be cloned into $REPO_ROOT"
fi

if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
  echo "[install] Missing requirements.txt in repo. Clone the project first." >&2
  exit 1
fi

say "Creating a local virtualenv for the project"
python -m venv "$REPO_ROOT/.venv" || python3 -m venv "$REPO_ROOT/.venv"
"$REPO_ROOT/.venv/bin/python" -m pip install --upgrade pip
"$REPO_ROOT/.venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"

say "Preparing local config from the example template if needed"
if [[ ! -f "$REPO_ROOT/config/config.yaml" ]]; then
  cp "$REPO_ROOT/config/config.example.yaml" "$REPO_ROOT/config/config.yaml"
  echo "[install] Created $REPO_ROOT/config/config.yaml from the example template. Edit your real keywords here."
fi

say "Preparing .env from .env.example if it does not exist"
if [[ ! -f "$REPO_ROOT/.env" ]]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "[install] Created $REPO_ROOT/.env. Edit SMTP and recipient settings before first run."
fi

say "Boot helper installed. Next steps:"
printf '  1. Open Termux once and allow the boot/notification permissions when prompted.\n'
printf '  2. Reopen Termux and run: termux-boot  (or just reboot the phone).\n'
printf '  3. Check the bridge with: python %s/tt_notify_bridge.py --token super-secret-change-me\n' "$LOCAL_BIN"
printf '  4. To verify the proot SSH endpoint, run: proot-distro login ubuntu-jammy -- bash -lc "bash /root/start-sshd-once.sh"\n'
printf '  5. Use this command to inspect the IP after the boot script runs: ifconfig 2>/dev/null | grep -Eo \"inet (addr:)?([0-9]{1,3}\.){3}[0-9]{1,3}\" | grep -v 127.0.0.1\n'

say "Installer finished."
