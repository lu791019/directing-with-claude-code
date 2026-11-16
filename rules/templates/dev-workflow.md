# 開發流程文件 Templates

## 1. `implementation_plan.md` — 實作計畫

```markdown
# [專案/功能名稱] Implementation Plan

## Intent
[一句話：要解決誰的什麼問題。不寫怎麼做]

## Goal Description
[簡述目標：要建構什麼、解決什麼問題]

## Risk Tier
[高／中／低 + 一句理由。判準見 `~/.claude/rules/common/testing.md`；
高＝金流、資料遺失、對外發送、權限、正式部署。一個案子含多級時逐項標。
repo 有 `REVIEW.md` 時附 `risk-paths --files <Proposed Changes 列的檔>` 結果（寫計畫時還沒有 diff，
用 --base 一定是未命中）；命中＝高，不得調低；exit 2 是錯誤不是未命中]

## Rollback（怎麼撤回）
[壞掉時一步回到原狀的做法：revert 哪個 commit／關哪個 flag／跑哪支 down migration。
資料庫或對外發送類寫清楚「撤不回的部分」，例如已寄出的信、已刪的資料]

## Acceptance Criteria（寫碼前定好，收尾逐條附證據）
- AC1 Given [前提] When [動作] Then [可觀察的結果]
- AC2 ...
- AC3 （至少一條邊界或異常情境：空值、上限、幣別／語系、重複送出、外部服務掛掉）

## User Review Required
> **NOTE**
> [列出關鍵技術決策、使用的框架/工具、以及任何需要使用者確認的假設]

## Proposed Changes

### Project Structure
[描述整體專案結構或變更範圍]

### Components
- `[NEW/MODIFY] path/to/file.ext`
  [描述此檔案的用途與職責]

- `[NEW/MODIFY] path/to/another-file.ext`
  [描述此檔案的用途與職責]

（依實際需求列出所有相關檔案）

## Verification Plan

### Manual Verification
- [驗證步驟 1]
- [驗證步驟 2]
- [驗證步驟 3]

### Automated Tests（如適用）
- [測試項目 1]
- [測試項目 2]
```

## 2. `task.md` — 任務清單

```markdown
# [專案/功能名稱] Tasks

## Project Initialization
- [ ] Create task.md and implementation_plan.md
- [ ] [初始化步驟...]

## Core Implementation
- [ ] [核心功能任務 1]
- [ ] [核心功能任務 2]
- [ ] [核心功能任務 3]

## UI/UX Refinement（如適用）
- [ ] [UI 相關任務]

## Verification
- [ ] Verify functionality with testing
- [ ] Create walkthrough.md
```

> 隨著實作進展，逐步將 `- [ ]` 更新為 `- [x]` 來追蹤完成狀態。

## 3. PLAN.md / GUIDE.md 同步更新

開發任務收尾時，以及需求/架構變更時，同步更新這兩份文件。
更新前先讀目標檔案，沿用既有的標題層級、表格格式、checklist 風格。

### PLAN.md／GUIDE.md 是什麼

- `PLAN.md`：專案願景、架構、目錄結構、各 Phase checklist 與完成狀態、關鍵決策紀錄。
- `GUIDE.md`：快速開始、指令總覽、各流程說明、目前功能狀態、疑難排解。

下面的 § 編號是作者自己專案的章節，換成你的。

### PLAN.md 更新範圍

| 觸發情境 | 更新哪個 Section |
|----------|-----------------|
| Phase/Section 完成 | §11：對應 Phase 標記 ✅、填完成日期、更新 checklist |
| 新增流程/管線 | §6 內容生產管線 或對應架構章節 |
| 架構或目錄結構變更 | §3 目錄結構 |
| 重要決策（技術選型、方案取捨） | §12 關鍵決策紀錄 |

#### Phase 完成格式範例

```markdown
### Phase N：[名稱] ✅ 已完成

**完成日期：** YYYY-MM-DD

**已完成項目：**
- [x] 具體項目 1
- [x] 具體項目 2

**驗證方式：**
- [驗證步驟]

**已知問題：**
- [如有]
```

### GUIDE.md 更新範圍

| 觸發情境 | 更新哪個 Section |
|----------|-----------------|
| 新增 CLI 指令或 IDE skill | §2 指令總覽表格（對應情境分組 A-H） |
| 新增流程/管線 | 對應 Section（含流程圖 + I/O 表） |
| 架構或目錄結構變更 | §7 檔案架構與分類 |
| Phase 完成 | §12 功能狀態表 |

#### 指令總覽表格格式（§2）

```markdown
| 順序 | 指令 | 類型 | 說明 | 輸出位置 |
|:----:|------|:----:|------|----------|
| N | `./bin/agent <cmd> [參數]` | CLI | 一句話說明 | `輸出路徑/` |
| N | `/skill-name` | IDE | 一句話說明 | `輸出路徑/` |
```

### 同時檢查

- 專案 `CLAUDE.md` 指令速查表（如有新增/移除指令）
- `MEMORY.md` 的狀態摘要（如 Phase 完成、已知問題變更）

---

## 4. `walkthrough.md` — 完成總結

```markdown
# [專案/功能名稱] Walkthrough

[一段簡述：完成了什麼、使用了哪些技術、達成了哪些需求]

## Changes Implemented

### [分類 1，例如 Core Features]
- **[功能名稱]**：[簡述實作內容]
- **[功能名稱]**：[簡述實作內容]

### [分類 2，例如 UI/UX]
- **[功能名稱]**：[簡述實作內容]

## Verification Results

### Acceptance Criteria 對照（逐條，不能只寫「測試全過」）
| AC | 結果 | 證據（指令輸出／截圖／DB 查詢／log，附位置） |
|----|------|------|
| AC1 | ✅／❌ | |

### 測試結果
- 總數／綠／紅／略過：
- 失敗項與風險等級：[例：2 項紅，皆為低級文案] 或「無」
- 本次修的 bug 留下的回歸測試：[測試名稱與路徑] 或「無修 bug」
- 高風險項：獨立撰寫測試者／對抗輪結論／突變抽驗結果／Dex 親驗與否
- 獨立 review（中／高）：誰審的、第幾輪收斂、重要 a／小意見 b／既有 c，既有項轉去哪個待辦

### 漏抓檢討（複驗、review 或上線後才發現的 bug 才寫；沒有寫「無」）
| bug | 哪一層本來該抓到 | 補了什麼（測試／REVIEW.md／lint／規則，附路徑） |
|-----|------------------|------|

### [其他實測場景名稱]
- **Action**：[執行了什麼操作]
- **Result**：[觀察到的結果]

## Next Steps
- [後續可擴展的方向 1]
- [後續可擴展的方向 2]
```
