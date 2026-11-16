# dispatch-round：分輪派工

主線（主對話）寫派工單、裁決、複驗、入庫；子代理一輪只做一件事的紅燈→綠燈。流程本體在 `SKILL.md`，放進 `~/.claude/skills/dispatch-round/` 即可使用。

- `scripts/risk_paths.py`：讀 repo 的 `REVIEW.md` 判斷改動是否命中高風險路徑。
- `scripts/check_ownership.py`：平行派工時核對每個代理有沒有改到不屬於它的檔。
- `scripts/cost-scan.py`：掃 `~/.claude/projects` 的 session 記錄，換算 API 等值成本。成本模型請依自己的用量記錄。
- 測試：`python3 -m pytest scripts/tests`。

內容由 Dex 參考公司團隊的做法調整、重寫而成，用來說明自己的工作流程，不在本 repo 的 AGPL-3.0 授權範圍內，見 `LICENSE-NOTICE.md`。
