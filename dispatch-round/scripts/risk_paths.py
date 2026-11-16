#!/usr/bin/env python3
"""依變更檔案的路徑判風險等級：命中 repo 根目錄 REVIEW.md 的高風險路徑＝高。

風險等級由「改了什麼」決定，不由寫的人自報（〈Solving code review at Anthropic〉）。
高風險路徑寫在 REVIEW.md 的 ```risk-paths 區塊，一行一個 glob，`#` 開頭是註解。

用法：
  risk-paths [--base main]          # 比對 base 到工作區（含未 commit、未追蹤）的變更
  risk-paths --files a.ts b.sql     # 直接判斷給定的路徑
離開碼：0＝未命中、3＝命中（高）、2＝錯誤（找不到 REVIEW.md 或區塊、git 失敗）——2 不可當成未命中。
規劃階段還沒有 diff，用 --files 帶計畫要動的檔；複驗時再用 --base。
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

EXIT_LOW, EXIT_ERROR, EXIT_HIGH = 0, 2, 3
BLOCK_RE = re.compile(r"^```risk-paths[ \t]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def parse_patterns(review_md: str) -> list[str] | None:
    m = BLOCK_RE.search(review_md)
    if not m:
        return None
    lines = (ln.strip() for ln in m.group(1).splitlines())
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _glob_to_regex(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, pattern: str) -> bool:
    path = path.removeprefix("./")
    if pattern.endswith("/"):  # gitignore 式寫法：結尾斜線＝整個目錄
        pattern += "**"
    return _glob_to_regex(pattern.removeprefix("./")).match(path) is not None


def classify(paths: list[str], patterns: list[str]) -> list[tuple[str, str]]:
    hits = []
    for path in paths:
        hit = next((p for p in patterns if matches(path, p)), None)
        if hit:
            hits.append((path, hit))
    return hits


def _git_lines(root: Path, *args: str) -> list[str]:
    r = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return [ln for ln in r.stdout.splitlines() if ln]


def repo_root() -> Path | None:
    try:
        return Path(_git_lines(Path.cwd(), "rev-parse", "--show-toplevel")[0])
    except (subprocess.CalledProcessError, IndexError):
        return None


def to_repo_relative(files: list[str], root: Path | None) -> list[str]:
    """--files 的路徑相對於 cwd；換算成相對 repo 根目錄，才能和 REVIEW.md 的規則比。"""
    if root is None:
        return files
    top = root.resolve()
    out = []
    for f in files:
        full = (Path.cwd() / f).resolve()
        out.append(full.relative_to(top).as_posix() if full.is_relative_to(top) else f)
    return out


def changed_files(base: str, root: Path) -> list[str]:
    # 從分岔點比，不從 base 的最新 commit 比：base 之後前進的變更不屬於這個分支
    fork_point = _git_lines(root, "merge-base", base, "HEAD")[0]
    # --no-renames：檔案搬出高風險目錄時，舊路徑也要算
    tracked = _git_lines(root, "diff", "--name-only", "--no-renames", fork_point)
    untracked = _git_lines(root, "ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked) | set(untracked))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="依變更路徑判風險等級")
    ap.add_argument("--base", default="main", help="比對基準（預設 main）")
    ap.add_argument("--review-md", help="REVIEW.md 路徑（預設 repo 根目錄）")
    ap.add_argument("--files", nargs="+", help="直接給路徑，不讀 git")
    args = ap.parse_args(argv)

    root = repo_root()
    if root is None and not args.files:
        print("risk-paths：不在 git repo 裡（錯誤，不是未命中）", file=sys.stderr)
        return EXIT_ERROR
    review_path = (
        Path(args.review_md) if args.review_md else (root or Path.cwd()) / "REVIEW.md"
    )
    if not review_path.is_file():
        print(
            f"risk-paths：找不到 {review_path}（範本見 ~/.claude/templates/REVIEW.md）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    patterns = parse_patterns(review_path.read_text(encoding="utf-8"))
    if patterns is None:
        print(f"risk-paths：{review_path} 沒有 ```risk-paths 區塊", file=sys.stderr)
        return EXIT_ERROR

    try:
        paths = (
            to_repo_relative(args.files, root)
            if args.files
            else changed_files(args.base, root)
        )
    except subprocess.CalledProcessError as e:
        print(
            f"risk-paths：git 失敗（錯誤，不是未命中）：{e.stderr.strip()}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    hits = classify(paths, patterns)
    if not hits:
        print(
            f"未命中高風險路徑（{len(paths)} 個變更檔）——等級照 implementation_plan 判定"
        )
        return EXIT_LOW
    print(f"風險等級：高（{len(hits)}／{len(paths)} 個變更檔命中，計畫不得調低）")
    for path, pattern in hits:
        print(f"  {path}  ← {pattern}")
    return EXIT_HIGH


if __name__ == "__main__":
    sys.exit(main())
