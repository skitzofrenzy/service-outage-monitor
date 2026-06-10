#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 10
proot-distro login ubuntu-jammy -- bash -lc 'bash ~/sshd_commands.sh start'
termux-notification --title "SSHD" --content "Ubuntu SSHD started at boot"
