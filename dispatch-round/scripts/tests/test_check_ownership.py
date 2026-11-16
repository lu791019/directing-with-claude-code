"""check_ownership：平行代理只能改計畫「ownership 區塊」分給它的檔；共用檔（shared）一律不可改。"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_ownership as co  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "check_ownership.py"

PLAN_MD = """# Implementation Plan
## 介面與檔案歸屬（平行輪）
```ownership
# 共用介面：主線先 commit，代理只能讀
shared: src/tapes/registry.ts
shared: src/tapes/types.ts
# 各代理擁有的檔
tape-notion: src/tapes/notion/**
tape-notion: src/tapes/notion.ts
tape-slack: src/tapes/slack/
```
"""


def test_parse_reads_block_groups_by_owner_and_skips_comments():
    assert co.parse_ownership(PLAN_MD) == {
        "shared": ["src/tapes/registry.ts", "src/tapes/types.ts"],
        "tape-notion": ["src/tapes/notion/**", "src/tapes/notion.ts"],
        "tape-slack": ["src/tapes/slack/"],
    }


def test_parse_without_block_returns_none():
    assert co.parse_ownership("# plan\n沒有區塊\n") is None


def test_parse_malformed_line_raises():
    with pytest.raises(ValueError, match="沒有冒號"):
        co.parse_ownership("```ownership\nsrc/a/**\n```\n")


OWNERS = co.parse_ownership(PLAN_MD)


def test_check_in_scope_is_clean():
    assert (
        co.check(
            ["src/tapes/notion/draw.ts", "src/tapes/notion.ts"], OWNERS, "tape-notion"
        )
        == []
    )


def test_check_flags_file_owned_by_another_agent():
    assert co.check(["src/tapes/slack/draw.ts"], OWNERS, "tape-notion") == [
        ("src/tapes/slack/draw.ts", "屬於 tape-slack")
    ]


def test_check_flags_shared_file_even_if_pattern_overlaps_agent():
    owners = {"shared": ["src/tapes/types.ts"], "a": ["src/tapes/**"]}
    assert co.check(["src/tapes/types.ts"], owners, "a") == [
        ("src/tapes/types.ts", "共用檔 shared")
    ]


def test_check_flags_unowned_file():
    assert co.check(["README.md"], OWNERS, "tape-notion") == [
        ("README.md", "不屬於任何代理")
    ]


def test_check_trailing_slash_means_whole_directory():
    assert co.check(["src/tapes/slack/deep/x.ts"], OWNERS, "tape-slack") == []


def test_check_unknown_agent_raises():
    with pytest.raises(KeyError):
        co.check([], OWNERS, "nobody")


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
        },
    )


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "implementation_plan.md").write_text(PLAN_MD)
    (tmp_path / "src/tapes/notion").mkdir(parents=True)
    (tmp_path / "src/tapes/slack").mkdir(parents=True)
    (tmp_path / "src/tapes/registry.ts").write_text("export const tapes = []")
    (tmp_path / "src/tapes/notion.ts").write_text("x")
    (tmp_path / "README.md").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "switch", "-q", "-c", "agent/tape-notion")
    return tmp_path


def _run(repo, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or repo,
        capture_output=True,
        text=True,
    )


def test_cli_untracked_file_in_own_dir_exits_0(repo):
    (repo / "src/tapes/notion/draw.ts").write_text("x")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 0, r.stderr
    assert "在範圍內" in r.stdout


def test_cli_committed_change_to_other_agents_file_exits_3(repo):
    (repo / "src/tapes/slack/draw.ts").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "oops")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 3
    assert "src/tapes/slack/draw.ts" in r.stdout and "tape-slack" in r.stdout


def test_cli_editing_shared_file_exits_3(repo):
    (repo / "src/tapes/registry.ts").write_text("export const tapes = ['notion']")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 3
    assert "registry.ts" in r.stdout and "共用檔" in r.stdout


def test_cli_rename_out_of_own_dir_exits_3(repo):
    _git(repo, "mv", "src/tapes/notion.ts", "src/tapes/slack/notion.ts")
    _git(repo, "commit", "-qm", "move")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 3
    assert "src/tapes/slack/notion.ts" in r.stdout


def test_cli_files_from_subdirectory_resolves_against_repo_root(repo):
    sub = repo / "src/tapes/notion"
    r = _run(
        repo,
        "--plan",
        str(repo / "implementation_plan.md"),
        "--agent",
        "tape-notion",
        "--files",
        "draw.ts",
        cwd=sub,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    r = _run(
        repo,
        "--plan",
        str(repo / "implementation_plan.md"),
        "--agent",
        "tape-notion",
        "--files",
        "../slack/draw.ts",
        cwd=sub,
    )
    assert r.returncode == 3


def test_cli_plan_without_block_exits_2(repo):
    (repo / "implementation_plan.md").write_text("# plan\n")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 2
    assert "ownership" in r.stderr


def test_cli_unknown_agent_exits_2(repo):
    r = _run(
        repo, "--plan", "implementation_plan.md", "--agent", "nobody", "--base", "main"
    )
    assert r.returncode == 2
    assert "nobody" in r.stderr


def test_cli_missing_plan_file_exits_2(repo):
    r = _run(repo, "--plan", "nope.md", "--agent", "tape-notion", "--base", "main")
    assert r.returncode == 2


def test_cli_requires_base_or_files(repo):
    r = _run(repo, "--plan", "implementation_plan.md", "--agent", "tape-notion")
    assert r.returncode == 2


def test_check_flags_file_that_also_matches_another_agent():
    """glob 重疊（a: src/** 蓋住 b: src/b/**）：檔案同時屬於兩個代理，誰改都算越界，工具要抓到。"""
    owners = {"a": ["src/**"], "b": ["src/b/**"]}
    assert co.check(["src/b/x.ts"], owners, "a") == [
        ("src/b/x.ts", "歸屬重疊：也屬於 b")
    ]
    assert co.check(["src/b/x.ts"], owners, "b") == [
        ("src/b/x.ts", "歸屬重疊：也屬於 a")
    ]
    assert co.check(["src/a/x.ts"], owners, "a") == []


def test_cli_overlapping_ownership_exits_3(repo):
    (repo / "implementation_plan.md").write_text(
        "```ownership\ntape-notion: src/tapes/**\ntape-slack: src/tapes/slack/\n```\n"
    )
    (repo / "src/tapes/slack/draw.ts").write_text("x")
    r = _run(
        repo,
        "--plan",
        "implementation_plan.md",
        "--agent",
        "tape-notion",
        "--base",
        "main",
    )
    assert r.returncode == 3
    assert "歸屬重疊" in r.stdout and "tape-slack" in r.stdout
