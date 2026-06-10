# scripts/README

This folder holds the helper scripts used by the Termux + proot runtime.

## Suggested phone setup order
1. Install the baseline packages in Termux:
   ```bash
   pkg update -y
   pkg install -y git openssh python proot-distro termux-api termux-tools tmux curl
   ```
2. Clone the repo:
   ```bash
   git clone https://github.com/skitzofrenzy/service-outage-monitor.git
   cd service-outage-monitor
   ```
3. Run the installer:
   ```bash
   bash scripts/install_termux.sh
   ```
4. Set a Termux password once with:
   ```bash
   passwd
   ```
5. Start the boot hooks with `termux-boot` or reboot the phone.

## What each script does
- `install_termux.sh` — installs the required Termux packages, creates the local config, and wires the boot/notification hooks.
- `tt_notify_bridge.py` — lightweight HTTP bridge used by the proot runner to show toasts and notifications via Termux API.
- `proot_startup.sh` — proot-side launcher that starts the runner in tmux or nohup.
- `proot_sshd_commands.sh` and `proot_start-sshd-once.sh` — SSH service helpers for the Ubuntu proot session.
- `termux_boot_*.sh` — Termux boot hooks that start the bridge and launch the proot runtime on device boot.
