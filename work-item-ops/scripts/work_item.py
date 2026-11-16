#!/usr/bin/env python3
"""案子做完時回報工單：留言說明做了什麼、指派回負責人、改成待驗收狀態，可連上層工單一起改。

預設只預覽（dry-run），加 --apply 才真的寫入。寫入前會先確認狀態名存在。

範例：
  python3 work_item.py --repo owner/name finish --issue 42 \\
      --comment-file done.md --assignee reviewer-login --status 待驗收
  python3 work_item.py --repo owner/name finish --issue 42 --parent 40 \\
      --comment "做完了，見 PR #43" --assignee reviewer-login --status 待驗收 --apply
  python3 work_item.py --repo owner/name statuses

預設工單系統是 GitHub Issues（用 gh CLI），狀態用 label 表示，label 名稱前綴預設 `status:`。
換成其他系統：照 Tracker 介面寫一個類別，在 TRACKERS 註冊即可。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Protocol


class TrackerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Item:
    number: str
    title: str
    status: str | None
    assignees: tuple[str, ...]


class Tracker(Protocol):
    """換工單系統時要實作的介面。讀取方法在 dry-run 也會呼叫；寫入方法只在 --apply 時呼叫。"""

    def get(self, number: str) -> Item: ...
    def statuses(self) -> list[str]: ...
    def comment(self, number: str, body: str) -> None: ...
    def assign(self, number: str, assignee: str) -> None: ...
    def set_status(self, number: str, status: str) -> None: ...


@dataclass
class GitHubIssues:
    """GitHub Issues：狀態用 `<prefix><狀態名>` 的 label 表示，同一時間只留一個狀態 label。"""

    repo: str
    prefix: str = "status:"
    runner: object = field(default=None, repr=False)

    def _gh(self, *args: str) -> str:
        cmd = ["gh", *args, "--repo", self.repo]
        run = self.runner or subprocess.run
        result = run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise TrackerError(f"gh 失敗（{' '.join(args[:2])}）：{result.stderr.strip()}")
        return result.stdout

    def statuses(self) -> list[str]:
        labels = json.loads(self._gh("label", "list", "--limit", "500", "--json", "name"))
        return sorted(l["name"][len(self.prefix):] for l in labels if l["name"].startswith(self.prefix))

    def get(self, number: str) -> Item:
        data = json.loads(self._gh("issue", "view", number, "--json", "number,title,labels,assignees"))
        status = next((l["name"][len(self.prefix):] for l in data["labels"] if l["name"].startswith(self.prefix)), None)
        return Item(str(data["number"]), data["title"], status, tuple(a["login"] for a in data["assignees"]))

    def comment(self, number: str, body: str) -> None:
        self._gh("issue", "comment", number, "--body", body)

    def assign(self, number: str, assignee: str) -> None:
        self._gh("issue", "edit", number, "--add-assignee", assignee)

    def set_status(self, number: str, status: str) -> None:
        current = self.get(number).status
        args = ["issue", "edit", number, "--add-label", self.prefix + status]
        if current and current != status:
            args += ["--remove-label", self.prefix + current]
        self._gh(*args)


TRACKERS = {"github": GitHubIssues}


@dataclass(frozen=True)
class Step:
    number: str
    action: str
    detail: str


def plan_finish(tracker: Tracker, numbers: list[str], comment: str | None, assignee: str | None, status: str) -> list[Step]:
    """只讀：確認狀態名存在、工單讀得到，回傳要做的步驟。"""
    known = tracker.statuses()
    if status not in known:
        raise TrackerError(f"狀態「{status}」不存在。現有狀態：{'、'.join(known) or '（沒有）'}")
    steps: list[Step] = []
    for i, number in enumerate(numbers):
        item = tracker.get(number)
        label = f"#{item.number} {item.title}"
        if comment and i == 0:
            steps.append(Step(number, "comment", f"{label}：留言 {len(comment)} 字"))
        if assignee and assignee not in item.assignees:
            steps.append(Step(number, "assign", f"{label}：指派給 {assignee}"))
        if item.status != status:
            steps.append(Step(number, "set_status", f"{label}：狀態 {item.status or '（無）'} → {status}"))
    return steps


def apply_steps(tracker: Tracker, steps: list[Step], comment: str | None, assignee: str | None, status: str) -> None:
    for s in steps:
        if s.action == "comment":
            tracker.comment(s.number, comment or "")
        elif s.action == "assign":
            tracker.assign(s.number, assignee or "")
        elif s.action == "set_status":
            tracker.set_status(s.number, status)
        print(f"已完成：{s.detail}")


def read_comment(args: argparse.Namespace) -> str | None:
    if args.comment_file:
        with open(args.comment_file, encoding="utf-8") as f:
            return f.read().strip()
    return args.comment


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracker", choices=sorted(TRACKERS), default="github")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--status-prefix", default="status:", help="狀態 label 的前綴（GitHub 用）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("statuses", help="列出現有狀態名（只讀）")
    f = sub.add_parser("finish", help="案子做完：留言、指派回負責人、改狀態")
    f.add_argument("--issue", required=True, help="工單編號")
    f.add_argument("--parent", action="append", default=[], help="一起改狀態的上層工單編號，可重複")
    g = f.add_mutually_exclusive_group()
    g.add_argument("--comment", help="留言內容")
    g.add_argument("--comment-file", help="留言內容的檔案（markdown）")
    f.add_argument("--assignee", help="指派回的負責人帳號")
    f.add_argument("--status", required=True, help="目標狀態，例如：待驗收")
    f.add_argument("--apply", action="store_true", help="真的寫入；不加就只預覽")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tracker = TRACKERS[args.tracker](repo=args.repo, prefix=args.status_prefix)
    try:
        if args.cmd == "statuses":
            print("\n".join(tracker.statuses()) or "（沒有狀態 label）")
            return 0
        comment = read_comment(args)
        steps = plan_finish(tracker, [args.issue, *args.parent], comment, args.assignee, args.status)
        if not steps:
            print("已經是目標狀態，沒有要做的事。")
            return 0
        print(("將執行：" if args.apply else "預覽（加 --apply 才會寫入）："))
        for s in steps:
            print(f"- {s.detail}")
        if args.apply:
            apply_steps(tracker, steps, comment, args.assignee, args.status)
        return 0
    except TrackerError as e:
        print(f"錯誤：{e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
