#!/usr/bin/env python3
"""平行代理的檔案歸屬核對：代理分支改到的檔，必須全部落在計畫「ownership 區塊」分給它的 glob 內。

平行派工要先定介面與檔案歸屬（Felix Rieseberg〈Made by mechanical means〉：每卷帶子一個檔、
統一介面，thread 才能同時做而不互踩）。歸屬表寫在 implementation_plan.md：

  ```ownership
  shared: src/tapes/registry.ts      # 共用檔：主線先 commit，代理只能讀，誰改都算越界
  tape-notion: src/tapes/notion/**   # 一行一個，`名稱: glob`，`#` 開頭或行尾是註解
  tape-slack: src/tapes/slack/       # 結尾斜線＝整個目錄
  ```

用法：
  check_ownership --plan implementation_plan.md --agent tape-notion --base main    # 複驗：分岔點以來改了什麼
  check_ownership --plan implementation_plan.md --agent tape-notion --files a.ts   # 規劃：這些檔它能不能動
離開碼：0＝全在範圍內、3＝有越界、2＝錯誤（沒有區塊、代理不在表上、git 失敗）——2 不可當成通過。
glob 比對沿用 risk_paths.matches（`**`、結尾 `/`＝整個目錄、相對 repo 根目錄）。
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risk_paths import changed_files, matches, repo_root, to_repo_relative  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_VIOLATION = 0, 2, 3
SHARED = "shared"
BLOCK_RE = re.compile(r"^```ownership[ \t]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def parse_ownership(plan_md: str) -> dict[str, list[str]] | None:
    """讀 ```ownership 區塊 → {名稱: [glob, ...]}；沒有區塊回 None；格式錯丟 ValueError。"""
    m = BLOCK_RE.search(plan_md)
    if not m:
        return None
    owners: dict[str, list[str]] = {}
    for raw in m.group(1).splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(
                f"ownership 區塊這行沒有冒號（格式：名稱: glob）：{raw.strip()}"
            )
        name, glob = (s.strip() for s in line.split(":", 1))
        if not name or not glob:
            raise ValueError(f"ownership 區塊這行名稱或 glob 是空的：{raw.strip()}")
        owners.setdefault(name, []).append(glob)
    return owners


def _owner_of(
    path: str, owners: dict[str, list[str]], exclude: tuple[str, ...]
) -> str | None:
    return next(
        (
            name
            for name, globs in owners.items()
            if name not in exclude and any(matches(path, g) for g in globs)
        ),
        None,
    )


def check(
    files: list[str], owners: dict[str, list[str]], agent: str
) -> list[tuple[str, str]]:
    """回傳越界清單 [(檔案, 原因)]。共用檔優先判：就算也落在代理自己的 glob 內，仍算越界。"""
    mine = owners[agent]  # 代理不在表上 → KeyError，呼叫端轉成 exit 2
    violations = []
    for path in files:
        if any(matches(path, g) for g in owners.get(SHARED, [])):
            violations.append((path, f"共用檔 {SHARED}"))
        elif any(matches(path, g) for g in mine):
            # glob 重疊（例如 a: src/** 蓋住 b: src/b/**）：同時屬於別的代理也算越界，SKILL 要求歸屬不相交
            other = _owner_of(path, owners, exclude=(agent, SHARED))
            if other:
                violations.append((path, f"歸屬重疊：也屬於 {other}"))
        else:
            other = _owner_of(path, owners, exclude=(agent, SHARED))
            violations.append((path, f"屬於 {other}" if other else "不屬於任何代理"))
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--plan", default="implementation_plan.md", help="含 ```ownership 區塊的計畫檔"
    )
    ap.add_argument(
        "--agent", required=True, help="要核對的代理名稱（區塊裡冒號前的名稱）"
    )
    src = ap.add_mutually_exclusive_group(
        required=True
    )  # 兩者都沒給 → argparse 自己以 exit 2 結束
    src.add_argument(
        "--base", help="複驗：從 merge-base 到工作區的變更（含未 commit、未追蹤）"
    )
    src.add_argument("--files", nargs="+", help="規劃：直接判斷這些路徑（相對 cwd）")
    args = ap.parse_args(argv)

    try:
        plan_md = Path(args.plan).read_text(encoding="utf-8")
    except OSError as e:
        print(f"錯誤：讀不到計畫檔 {args.plan}（{e.strerror}）", file=sys.stderr)
        return EXIT_ERROR
    try:
        owners = parse_ownership(plan_md)
    except ValueError as e:
        print(f"錯誤：{e}", file=sys.stderr)
        return EXIT_ERROR
    if owners is None:
        print(
            f"錯誤：{args.plan} 沒有 ```ownership 區塊；平行輪的計畫必須先定檔案歸屬",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if args.agent not in owners:
        known = "、".join(n for n in owners if n != SHARED) or "（無）"
        print(
            f"錯誤：代理 {args.agent} 不在 ownership 區塊裡（表上有：{known}）",
            file=sys.stderr,
        )
        return EXIT_ERROR

    root = repo_root()
    if args.files:
        files = to_repo_relative(args.files, root)
    else:
        if root is None:
            print("錯誤：不在 git repo 內，--base 無法比對", file=sys.stderr)
            return EXIT_ERROR
        try:
            files = changed_files(args.base, root)
        except subprocess.CalledProcessError as e:
            print(
                f"錯誤：git 失敗：{e.stderr.strip() if e.stderr else e}",
                file=sys.stderr,
            )
            return EXIT_ERROR

    violations = check(files, owners, args.agent)
    if violations:
        for path, reason in violations:
            print(f"越界：{path}（{reason}）")
        print(
            f"越界 {len(violations)} 檔／共 {len(files)} 檔變更；代理 {args.agent} 只能動：{'、'.join(owners[args.agent])}"
        )
        return EXIT_VIOLATION
    print(f"在範圍內：{len(files)} 檔變更全部屬於 {args.agent}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
