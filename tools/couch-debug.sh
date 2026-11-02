#!/usr/bin/bash
# couch-debug.sh - collect Gaming Mode / NVIDIA logs for the black-screen problem.
#
# What it does:
#   1. Writes a report to ~/couch-debug.txt (this boot AND the previous boot).
#   2. Uploads the report to paste.rs and prints the link.
#   3. Turns on SSH and adds the owner's public key, so the owner's other PC
#      can connect for remote debugging.
#
# Run as your normal user (not root):  curl -sL <url> | bash

set -u
OUT="$HOME/couch-debug.txt"
KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeo9+UhkZK+CeeWbRNnqG3sor+M3e27WC9Q5X1J+4Qy dcintron3790@gmail.com"

echo ">> sudo needs your password once:"
sudo -v || { echo "sudo failed"; exit 1; }

section() { printf '\n========== %s ==========\n' "$1"; }

{
  section "date";            date
  section "rpm-ostree";      rpm-ostree status
  section "uname";           uname -a
  section "cmdline";         cat /proc/cmdline
  section "gpu (lspci)";     lspci -nnk | grep -A3 -Ei 'vga|3d|display'
  section "lsmod nvidia";    lsmod | grep -Ei 'nvidia|nouveau'
  section "nvidia-smi";      nvidia-smi 2>&1 | head -30
  section "drm params"
  for p in modeset fbdev; do
    printf '%s=' "$p"; cat "/sys/module/nvidia_drm/parameters/$p" 2>&1
  done
  ls -l /dev/dri 2>&1
  section "modprobe.d nvidia"; grep -rH . /usr/lib/modprobe.d/*nvidia* /etc/modprobe.d/*nvidia* 2>/dev/null
  section "vulkan icds";     ls /usr/share/vulkan/icd.d/ 2>&1
  section "failed units";    systemctl --failed --no-pager
  section "boots";           sudo journalctl --list-boots --no-pager | tail -5

  for b in 0 -1; do
    section "BOOT $b: display manager"
    sudo journalctl -b "$b" --no-pager -u sddm -u gdm 2>&1 | tail -80
    section "BOOT $b: gamescope / steam / nvidia / drm"
    sudo journalctl -b "$b" --no-pager 2>&1 \
      | grep -Ei 'gamescope|steam|nvidia|nvrm|drm|vulkan|wlserver|xwayland|session' \
      | tail -400
    section "BOOT $b: errors"
    sudo journalctl -b "$b" -p err --no-pager 2>&1 | tail -150
  done
} > "$OUT" 2>&1

echo ">> report saved: $OUT"

# SSH access for remote debugging
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys" && chmod 600 "$HOME/.ssh/authorized_keys"
grep -qF "$KEY" "$HOME/.ssh/authorized_keys" || echo "$KEY" >> "$HOME/.ssh/authorized_keys"
sudo systemctl enable --now sshd >/dev/null 2>&1 && echo ">> SSH is on"

URL=$(curl -s --max-time 30 --data-binary @"$OUT" https://paste.rs)

echo
echo "================ TELL CLAUDE THESE ================"
echo "LOG LINK: ${URL:-upload failed, file is $OUT}"
echo "USER:     $(whoami)"
echo "IP:       $(ip -4 -br addr | awk '$1!="lo"{print $3}' | cut -d/ -f1 | paste -sd' ')"
echo "==================================================="
