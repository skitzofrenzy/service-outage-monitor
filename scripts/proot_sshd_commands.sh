#!/bin/bash
set -euo pipefail

start_sshd_debug() {
  echo "Starting SSHD in debug mode with config: /etc/ssh/sshd_config.min"
  mkdir -p /var/log/proot
  /usr/sbin/sshd -E /var/log/proot/sshd.log -D -e -f /etc/ssh/sshd_config.min
}

stop_sshd() {
  echo "Stopping SSHD service"
  pkill -x sshd || echo "SSHD is not running"
}

check_sshd_status() {
  if pgrep -x sshd > /dev/null; then
    echo "SSHD is running"
    exit 0
  else
    echo "SSHD is not running"
    exit 1
  fi
}

restart_sshd() {
  echo "Restarting SSHD service"
  stop_sshd
  start_sshd_debug
}

test_ssh_connection() {
  echo "Testing SSH connection on 127.0.0.1:30022"
  if command -v nc >/dev/null 2>&1; then
    nc -vz 127.0.0.1 30022
  else
    echo "nc (netcat) not found. Install it first."
    exit 2
  fi
}

monitor_ssh_logs() {
  mkdir -p /var/log/proot
  : > /var/log/proot/sshd.log
  echo "Monitoring SSH logs (/var/log/proot/sshd.log)"
  tail -f /var/log/proot/sshd.log
}

clear_ssh_logs() {
  mkdir -p /var/log/proot
  echo "Clearing SSH logs"
  > /var/log/proot/sshd.log
}

show_menu() {
  cat <<'MENU'
===== SSHD Command Menu =====
1) Start SSHD in Debug Mode
2) Stop SSHD
3) Check SSHD Status
4) Restart SSHD
5) Test SSH Connection Locally
6) Monitor SSH Logs
7) Clear SSH Logs
8) Exit
MENU
}

usage() {
  cat <<'HELP'
Usage:
  sshd_commands.sh                 # show menu
  sshd_commands.sh <option>        # run by number (1-7)
  sshd_commands.sh <name>          # run by name: start|stop|status|restart|test|monitor|clear|help
HELP
}

execute_command() {
  local sel="${1:-}"
  case "$sel" in
    1|start) start_sshd_debug ;;
    2|stop) stop_sshd ;;
    3|status) check_sshd_status ;;
    4|restart) restart_sshd ;;
    5|test) test_ssh_connection ;;
    6|monitor) monitor_ssh_logs ;;
    7|clear) clear_ssh_logs ;;
    8|exit|quit) echo "Exiting..."; exit 0 ;;
    h|-h|--help|help) usage; exit 0 ;;
    *) echo "Invalid option: $sel"; usage; exit 64 ;;
  esac
}

if [[ $# -gt 0 ]]; then
  for arg in "$@"; do
    execute_command "$arg"
  done
  exit 0
fi

while true; do
  show_menu
  read -rp "Please choose an option (1-8): " choice
  execute_command "$choice"
  echo
 done
