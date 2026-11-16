# NOTICE

這個 repo 有兩類內容，授權不同。

## 一、作者自己做的（AGPL-3.0，見 `LICENSE`）

- `README.md` 的拍電影對照與教學內容
- `chief-of-staff/`：幕僚長與 CXO 組織
- `handoff/`：交接檔的寫法由作者從自己多個專案的交接檔整理；「用交接檔取代續接對話」的做法參考了工作上團隊的經驗
- `work-item-ops/`：概念來自團隊的工單流程，程式與文字是重新寫的通用版
- `rules/`：風險分級、測試、code review 規則、開發文件範本、test-edit-guard hook（`rules/agents.md` 除外）

## 二、由公司團隊的做法調整而來（不在 AGPL-3.0 授權範圍內）

- `four-agent-flow/`
- `dispatch-round/`
- `ux-blackbox-trial/`
- `keepwarm/`

這些資料夾的內容由作者參考公司團隊的做法調整、重寫而成，用來說明作者自己的工作流程，僅供閱讀參考，不在本 repo 的 AGPL-3.0 授權範圍內；要再利用請先取得原團隊同意。各資料夾另附 `LICENSE-NOTICE.md`。

## 其他

- `rules/agents.md`、`rules/testing.md`、`rules/code-review.md`：底稿來自開源專案 everything-claude-code（MIT License，Copyright (c) 2026 Affaan Mustafa）的 `rules/common/`。`agents.md` 為原文；`testing.md`、`code-review.md` 由作者大幅改寫（風險分級、測試鎖定、回報格式、收斂上限）。原專案的 MIT 授權聲明適用於這些檔案中沿用的部分。
- 引用的公開文章：Felix Rieseberg〈Made by mechanical means〉、Anthropic〈Solving code review at Anthropic〉、Nielsen 十項啟發式。
