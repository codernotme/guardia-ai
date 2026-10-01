#!/bin/bash
# ============================================================================
# Guardia AI v2.0.0 — Raspberry Pi 4B Setup Script (Pixhawk 2.4.8)
# ============================================================================
# Run this on a fresh Raspberry Pi OS Lite 64-bit installation (Bookworm).
#
# Usage:
#   chmod +x setup_pi.sh
#   sudo ./setup_pi.sh
#
# What this does:
#   1. System updates and essential packages (Python 3.11, OpenCV, TFLite)
#   2. Configure Pixhawk 2.4.8 udev rules (USB & UART) and permissions
#   3. Configure camera (Pi Camera Module 3 / v2 libcamera & Picamera2)
#   4. Configure offline local Wi-Fi AP (hostapd/dnsmasq: 192.168.4.1)
#   5. Create local directories for logs, blackbox SQLite DB, recordings
#   6. Set up Python venv with edge AI dependencies
#   7. Disable all telemetry/tracking and configure systemd service
# ============================================================================

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  🚁 Guardia AI v2.0.0 — Pi 4B & Pixhawk 2.4.8 Setup  ║"
echo "║  Tackle Studio — Aryan Bajpai                        ║"
echo "╚══════════════════════════════════════════════════════╝"

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

# Determine boot config file location (Bookworm uses /boot/firmware/config.txt)
BOOT_CONFIG="/boot/config.txt"
if [ -f /boot/firmware/config.txt ]; then
    BOOT_CONFIG="/boot/firmware/config.txt"
fi

# ──────────────────────────────────────────────────────────────
# 1. System Updates & Core Packages
# ──────────────────────────────────────────────────────────────
echo "═══ [1/7] System updates & packages ═══"
apt-get update
apt-get upgrade -y
apt-get install -y \
    python3-pip python3-venv python3-dev \
    libopencv-dev python3-opencv \
    libgstreamer1.0-dev gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    cmake git htop tmux sqlite3 \
    libatlas-base-dev \
    chrony watchdog hostapd dnsmasq iptables \
    python3-picamera2 libcamera-apps libcamera-dev || true

# Add user to required hardware access groups
usermod -aG dialout,video,gpio,i2c "$GUARDIA_USER"

# ──────────────────────────────────────────────────────────────
# 2. Pixhawk 2.4.8 Serial & USB Rules
# ──────────────────────────────────────────────────────────────
echo "═══ [2/7] Configuring Pixhawk 2.4.8 Interfaces ═══"

# Disable serial login console so GPIO14/15 is free for TELEM2 MAVLink
systemctl stop serial-getty@ttyS0.service 2>/dev/null || true
systemctl disable serial-getty@ttyS0.service 2>/dev/null || true
systemctl stop serial-getty@ttyAMA0.service 2>/dev/null || true
systemctl disable serial-getty@ttyAMA0.service 2>/dev/null || true

# Boot config: enable UART and redirect Bluetooth
if ! grep -q "dtoverlay=disable-bt" "$BOOT_CONFIG"; then
    echo "" >> "$BOOT_CONFIG"
    echo "# Guardia AI v2.0.0 — Pixhawk 2.4.8 UART" >> "$BOOT_CONFIG"
    echo "dtoverlay=disable-bt" >> "$BOOT_CONFIG"
    echo "enable_uart=1" >> "$BOOT_CONFIG"
fi

# Pixhawk 2.4.8 USB udev rule (assigns symlink /dev/pixhawk and permissions)
cat > /etc/udev/rules.d/99-pixhawk.rules << 'EOF'
# Pixhawk 2.4.8 / PX4 / 3DR USB Autopilot rule
SUBSYSTEM=="tty", ATTRS{idVendor}=="26ac", ATTRS{idProduct}=="0011", SYMLINK+="pixhawk", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="26ac", MODE="0666", GROUP="dialout"
EOF
udevadm control --reload-rules && udevadm trigger || true

# ──────────────────────────────────────────────────────────────
# 3. Configure Camera (libcamera & Picamera2)
# ──────────────────────────────────────────────────────────────
echo "═══ [3/7] Configuring camera ═══"
if ! grep -q "camera_auto_detect=1" "$BOOT_CONFIG"; then
    echo "camera_auto_detect=1" >> "$BOOT_CONFIG"
