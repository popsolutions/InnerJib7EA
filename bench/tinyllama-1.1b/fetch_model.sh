#!/usr/bin/env bash
# SPDX-License-Identifier: CC-BY-SA-4.0
#
# Fetch TinyLlama-1.1B-Chat-v1.0 in GGUF Q4_0 quantization from HuggingFace.
# Idempotent: skips download if file present and SHA256 matches.
#
# Closes part of popsolutions/InnerJib7EA#3.

set -euo pipefail

# --- Config -----------------------------------------------------------------

MODEL_FILE="tinyllama-1.1b-chat-v1.0.Q4_0.gguf"
MODEL_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/${MODEL_FILE}"

# SHA256 of the canonical TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF Q4_0 artefact.
# Pinned to detect upstream tampering or a silent file replacement on HF.
#
# NOTE: this default value is a PLACEHOLDER. The first CI bench run will
# fail SHA256 verification — record the actual hash from that run's logs and
# update this constant in a follow-up commit. We deliberately do not pin a
# hash we cannot verify locally (no network access during bootstrap).
# Set EXPECTED_SHA256="" to skip verification temporarily (NOT for CI).
EXPECTED_SHA256="${EXPECTED_SHA256:-PLACEHOLDER_UPDATE_AFTER_FIRST_FETCH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_PATH="${SCRIPT_DIR}/${MODEL_FILE}"

# --- Helpers ----------------------------------------------------------------

log() { printf '[fetch_model] %s\n' "$*" >&2; }

compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        log "ERROR: neither sha256sum nor shasum available"
        exit 2
    fi
}

verify_sha256() {
    local path="$1"
    local actual
    actual="$(compute_sha256 "${path}")"
    if [[ -z "${EXPECTED_SHA256}" ]]; then
        log "EXPECTED_SHA256 unset — skipping verification (NOT recommended for CI)"
        log "  computed: ${actual}"
        return 0
    fi
    if [[ "${EXPECTED_SHA256}" == "PLACEHOLDER_UPDATE_AFTER_FIRST_FETCH" ]]; then
        log "EXPECTED_SHA256 is the bootstrap placeholder."
        log "  computed: ${actual}"
        log "  ACTION: update EXPECTED_SHA256 in this script to the value above,"
        log "          commit, then re-run. Failing for now to force the fix."
        return 5
    fi
    if [[ "${actual}" != "${EXPECTED_SHA256}" ]]; then
        log "ERROR: SHA256 mismatch."
        log "  expected: ${EXPECTED_SHA256}"
        log "  actual:   ${actual}"
        return 4
    fi
    log "SHA256 OK: ${actual}"
    return 0
}

# --- Main -------------------------------------------------------------------

if [[ -f "${TARGET_PATH}" ]]; then
    log "Found existing model at ${TARGET_PATH}, verifying SHA256..."
    if verify_sha256 "${TARGET_PATH}"; then
        log "Already up to date. Skipping download."
        exit 0
    fi
    log "Existing file failed verification — deleting and re-fetching."
    rm -f "${TARGET_PATH}"
fi

log "Fetching ${MODEL_FILE} (~668 MB) from HuggingFace..."

if command -v curl >/dev/null 2>&1; then
    curl --fail --location --progress-bar \
        --output "${TARGET_PATH}.partial" \
        "${MODEL_URL}"
elif command -v wget >/dev/null 2>&1; then
    wget --show-progress --output-document "${TARGET_PATH}.partial" \
        "${MODEL_URL}"
else
    log "ERROR: neither curl nor wget available"
    exit 3
fi

mv "${TARGET_PATH}.partial" "${TARGET_PATH}"

log "Verifying downloaded file SHA256..."
if ! verify_sha256 "${TARGET_PATH}"; then
    log "Refusing to proceed. Either:"
    log "  - HF rotated the artefact (update EXPECTED_SHA256 in this script), or"
    log "  - the download was corrupted (re-run this script)."
    exit 4
fi

log "OK — ${MODEL_FILE} ready at ${TARGET_PATH}"
