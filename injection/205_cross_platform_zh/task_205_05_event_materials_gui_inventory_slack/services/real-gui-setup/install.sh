#!/usr/bin/env bash
# One-shot task-local setup for the real GUI inventory workflow.
# Installs/verifies LibreOffice Calc, a file manager, image viewers, and the
# real Slack Desktop client from Slack's official Linux download chain when
# that chain resolves to a Debian package.

set -euo pipefail

MARKER_DIR="/tmp_workspace/clawbench/service_state"
RESULTS_DIR="/tmp_workspace/results"
READY_MARKER="${MARKER_DIR}/event-materials-real-gui-ready"
SLACK_BLOCKER="${RESULTS_DIR}/slack_desktop_install_blocker.md"
SLACK_VERSION="${SLACK_VERSION:-4.47.69}"
LOG_PREFIX="[real-gui-setup]"

mkdir -p "${MARKER_DIR}" "${RESULTS_DIR}"

export DEBIAN_FRONTEND=noninteractive

install_gui_packages() {
  echo "${LOG_PREFIX} installing/verifying LibreOffice Calc, file manager, and image viewers"
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dbus-x11 \
    desktop-file-utils \
    file \
    gnupg \
    libreoffice-calc \
    libreoffice-gtk3 \
    pcmanfm \
    ristretto \
    xdg-utils \
    xdotool \
    wmctrl
}

write_slack_blocker() {
  local reason="$1"
  {
    echo "# Slack Desktop install blocker"
    echo
    echo "The real Slack Desktop client could not be installed by the task-local"
    echo "one-shot setup."
    echo
    echo "Reason: ${reason}"
	    echo
	    echo "Only official Slack download locations were attempted:"
	    echo
	    echo "- https://downloads.slack-edge.com/desktop-releases/linux/x64/${SLACK_VERSION}/slack-desktop-${SLACK_VERSION}-amd64.deb"
	    echo "- https://slack.com/downloads/linux"
	    echo "- https://slack.com/downloads/instructions/linux?ddl=1&build=deb"
	    echo "- https://downloads.slack-edge.com/"
    echo
    echo "No Slack mock service or spreadsheet fallback mock is provided for this task."
  } > "${SLACK_BLOCKER}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${MARKER_DIR}/slack-desktop-blocker"
  echo "${LOG_PREFIX} Slack blocker written: ${SLACK_BLOCKER}"
}

candidate_urls_from_slack() {
  local page
  local redirect

  echo "https://downloads.slack-edge.com/desktop-releases/linux/x64/${SLACK_VERSION}/slack-desktop-${SLACK_VERSION}-amd64.deb"

  redirect="$(curl -fsSLI "https://slack.com/downloads/instructions/linux?ddl=1&build=deb" \
    | awk 'BEGIN{IGNORECASE=1} /^location:/ {gsub("\r",""); print $2}' \
    | tail -n 1 || true)"
  if [[ "${redirect}" == https://downloads.slack-edge.com/*slack-desktop*amd64.deb* ]]; then
    echo "${redirect}"
  fi

  page="$(curl -fsSL "https://slack.com/downloads/linux" || true)"
  if [[ -n "${page}" ]]; then
    printf '%s\n' "${page}" \
      | grep -Eo 'https://downloads\.slack-edge\.com/[^"'"'"' <>()]+slack-desktop[^"'"'"' <>()]+amd64\.deb' \
      | sed 's/&amp;/\&/g' \
      | sort -u
  fi
}

install_slack_desktop() {
  if command -v slack >/dev/null 2>&1 || command -v slack-desktop >/dev/null 2>&1; then
    echo "${LOG_PREFIX} Slack Desktop already present"
    return 0
  fi

  local tmp_deb
  tmp_deb="$(mktemp --suffix=.deb)"

  local url
  while IFS= read -r url; do
    [[ -n "${url}" ]] || continue
    echo "${LOG_PREFIX} trying Slack Desktop package: ${url}"
    if curl -fL --retry 2 --connect-timeout 20 -o "${tmp_deb}" "${url}" \
      && dpkg-deb --info "${tmp_deb}" >/dev/null 2>&1 \
      && dpkg-deb --field "${tmp_deb}" Package | grep -qx "slack-desktop"; then
      apt-get install -y "${tmp_deb}"
      rm -f "${tmp_deb}"
      return 0
    fi
  done < <(candidate_urls_from_slack)

  rm -f "${tmp_deb}"
  write_slack_blocker "Slack's official Linux download page did not expose a directly installable amd64 .deb URL."
  return 0
}

install_gui_packages
install_slack_desktop

{
  echo "timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "libreoffice=$(libreoffice --version 2>/dev/null || true)"
  echo "calc=$(command -v localc || true)"
  echo "file_manager=$(command -v pcmanfm || true)"
  echo "image_viewer=$(command -v ristretto || true)"
  echo "slack=$(command -v slack || command -v slack-desktop || true)"
  if [[ -f "${SLACK_BLOCKER}" ]]; then
    echo "slack_blocker=${SLACK_BLOCKER}"
  fi
} > "${READY_MARKER}"

echo "${LOG_PREFIX} ready marker: ${READY_MARKER}"
