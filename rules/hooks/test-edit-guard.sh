#!/bin/bash
# PreToolUse（matcher: Write|Edit|NotebookEdit）：子代理改測試檔一律記錄；派工單第一行是 TESTS=locked 時擋下。
# 測試：bash ~/.claude/hooks/tests/test-edit-guard.test.sh
# 用途：寫程式的代理不能為了轉綠去改測試（2026-10-26 依〈從怎麼測試到該怎麼測試〉補強）。
# 不擋：主 session（沒有 agent_type）、沒標 TESTS=locked 的子代理（紅燈輪要新增測試）。
# 已知漏洞：Bash 的 sed／重導向寫檔不經過這裡，複驗時仍要看 git diff。
LOG="${TEST_EDIT_GUARD_LOG:-$HOME/.claude/logs/test-edits.jsonl}"
input=$(cat)
agent_type=$(printf '%s' "$input" | jq -r '.agent_type // empty')
[ -n "$agent_type" ] || exit 0
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')
base=$(basename "$path")
case "$path" in
  */tests/*|*/test/*|*/__tests__/*|*/e2e/*|*/spec/*) is_test=true ;;
  *) case "$base" in
       test_*.py|*_test.py|*_test.go|conftest.py|*.test.*|*.spec.*) is_test=true ;;
       *) is_test=false ;;
     esac ;;
esac
[ "$is_test" = true ] || exit 0
agent_id=$(printf '%s' "$input" | jq -r '.agent_id // empty')
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
sub="${transcript%.jsonl}/subagents/agent-${agent_id}.jsonl"
# 只認派工單「第一行」是 TESTS=locked；內文提到這個字（例如「本輪不標 TESTS=locked」）不算
lock_check=ok
if [ ! -f "$sub" ]; then
  lock_check=missing  # 找不到子代理紀錄：放行但記下來，別讓靜默降級看起來像「沒鎖」
  echo "test-edit-guard：找不到子代理紀錄 $sub，無法判斷是否 TESTS=locked（放行並記錄）" >&2
fi
if head -1 "$sub" 2>/dev/null | jq -r '.message.content | if type=="string" then . else (map(.text? // "") | join("\n")) end' 2>/dev/null | head -1 | grep -q '^TESTS=locked'; then
  locked=true
else
  locked=false
fi
mkdir -p "$(dirname "$LOG")"
jq -nc --arg t "$(date -u +%FT%TZ)" --arg type "$agent_type" --arg a "$agent_id" --arg p "$path" \
  --arg tool "$(printf '%s' "$input" | jq -r '.tool_name')" --arg cwd "$(printf '%s' "$input" | jq -r '.cwd // empty')" \
  --argjson locked "$locked" --arg check "$lock_check" \
  '{time:$t,agent_type:$type,agent_id:$a,tool:$tool,path:$p,cwd:$cwd,locked:$locked,blocked:$locked,lock_check:$check}' >> "$LOG"
if [ "$locked" = true ]; then
  echo "這一輪標了 TESTS=locked，不可修改測試檔 ${path}。測試若真的有錯，停下來在回報寫明哪一條、為什麼錯，由主線決定。" >&2
  exit 2
fi
exit 0
