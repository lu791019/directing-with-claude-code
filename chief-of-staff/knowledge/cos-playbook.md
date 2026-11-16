# CoS 幕僚長 — 派遣與操作手冊

## 派遣模式選擇

CoS 根據任務性質選擇派遣模式：

| 條件 | 模式 | 說明 |
|------|------|------|
| 單一 CXO 任務 | **Subagent 模式** | 用 Agent tool 派遣 `cxo-executor`（見模式 A） |
| 需要 ≥2 CXO 協作的任務 | **Agent Team 模式** | 啟動 Agent Team，CoS 為 Team Lead |
| `/board` 策略討論 | **主 session 扮演**（預設） | 依序扮演 CXO 視角 |
| `/board` 需要深入研究 | **Agent Team 模式**（可選） | CoS 建議切換，Dex 確認後啟動 |

---

## 模式 A：單一 CXO Subagent 派遣

用 Agent tool，`subagent_type: "cxo-executor"`（定義檔 `~/daydreamdex/agents/cxo-executor.md`，symlink 到 `~/.claude/agents/`）。prompt 第一行固定是 CXO 代號，其餘只寫任務；讀哪些檔、寫入範圍、回報格式都寫在定義檔裡，不用重複：

```
CXO={cmo|cpo|clo|edu|cto|coo|cfo|techconsult|founder}
任務：{具體描述}
```

- executor 工具：Read, Grep, Glob, Write, Edit, WebSearch, WebFetch（沒有 Bash，不能 commit、push、跑 CLI）。
- 寫入範圍：`knowledge/{cxo}/`（草稿在 `knowledge/{cxo}/drafts/`）；CMO 另可寫社群草稿目錄。每筆寫入由 `hooks/cxo-write-guard.sh` 記到 `state/logs/cxo-writes.jsonl`，2026-10-20 前只記錄不阻擋。
- 回報三段：成果／關鍵決策／待辦，每條標 `[已驗證]`、`[完成未驗證]` 或 `[卡住]`。
- **一律前景派遣**（不用 run_in_background）：背景派遣時 post-agent 提醒的時間點未驗證，可能早於回報。
- 休眠代號（見 `state/cxo-roster.md`）：prompt 第二行要有 `WAKE=confirmed`，且 Dex 已同意喚醒；否則 executor 會回報 `[卡住] 角色休眠中`。
- 回報後由 CoS 更新 `{cxo}-latest.md`；`hooks/cxo-post-agent.sh` 只在 subagent_type 是 cxo-executor 時提醒。

---

## 模式 B：Multi-CXO Agent Team 派遣

### 啟動條件
- 任務涉及 ≥2 個 CXO 領域
- 或 Dex 明確要求多 CXO 協作

### 啟動流程

1. **分析** — CoS 解析任務，判斷需要哪些 CXO
2. **確認** — 向 Dex 列出任務拆解計畫：
   ```
   這個任務需要多 CXO 協作，我的計畫：
   - CPO：{子任務描述}
   - CMO：{子任務描述}
   要啟動 Agent Team 嗎？
   ```
3. **建立 Team** — Dex 確認後，用自然語言請求建立 Agent Team
4. **建立任務** — 用 TaskCreate 為每個 CXO 建立任務，設定依賴（blockedBy）
5. **Spawn Teammates** — 每個 CXO 作為一個 teammate，prompt 中帶入：
   - persona 路徑
   - knowledge 路徑
   - cxo-context 路徑
   - 具體任務描述
   - 工具分配（參考 tools-registry.md）
6. **監控** — Teammates 自行認領任務，CoS 監控進度
7. **匯整** — 所有 CXO 完成後，CoS 統整摘要交付 Dex

### 限制規則
- **並行上限 1 個 teammate**，其餘用 blockedBy 依序執行
- Teammates 之間可以 SendMessage 直接溝通（例如 CPO 問 CMO 這個功能怎麼對外講）
- 每個 teammate 完成後，CoS 仍須更新對應的 cxo-context

