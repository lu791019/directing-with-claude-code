"""risk_paths：依變更檔案路徑判風險等級（命中 REVIEW.md 高風險路徑＝高）。"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import risk_paths as rp  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "risk_paths.py"

REVIEW_MD = """# REVIEW.md
## 這裡的壞掉長什麼樣
- 金額不是整數分

## 高風險路徑
```risk-paths
# 金流
src/billing/**
supabase/migrations/**
.github/workflows/*.yml
cloudbuild.yaml
```

## 跳過不審
```
vendor/**
```
"""


def test_parse_reads_only_risk_paths_block_and_skips_comments():
    assert rp.parse_patterns(REVIEW_MD) == [
        "src/billing/**",
        "supabase/migrations/**",
        ".github/workflows/*.yml",
        "cloudbuild.yaml",
    ]


def test_parse_without_block_returns_none():
    assert rp.parse_patterns("# REVIEW.md\n沒有區塊\n") is None


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("src/billing/charge.ts", "src/billing/**", True),
        ("src/billing/deep/a/b.ts", "src/billing/**", True),
        ("src/billingx/a.ts", "src/billing/**", False),
        ("supabase/migrations/041_x.sql", "supabase/migrations/**", True),
        (".github/workflows/ci.yml", ".github/workflows/*.yml", True),
        (".github/workflows/sub/ci.yml", ".github/workflows/*.yml", False),
        ("cloudbuild.yaml", "cloudbuild.yaml", True),
        ("docs/cloudbuild.yaml", "cloudbuild.yaml", False),
        ("cloudbuild.yaml.bak", "cloudbuild.yaml", False),
        ("a/b/secret.env", "**/*.env", True),
        ("secret.env", "**/*.env", True),
    ],
)
def test_match(path, pattern, expected):
    assert rp.matches(path, pattern) is expected


def test_classify_returns_hits_with_pattern():
    hits = rp.classify(
        ["README.md", "src/billing/charge.ts", "cloudbuild.yaml"],
        ["src/billing/**", "cloudbuild.yaml"],
    )
    assert hits == [
        ("src/billing/charge.ts", "src/billing/**"),
        ("cloudbuild.yaml", "cloudbuild.yaml"),
    ]


def test_classify_no_hits():
    assert rp.classify(["README.md"], ["src/billing/**"]) == []


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
    (tmp_path / "REVIEW.md").write_text(REVIEW_MD)
    (tmp_path / "README.md").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _run(repo, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True
    )


def test_cli_low_change_exits_0(repo):
    (repo / "README.md").write_text("y")
    r = _run(repo, "--base", "main")
    assert r.returncode == 0, r.stderr
    assert "未命中" in r.stdout


def test_cli_committed_high_change_exits_3(repo):
    (repo / "src/billing").mkdir(parents=True)
    (repo / "src/billing/charge.ts").write_text("x")
    _git(repo, "switch", "-q", "-c", "feat")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c")
    r = _run(repo, "--base", "main")
    assert r.returncode == 3
    assert "src/billing/charge.ts" in r.stdout and "高" in r.stdout


def test_cli_untracked_high_file_counts(repo):
    (repo / "cloudbuild.yaml").write_text("x")
    r = _run(repo, "--base", "main")
    assert r.returncode == 3
    assert "cloudbuild.yaml" in r.stdout


def test_cli_missing_block_exits_2(repo):
    (repo / "REVIEW.md").write_text("# 空\n")
    r = _run(repo, "--base", "main")
    assert r.returncode == 2
    assert "risk-paths" in r.stderr


def test_cli_missing_review_md_exits_2(repo):
    (repo / "REVIEW.md").unlink()
    r = _run(repo, "--base", "main")
    assert r.returncode == 2


def test_cli_explicit_files_skip_git(repo):
    r = _run(repo, "--files", "supabase/migrations/001.sql", "README.md")
    assert r.returncode == 3
    assert "supabase/migrations/001.sql" in r.stdout


def test_cli_ignores_changes_made_on_base_after_branching(repo):
    # 回歸：base 在分支之後又前進，那些變更不是這個分支的（某 repo 實測誤報 55 檔）
    _git(repo, "switch", "-q", "-c", "feat")
    (repo / "README.md").write_text("feat change")
    _git(repo, "commit", "-qam", "feat")
    _git(repo, "switch", "-q", "main")
    (repo / "src/billing").mkdir(parents=True)
    (repo / "src/billing/charge.ts").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "main moves on")
    _git(repo, "switch", "-q", "feat")
    r = _run(repo, "--base", "main")
    assert r.returncode == 0, r.stdout
    assert "src/billing" not in r.stdout


@pytest.mark.parametrize(
    "path,pattern,expected",
    [
        ("src/lib/auth/x.ts", "src/lib/auth/", True),  # gitignore 式結尾斜線＝整個目錄
        ("src/lib/authx/x.ts", "src/lib/auth/", False),
    ],
)
def test_match_trailing_slash_means_directory(path, pattern, expected):
    assert rp.matches(path, pattern) is expected


def test_cli_files_with_dot_slash_prefix(repo):
    r = _run(repo, "--files", "./src/billing/a.ts")
    assert r.returncode == 3, r.stdout


def test_cli_from_subdirectory_uses_repo_root(repo):
    # 回歸：在子目錄跑時找不到根目錄的 REVIEW.md，高風險被當成「依表判斷」
    (repo / "src/billing").mkdir(parents=True)
    (repo / "src/billing/charge.ts").write_text("x")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "main"],
        cwd=repo / "src",
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3, r.stdout + r.stderr
    assert "src/billing/charge.ts" in r.stdout


def test_cli_rename_out_of_risk_dir_counts_old_path(repo):
    (repo / "src/billing").mkdir(parents=True)
    (repo / "src/billing/charge.ts").write_text("x" * 200)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add billing")
    _git(repo, "switch", "-q", "-c", "feat")
    _git(repo, "mv", "src/billing/charge.ts", "charge.ts")
    _git(repo, "commit", "-qm", "move out")
    r = _run(repo, "--base", "main")
    assert r.returncode == 3, r.stdout
    assert "src/billing/charge.ts" in r.stdout


def test_cli_files_from_subdirectory_resolved_against_cwd(repo):
    # 回歸：子目錄執行 --files 時，路徑相對 cwd，要換算成相對 repo 根目錄再比
    (repo / "src").mkdir()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--files", "billing/charge.ts"],
        cwd=repo / "src",
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3, r.stdout + r.stderr
    assert "src/billing/charge.ts" in r.stdout
