"""鎖 cost-scan 的計數：同一則回應多行要合併，子代理按 agentId 分組。"""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "cost-scan.py"
_spec = importlib.util.spec_from_file_location("cost_scan", SCRIPT)
cost_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cost_scan)


def _line(mid, output, blocks=(), side=True, agent="a1", session="s1", ts="2026-10-01T00:00:00Z"):
    return json.dumps({
        "type": "assistant", "timestamp": ts, "isSidechain": side,
        "sessionId": session, "agentId": agent,
        "message": {
            "id": mid, "model": "claude-sonnet-5-5",
            "usage": {"input_tokens": 1, "output_tokens": output, "cache_read_input_tokens": 100},
            "content": list(blocks),
        },
    })


def _tool(block_id, name="Read"):
    return {"type": "tool_use", "id": block_id, "name": name}


def _scan(tmp_path, lines):
    (tmp_path / "s.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows, _ = cost_scan.scan(str(tmp_path))
    return rows


def test_multiline_response_merges_into_one_row_with_final_output(tmp_path):
    rows = _scan(tmp_path, [_line("m1", 3), _line("m1", 3), _line("m1", 250)])
    assert len(rows) == 1
    assert rows[0]["out"] == 250


def test_tool_use_counts_across_lines_of_same_response(tmp_path):
    rows = _scan(tmp_path, [
        _line("m1", 3),
        _line("m1", 3, [_tool("t1")]),
        _line("m1", 90, [_tool("t2", "Edit")]),
    ])
    assert rows[0]["tools"] == 2


def test_tool_use_block_written_twice_counts_once(tmp_path):
    rows = _scan(tmp_path, [_line("m1", 3, [_tool("t1")]), _line("m1", 3, [_tool("t1")])])
    assert rows[0]["tools"] == 1


def test_subagents_in_same_parent_session_stay_separate(tmp_path):
    rows = _scan(tmp_path, [_line("m1", 5, agent="a1"), _line("m2", 5, agent="a2")])
    assert sorted(r["aid"] for r in rows) == ["a1", "a2"]


@pytest.mark.parametrize("model,tier", [
    ("claude-opus-5-5", "opus55"),
    ("claude-opus-5", "opus"),
    ("claude-sonnet-5-5", "sonnet5"),
    ("claude-haiku-5-5", "haiku"),
    ("claude-fable-5-1", "fable"),
    ("<synthetic>", None),
])
def test_tier_maps_current_models(model, tier):
    assert cost_scan.tier(model) == tier