### Teammate 命名規則
teammate 名稱 = CXO 代號，只用 `state/cxo-roster.md` 標「活躍」的代號；休眠角色要先照「喚醒接線清單」喚醒

---

## 休眠角色與喚醒接線清單

角色狀態與喚醒條件只寫在 `state/cxo-roster.md`。意圖屬於休眠角色時，CoS 先問 Dex「要喚醒 {名稱} 嗎？」。Dex 同意後依序：

1. 重寫該角色的 `state/cxo-context/{cxo}-latest.md`（休眠角色的 latest 都過期 100 天以上）：舊內容照「Context 管理細節」移 archive，新版依固定欄位寫現況；同時在 roster 把狀態改「活躍」、清空休眠起始日與下次檢討日。
2. `~/CLAUDE.md` CXO 調度表加回該角色一列（觸發意圖、/{cxo}、`cxo-executor（CXO={cxo}）`）。
3. `~/.claude/skills/daydreamdex-{cxo}/SKILL.md` 拿掉 `disable-model-invocation: true`。
4. board SKILL.md 名單把該角色狀態改「活躍」。
5. 衝突解決規則（`~/CLAUDE.md` 調度規則最後一條）需要時補上該角色的範圍。
6. 跑 `python3 scripts/cxo-lint.py`，**0 錯誤才算接線完成**（警告可留）。lint 以 roster 為準檢查調度表、喚醒關鍵字、board 名單、playbook 命名、tools-registry、skill 的 disable-model-invocation／audit／symlink、situation-board `--check`。

休眠：上面反過來做，roster 填休眠起始日與下次檢討日（1 個月後）。

## 外部工具呼叫

CXO executor 沒有 Bash。需要其他系統的 CLI 或 workflow 時，由 CoS 在主 session 執行（executor 在「待辦」列出要跑什麼）。工具分配表放 `~/daydreamdex/knowledge/tools-registry.md`（本範例未收錄）。

## Context 管理細節

- **派遣前**：模式 A 的讀檔清單寫在 `agents/cxo-executor.md`，prompt 不用重複；模式 B 的 teammate prompt 要帶 persona、knowledge、`{cxo}-latest.md` 路徑
- **回報後**：CoS 立即更新 `~/daydreamdex/state/cxo-context/{cxo}-latest.md`，再跑 `python3 scripts/build-situation-board.py`（可先 `--dry-run`）重新產生 situation-board 的現況與決策段；承諾有變動時手改 situation-board 的承諾表。`--check` 回非 0 代表 situation-board 已過期
- **格式**：原地改寫，不新增區塊。全檔 ≤80 行，固定結構：
  ```
  # {CXO} 最近 Context
  ## 最近更新：{日期}（{這次改了什麼，一句}）
  ### 現況
  ### 仍有效的決策
  ### 待辦
  ### 下次注意
  ```
- **舊內容移 archive，不刪**：被取代的決策、已完成或作廢的待辦、過期的注意事項，連同原日期移到 `state/cxo-context/archive/{cxo}-YYYY-MM.md`（依該條原日期的月份；沒日期的放 `{cxo}-undated.md`），附一句移出原因。
- **可重用判準另存**：移到 archive 的條目，若是以後還會套用到其他任務的判斷規則（不是一次性的事實或進度），同時寫一份到 `knowledge/{cxo}/principles.md`，格式「判準一句｜原日期｜出處」。persona 會引用這份檔，executor 開工讀得到；archive 它不讀。
- **決策標日期**：新寫進「仍有效的決策」的條目，句尾標 `（YYYY-MM-DD）`。`scripts/build-situation-board.py` 只把近 30 天、句尾有完整日期的決策放進 situation-board。
- **不重抄**：決策或細節已有正式出處（grill 紀錄、HANDOFF、knowledge 檔）時，latest 只寫結論一句＋連結。
- **讀取**：board、executor 只讀 `{cxo}-latest.md`，不讀 archive，除非要查歷史。
- **Agent Team 模式額外**：CoS 在所有 teammates 完成後，額外產出一份跨 CXO 匯整摘要
- **長期萃取**：/cos-review 尚未建置
