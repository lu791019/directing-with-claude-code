#!/bin/bash
# test-edit-guard.sh 的情境測試。用法：bash hooks/tests/test-edit-guard.test.sh
# 用暫存 log，不寫進正式的 ~/.claude/logs/test-edits.jsonl
HOOK="${HOOK:-$(cd "$(dirname "$0")/.." && pwd)/test-edit-guard.sh}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/sess/subagents"
export TEST_EDIT_GUARD_LOG="$T/log.jsonl"
mk(){ jq -nc --arg c "$2" '{type:"user",message:{role:"user",content:$c}}' > "$T/sess/subagents/agent-$1.jsonl"; }
mk L $'TESTS=locked\n你的任務：修正輪'
mk U $'紅燈輪：寫測試'
mk M $'你的任務：紅燈輪。注意本輪不標 TESTS=locked，因為要新增測試'
J(){ printf '{"tool_name":"Edit","agent_type":"%s","agent_id":"%s","transcript_path":"%s/sess.jsonl","cwd":"/x","tool_input":{"file_path":"%s"}}' general "$1" "$T" "$2"; }
fail=0
case_(){ printf '%s' "$2" | bash "$HOOK" >/dev/null 2>"$T/err"; got=$?
  if [ "$got" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1（exit=$got 期望 $3）"; fail=1; fi; }
case_ "主 session 改測試檔不擋" "$(printf '{"tool_name":"Edit","transcript_path":"%s/sess.jsonl","tool_input":{"file_path":"/r/tests/test_a.py"}}' "$T")" 0
case_ "locked 改 tests/ 擋" "$(J L /r/tests/test_a.py)" 2
case_ "locked 改 foo.spec.ts 擋" "$(J L /r/src/foo.spec.ts)" 2
case_ "locked 改 conftest.py 擋" "$(J L /r/conftest.py)" 2
case_ "locked 改實作檔不擋" "$(J L /r/src/app.py)" 0
case_ "未 locked 改測試不擋" "$(J U /r/tests/test_b.py)" 0
case_ "內文提到 TESTS=locked 但第一行不是＝不擋" "$(J M /r/tests/test_c.py)" 0
case_ "找不到子代理紀錄檔＝不擋但要記 missing" "$(J NOPE /r/tests/test_d.py)" 0
if jq -e 'select(.agent_id=="NOPE") | .lock_check=="missing"' "$TEST_EDIT_GUARD_LOG" >/dev/null 2>&1; then echo "PASS missing 有記進 log"; else echo "FAIL missing 沒記進 log"; fail=1; fi
exit $fail
