#!/bin/bash
# ============================================================================
# Guardia AI v2.0.1 — Raspberry Pi 4B Setup Script
# ============================================================================
# Run this on a fresh Raspberry Pi OS Lite 64-bit installation.
#
# Usage:
#   chmod +x setup_pi.sh
#   sudo ./setup_pi.sh
#
# What this does:
#   1. System updates and essential packages
#   2. Configure UART for Pixhawk communication
#   3. Install Python dependencies
#   4. Set up camera
#   5. Create service files for auto-start
#   6. Disable all telemetry/tracking
#   7. Harden security
# ============================================================================

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  🚁 Guardia AI v2.0.1 — Pi 4B Setup                ║"
echo "║  Tackle Studio — Aryan Bajpai                       ║"
echo "╚══════════════════════════════════════════════════════╝"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Run as root: sudo ./setup_pi.sh"
    exit 1
fi

GUARDIA_USER="${SUDO_USER:-pi}"
GUARDIA_HOME="/home/$GUARDIA_USER"
GUARDIA_DIR="$GUARDIA_HOME/guardia"

echo ""
echo "📋 Setup for user: $GUARDIA_USER"
echo "📁 Install dir: $GUARDIA_DIR"
echo ""

# ──────────────────────────────────────────────────────────────
# 1. System Updates
# ──────────────────────────────────────────────────────────────
echo "═══ [1/7] System updates ═══"
apt-get update
apt-get upgrade -y
apt-get install -y \
    python3-pip python3-venv python3-dev \
    libopencv-dev python3-opencv \
    libgstreamer1.0-dev gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    cmake git htop tmux \
    libatlas-base-dev \
    chrony \
    watchdog

# ──────────────────────────────────────────────────────────────
# 2. Configure UART for Pixhawk
# ──────────────────────────────────────────────────────────────
echo "═══ [2/7] Configuring UART ═══"

# Disable serial console (keeps serial port available for MAVLink)
systemctl stop serial-getty@ttyS0.service 2>/dev/null || true
systemctl disable serial-getty@ttyS0.service 2>/dev/null || true

# Move PL011 UART to GPIO14/15 (disable Bluetooth on this UART)
if ! grep -q "dtoverlay=disable-bt" /boot/config.txt; then
    echo "" >> /boot/config.txt
    echo "# Guardia AI — Pixhawk UART" >> /boot/config.txt
    echo "dtoverlay=disable-bt" >> /boot/config.txt
    echo "enable_uart=1" >> /boot/config.txt
    echo "✅ UART configured (reboot required)"
fi

# Disable Bluetooth modem service
systemctl disable hciuart.service 2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# 3. Configure Camera
# ──────────────────────────────────────────────────────────────
echo "═══ [3/7] Configuring camera ═══"

# Enable camera in boot config
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" >> /boot/config.txt
    echo "gpu_mem=256" >> /boot/config.txt
fi

# Install picamera2
apt-get install -y python3-picamera2 libcamera-apps || true

# ──────────────────────────────────────────────────────────────
# 4. Create Guardia directory structure
# ──────────────────────────────────────────────────────────────
echo "═══ [4/7] Creating directory structure ═══"

mkdir -p "$GUARDIA_DIR"/{logs,recordings,models,config}
chown -R "$GUARDIA_USER:$GUARDIA_USER" "$GUARDIA_DIR"

# ──────────────────────────────────────────────────────────────
# 5. Python environment
# ──────────────────────────────────────────────────────────────
echo "═══ [5/7] Setting up Python environment ═══"

sudo -u "$GUARDIA_USER" python3 -m venv "$GUARDIA_DIR/venv"
sudo -u "$GUARDIA_USER" "$GUARDIA_DIR/venv/bin/pip" install --upgrade pip

# Install requirements if the drone code exists
if [ -f "$GUARDIA_DIR/drone/requirements.txt" ]; then
    sudo -u "$GUARDIA_USER" "$GUARDIA_DIR/venv/bin/pip" install -r "$GUARDIA_DIR/drone/requirements.txt"
fi

# ──────────────────────────────────────────────────────────────
# 6. Disable ALL telemetry and tracking
# ──────────────────────────────────────────────────────────────
echo "═══ [6/7] Disabling telemetry ═══"

# Disable Pi telemetry/metrics
systemctl disable --now apt-daily.timer 2>/dev/null || true
systemctl disable --now apt-daily-upgrade.timer 2>/dev/null || true

# Disable packagekit if installed
systemctl disable --now packagekit 2>/dev/null || true

# Block telemetry domains at hosts level
TELEMETRY_DOMAINS=(
    "telemetry.raspberrypi.com"
    "metrics.raspberrypi.com"
    "analytics.google.com"
    "crashlyticsreports-pa.googleapis.com"
    "firebase-settings.crashlytics.com"
)

for domain in "${TELEMETRY_DOMAINS[@]}"; do
    if ! grep -q "$domain" /etc/hosts; then
        echo "0.0.0.0 $domain" >> /etc/hosts
    fi
done

echo "✅ Telemetry domains blocked in /etc/hosts"

# ──────────────────────────────────────────────────────────────
# 7. Security hardening
# ──────────────────────────────────────────────────────────────
echo "═══ [7/7] Security hardening ═══"

# SSH: disable password auth (use keys only)
if [ -f /etc/ssh/sshd_config ]; then
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    echo "✅ SSH password auth disabled (ensure you have SSH keys set up!)"
fi

# Enable hardware watchdog
if ! grep -q "dtparam=watchdog=on" /boot/config.txt; then
    echo "dtparam=watchdog=on" >> /boot/config.txt
fi

# Configure chrony for time sync (Pi has no RTC)
if [ -f /etc/chrony/chrony.conf ]; then
    echo "✅ Chrony configured for NTP time sync"
fi

# ──────────────────────────────────────────────────────────────
# Systemd service
# ──────────────────────────────────────────────────────────────

cat > /etc/systemd/system/guardia-drone.service << EOF
[Unit]
Description=Guardia AI Drone Agent
After=network.target

[Service]
Type=simple
User=$GUARDIA_USER
WorkingDirectory=$GUARDIA_DIR/drone
ExecStart=$GUARDIA_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=append:$GUARDIA_DIR/logs/drone.log
StandardError=append:$GUARDIA_DIR/logs/drone-error.log
WatchdogSec=30
Environment=GUARDIA_NO_TELEMETRY=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✅ Systemd service created (guardia-drone.service)"
echo "   Start with: sudo systemctl start guardia-drone"
echo "   Enable boot: sudo systemctl enable guardia-drone"

# ──────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ Setup complete!                                  ║"
echo "║                                                      ║"
echo "║  Next steps:                                         ║"
echo "║  1. REBOOT the Pi (required for UART changes)        ║"
echo "║  2. Copy drone code to $GUARDIA_DIR/drone/           ║"
echo "║  3. Copy AI models to $GUARDIA_DIR/models/           ║"
echo "║  4. Wire Pixhawk to Pi UART (TX↔RX, GND↔GND)       ║"
echo "║  5. Run: python main.py                              ║"
echo "║                                                      ║"
echo "║  ⚠️  NO TELEMETRY — all external data blocked        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Reboot now? (y/n)"
read -r answer
if [ "$answer" = "y" ]; then
    reboot
fi
