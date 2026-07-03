#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export HOME="${HOME:-/root}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg-runtime}"
# Enable AT-SPI / atk-bridge so GTK apps register in the accessibility
# tree — required for dogtail-based widget-name lookup by the
# linux-gui-control skill. We keep NO_AT_BRIDGE=0 (opt-in) rather than
# silently disabling it the way the runtime-base layer used to.
export NO_AT_BRIDGE=0
export GTK_MODULES="${GTK_MODULES:+${GTK_MODULES}:}gail:atk-bridge"
export QT_ACCESSIBILITY=1

mkdir -p "${XDG_RUNTIME_DIR}" "${HOME}/.config/tint2"
chmod 700 "${XDG_RUNTIME_DIR}"

# pyautogui (used by the desktop-control skill) requires ~/.Xauthority to
# exist even for unauthenticated Xvfb displays — it tries to open the file
# at import time and crashes if it's missing. Creating an empty file is
# enough; the "no xauthority details available" warning that Xlib prints
# is harmless.
: > "${HOME}/.Xauthority"

if [[ ! -f "${HOME}/.config/tint2/tint2rc" ]]; then
  cat > "${HOME}/.config/tint2/tint2rc" <<'EOF'
panel_items = TCL
panel_size = 100% 36
taskbar_mode = single_desktop
launcher_padding = 8 8 8
EOF
fi

Xvfb "${DISPLAY}" -screen 0 "${GEOMETRY:-1440x900}x24" -ac -nolisten tcp &
sleep 1
dbus-daemon --session --fork --print-address >/tmp/dbus-session-address
export DBUS_SESSION_BUS_ADDRESS
DBUS_SESSION_BUS_ADDRESS="$(cat /tmp/dbus-session-address)"

xfwm4 >/tmp/xfwm4.log 2>&1 &
xfdesktop >/tmp/xfdesktop.log 2>&1 &
tint2 >/tmp/tint2.log 2>&1 &

# AT-SPI service stack. Needed for the accessibility-based widget
# lookup (dogtail / pyatspi) used by `/root/skills/linux-gui-control/`
# scripts. Without these two daemons, any AT-SPI client will report
# "AT-SPI's desktop is visible but it has no children". Launch them
# after the window manager so GTK apps that start later can register
# themselves through atk-bridge.
if command -v /usr/libexec/at-spi-bus-launcher >/dev/null 2>&1; then
  /usr/libexec/at-spi-bus-launcher --launch-immediately \
      >/tmp/at-spi-bus.log 2>&1 &
  sleep 0.5
fi
if command -v /usr/libexec/at-spi2-registryd >/dev/null 2>&1; then
  /usr/libexec/at-spi2-registryd \
      >/tmp/at-spi-registry.log 2>&1 &
fi

# dogtail's module-level check reads the GNOME `toolkit-accessibility`
# gsetting and `SystemExit`s the caller if it is false. xfce4 sessions
# never set it, so we do it ourselves here. The write lands in the
# per-container dconf backend and is enough to unblock dogtail.
# We use Python (python3-gi is already in the image) instead of the
# `gsettings` CLI, which lives in libglib2.0-bin and is not installed.
python3 - <<'PY' >/dev/null 2>&1 || true
try:
    from gi.repository import Gio
    s = Gio.Settings.new("org.gnome.desktop.interface")
    s.set_boolean("toolkit-accessibility", True)
    s.sync()
except Exception:
    pass
PY

tail -f /dev/null
