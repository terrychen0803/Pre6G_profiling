#!/usr/bin/env bash
set -u

if [ "$#" -lt 2 ]; then
  echo "usage: run-recorded-command.sh OUTPUT_PREFIX COMMAND [ARG ...]" >&2
  exit 64
fi

prefix="$1"
shift
mkdir -p "$(dirname "$prefix")"

{
  printf 'start=%s\n' "$(date --iso-8601=seconds)"
  printf 'cwd=%q\n' "$PWD"
  printf 'command='
  printf '%q ' "$@"
  printf '\n'
} >"${prefix}.meta"

set +e
"$@" \
  > >(tee "${prefix}.stdout") \
  2> >(tee "${prefix}.stderr" >&2)
rc=$?
set -e

{
  printf 'end=%s\n' "$(date --iso-8601=seconds)"
  printf 'exit_code=%s\n' "$rc"
} >>"${prefix}.meta"
printf '%s\n' "$rc" >"${prefix}.exit-code"

exit "$rc"