fi

# ──────────────────────────────────────────────────────────────
# 4. Configure Offline Ad-hoc Wi-Fi Access Point (GCS Link)
# ──────────────────────────────────────────────────────────────
echo "═══ [4/7] Setting up Offline Wi-Fi AP (192.168.4.1) ═══"

# Configure static IP for wlan0
cat >> /etc/dhcpcd.conf << 'EOF'
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF

# Configure dnsmasq DHCP range for field devices
cat > /etc/dnsmasq.d/guardia-ap.conf << 'EOF'
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
EOF

# Configure hostapd SSID and WPA2
cat > /etc/hostapd/hostapd.conf << 'EOF'
interface=wlan0
driver=nl80211
ssid=Guardia-Drone-Offline
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=guardiaflight2026
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

if [ -f /etc/default/hostapd ]; then
    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
fi

# Unmask and enable services
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd 2>/dev/null || true
systemctl enable dnsmasq 2>/dev/null || true

# ──────────────────────────────────────────────────────────────
# 5. Local Directories & SQLite Database
# ──────────────────────────────────────────────────────────────
echo "═══ [5/7] Creating directory structure ═══"
mkdir -p "$GUARDIA_DIR"/{logs,recordings,models,config,data}
chown -R "$GUARDIA_USER:$GUARDIA_USER" "$GUARDIA_DIR"

# ──────────────────────────────────────────────────────────────
# 6. Python Environment & Dependencies
# ──────────────────────────────────────────────────────────────
echo "═══ [6/7] Setting up Python environment ═══"
sudo -u "$GUARDIA_USER" python3 -m venv "$GUARDIA_DIR/venv"
sudo -u "$GUARDIA_USER" "$GUARDIA_DIR/venv/bin/pip" install --upgrade pip

# Install tflite-runtime, pymavlink, opencv, fastapi
sudo -u "$GUARDIA_USER" "$GUARDIA_DIR/venv/bin/pip" install \
    pymavlink>=2.4.40 \
    tflite-runtime>=2.14.0 \
    numpy>=1.24.0 \
    fastapi>=0.110.0 \
    uvicorn>=0.28.0 \
    websockets>=12.0 \
    pydantic>=2.0.0

if [ -f "$GUARDIA_DIR/drone/requirements.txt" ]; then
    sudo -u "$GUARDIA_USER" "$GUARDIA_DIR/venv/bin/pip" install -r "$GUARDIA_DIR/drone/requirements.txt" || true
fi

# ──────────────────────────────────────────────────────────────
# 7. Disable All Telemetry & Security Hardening
# ──────────────────────────────────────────────────────────────
echo "═══ [7/7] Enforcing Zero-Telemetry Policy ═══"

# Disable OS background telemetry & automatic updates mid-flight
systemctl disable --now apt-daily.timer 2>/dev/null || true
systemctl disable --now apt-daily-upgrade.timer 2>/dev/null || true

# Block known analytics and cloud telemetry domains in hosts
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

# Create systemd auto-start service
cat > /etc/systemd/system/guardia-drone.service << EOF
[Unit]
Description=Guardia AI v2.0.0 Autonomous Drone Daemon
After=network.target

[Service]
Type=simple
User=$GUARDIA_USER
WorkingDirectory=$GUARDIA_DIR/drone
ExecStart=$GUARDIA_DIR/venv/bin/python main.py
Restart=always
RestartSec=3
StandardOutput=append:$GUARDIA_DIR/logs/drone.log
StandardError=append:$GUARDIA_DIR/logs/drone-error.log
Environment=GUARDIA_NO_TELEMETRY=1
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ Setup Complete for Pixhawk 2.4.8 + Pi 4B!        ║"
echo "║                                                      ║"
echo "║  Wi-Fi Access Point: Guardia-Drone-Offline           ║"
echo "║  Wi-Fi Password    : guardiaflight2026               ║"
echo "║  Local GCS Web HUD : http://192.168.4.1:8000         ║"
echo "║  Pixhawk USB Link  : /dev/ttyACM0 or /dev/pixhawk    ║"
echo "║  Pixhawk UART Link : /dev/serial0 (TELEM2)           ║"
echo "║                                                      ║"
echo "║  ⚠️ Please reboot now to apply UART & AP changes     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
