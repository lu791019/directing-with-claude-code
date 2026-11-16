# 四代理流程：PM → SA → PG → QA

流程構想來自工作上同事的設計，這裡是 Dex 移植到 Python 專案後、用自己的說法重寫的版本。

一個功能從需求文件走到測試報告，交給四個角色接力。每一棒只讀上一棒的產物、只寫自己的資料夾，交棒前把沒講清楚的事問完。

| 棒次 | 角色（subagent） | 讀什麼 | 產出什麼（寫到哪） | 拍電影對照 |
|---|---|---|---|---|
| 1 | PM（`pm-expert`，流程細節 `skills/pm-flow`） | `pm/spec_*.md` 需求文件 | 事件風暴、grill 質詢紀錄、業務版 Gherkin（`pm/`） | 劇本大綱 → 分鏡腳本 |
| 2 | SA（`sa-expert`，流程細節 `skills/sa-flow`） | `pm/` 全部產物＋實際專案程式碼 | 技術對照表、技術版 Gherkin、pytest 測試骨架（`sa/`） | 場景搭建＋美術設計 |
| 3 | PG（`pg-expert`） | `sa/` 產物＋QA 交來的紅燈測試 | 開發計畫書（`dev/`）、實作程式碼 | 一幕一幕拍 |
| 4 | QA（`qa-expert`，流程細節 `skills/qa-flow`） | `sa/`、`pm/` 產物 | 測試計畫、各層測試、測試報告（`qa/`） | 試片 |

QA 的紅燈測試先寫、交給 PG 轉綠，所以實際順序是 PM → SA → QA（紅燈）→ PG（轉綠）→ QA（驗證與報告）。

## 每一棒共通的規矩

- **不腦補。** 文件沒定義的欄位、流程、值域，停下來列問題清單，等人回答。
- **計畫先過人。** PG 的開發計畫、QA 的測試計畫，都要等使用者回「確認開始」才動手。
- **只寫自己的資料夾。** PM 寫 `pm/`、SA 寫 `sa/`、PG 寫 `dev/` 與計畫裡列出的程式檔、QA 寫 `qa/`。
- **PG 不改 QA 的測試，QA 不改產品程式碼。** 測試看起來錯了，回報讓人裁決。
- **問題編號全程一組。** PM、SA、QA 的待確認事項都用 `Q-XX`，接續編號，不重編。

## 本資料夾

```
four-agent-flow/
├── agents/          四個 subagent 定義（放 ~/.claude/agents/）
│   ├── pm-expert.md
│   ├── sa-expert.md
│   ├── pg-expert.md
│   └── qa-expert.md
└── skills/          三份流程細節（放 ~/.claude/skills/）
    ├── pm-flow/SKILL.md
    ├── sa-flow/SKILL.md
    └── qa-flow/SKILL.md
```

流程裡提到的 `grill-me`（決策樹質詢）、`no-hallucination`（不腦補）、`spec-html`（給客戶回填的規格頁）、`uat-report`（實機驗收報告）是另外的 skill，本 repo 沒有收錄；沒有它們時，照各檔裡寫的原則手動做即可。

授權：不在本 repo 的 AGPL-3.0 授權範圍內，見 `LICENSE-NOTICE.md`。
