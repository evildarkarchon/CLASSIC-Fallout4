#!/usr/bin/env bash

# Load the Visual Studio Dev Shell environment into Git Bash and pin Cargo to
# the MSVC linker so Git's usr/bin/link.exe cannot shadow it.
#
# Usage:
#   source tools/use_msvc_from_git_bash.sh
#   tools/use_msvc_from_git_bash.sh -- cargo test -p classic-config-core --manifest-path ClassicLib-rs/Cargo.toml

classic_use_msvc_from_git_bash() {
  local arch="amd64"
  local powershell_exe=""
  local script_dir=""
  local powershell_script=""
  local env_dump=""
  local name=""
  local encoded=""
  local value=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -a|--arch)
        if [[ $# -lt 2 ]]; then
          printf 'error: --arch requires a value\n' >&2
          return 1
        fi
        arch="$2"
        shift 2
        ;;
      --)
        shift
        break
        ;;
      -h|--help)
        cat <<'EOF'
Usage:
  source tools/use_msvc_from_git_bash.sh [--arch amd64|x86|arm64]
  tools/use_msvc_from_git_bash.sh [--arch amd64|x86|arm64] -- <command> [args...]

Loads the Visual Studio Dev Shell environment into Git Bash and sets
`CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER` to the resolved MSVC `link.exe`.

Examples:
  source tools/use_msvc_from_git_bash.sh
  tools/use_msvc_from_git_bash.sh -- cargo test -p classic-config-core --manifest-path ClassicLib-rs/Cargo.toml
EOF
        return 0
        ;;
      *)
        break
        ;;
    esac
  done

  case "$arch" in
    amd64|x86|arm64)
      ;;
    *)
      printf 'error: unsupported arch %s\n' "$arch" >&2
      return 1
      ;;
  esac

  if command -v pwsh.exe >/dev/null 2>&1; then
    powershell_exe="pwsh.exe"
  elif command -v pwsh >/dev/null 2>&1; then
    powershell_exe="pwsh"
  elif command -v powershell.exe >/dev/null 2>&1; then
    powershell_exe="powershell.exe"
  elif command -v powershell >/dev/null 2>&1; then
    powershell_exe="powershell"
  else
    printf 'error: could not find pwsh or powershell on PATH\n' >&2
    return 1
  fi

  if ! command -v cygpath >/dev/null 2>&1; then
    printf 'error: cygpath is required when running from Git Bash\n' >&2
    return 1
  fi

  if ! command -v base64 >/dev/null 2>&1; then
    printf 'error: base64 is required when running from Git Bash\n' >&2
    return 1
  fi

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || return 1
  powershell_script="$(cygpath -w "$script_dir/enter_vs_dev_shell.ps1")" || return 1

  if ! env_dump="$(
    "$powershell_exe" -NoLogo -NoProfile -ExecutionPolicy Bypass \
      -File "$powershell_script" -Arch "$arch" -EmitEnvironment
  )"; then
    return 1
  fi

  while IFS=$'\t' read -r name encoded; do
    if [[ -z "$name" ]]; then
      continue
    fi

    name="${name%$'\r'}"
    encoded="${encoded%$'\r'}"

    if ! value="$(printf '%s' "$encoded" | base64 --decode)"; then
      printf 'error: failed to decode environment value for %s\n' "$name" >&2
      return 1
    fi

    if [[ "$name" == "PATH" ]]; then
      if ! value="$(cygpath -u -p "$value")"; then
        printf 'error: failed to translate PATH from Windows format\n' >&2
        return 1
      fi
      export PATH="$value"
    else
      export "$name=$value"
    fi
  done <<< "$env_dump"

  hash -r
  printf 'Loaded MSVC environment for Git Bash (%s).\n' "$arch" >&2
  printf 'Cargo linker: %s\n' "${CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER:-unset}" >&2

  if [[ $# -gt 0 ]]; then
    "$@"
  fi
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  classic_use_msvc_from_git_bash "$@"
else
  if ! classic_use_msvc_from_git_bash "$@"; then
    exit 1
  fi

  if [[ $# -eq 0 ]]; then
    printf 'Launching a nested Bash shell with the MSVC environment loaded.\n' >&2
    exec "${SHELL:-bash}" -i
  fi
fi
