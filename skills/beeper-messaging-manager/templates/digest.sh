#!/usr/bin/env bash
# Beeper digest collector — emits ranked-unread JSON to stdout.
# A scheduled agent run (Hermes cron, OpenCode task, or plain cron→prompt)
# reasons over this output into a human phone-glance digest.
#
# CRITICAL: always --target desktop. On most workstations the default CLI
# target is the managed beeper-server (:23374), which is frequently
# unreachable or still initializing; without the override, commands silently
# return {"data":[]} and look like an empty inbox. See the skill's pitfalls.
#
# Usage:  digest.sh [TOP_N] [CONTEXT_MSGS]
#   TOP_N         how many top unread chats to include (default 15)
#   CONTEXT_MSGS  recent messages to pull per chat (default 3)
#
# Requires: `beeper` (@beeper/cli) and `jq` on PATH. If `beeper` is not on the
# scheduler's narrow PATH, set BEEPER_BIN to its absolute path.
set -euo pipefail

BEEPER="${BEEPER_BIN:-beeper}"
TARGET="${BEEPER_TARGET:-desktop}"
TOP_N="${1:-15}"
CTX="${2:-3}"

chats_json="$("$BEEPER" chats list --target "$TARGET" \
  --unread --no-muted --no-low-priority --no-archived \
  --limit "$TOP_N" --json 2>/dev/null || echo '{"data":[]}')"

echo '{'
echo '  "generated_at": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",'
echo '  "chats": ['
first=1
echo "$chats_json" | jq -c '.data[]?' 2>/dev/null | while read -r chat; do
  cid="$(echo "$chat" | jq -r '.id // .chatID // .localChatID // empty')"
  [ -z "$cid" ] && continue
  title="$(echo "$chat" | jq -r '.title // "<untitled>"')"
  net="$(echo "$chat" | jq -r '.network // "?"')"
  unread="$(echo "$chat" | jq -r '.unreadCount // 0')"
  is_dm="$(echo "$chat" | jq -r 'if (.participants|length? // 0) <= 2 or .type=="single" then "true" else "false" end' 2>/dev/null || echo false)"
  # Recent context: real content rows only (drop reaction/pseudo-message rows).
  msgs="$("$BEEPER" messages list --target "$TARGET" --chat "$cid" --limit "$CTX" --json 2>/dev/null \
    | jq -c '[.data[]? | select((.isHidden|not) and (.type=="TEXT" or .type=="IMAGE" or .type=="VIDEO" or .type=="AUDIO" or .type=="FILE" or .type=="STICKER"))
             | {ts:.timestamp, from:(.senderName // .senderID), type:.type, text:(.text // "")}]' 2>/dev/null || echo '[]')"
  [ "$first" -eq 0 ] && echo ','
  first=0
  jq -n --arg id "$cid" --arg title "$title" --arg net "$net" \
        --argjson unread "$unread" --arg dm "$is_dm" --argjson msgs "$msgs" \
        '{id:$id, title:$title, network:$net, unread:$unread, is_dm:($dm=="true"), recent:$msgs}'
done
echo '  ]'
echo '}'
