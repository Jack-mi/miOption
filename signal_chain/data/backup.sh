#!/bin/zsh
set -eu
umask 077
cd /Users/miller/Projects/miOption
folder="${MIOPTION_BACKUP_DIR:-$HOME/.local/share/mioption/backups}"
mkdir -p "$folder"
output="$folder/public-$(date +%Y%m%d-%H%M%S).sql"
trap 'rm -f "$output"' EXIT
/opt/homebrew/bin/supabase db dump --linked --schema public --data-only --file "$output"
test -s "$output"
/usr/bin/grep -q 'Data for Name: macro_observations' "$output"
trap - EXIT
