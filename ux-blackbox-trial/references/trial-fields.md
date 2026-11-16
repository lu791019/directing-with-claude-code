# trial.json 欄位

範例在 `assets/trial.example.json`，雛形用 `assets/trial.prototype.example.json`。測試根目錄不存在就先建立。

| 欄位 | 必填 | 誰讀 | 用途 |
|---|---|---|---|
| `title` | 是 | scaffold | 功能名稱，出現在指引與狀態檔 |
| `root` | 是 | 兩支腳本 | 測試根目錄 |
| `start_url` | 是 | 兩支腳本 | 測試員的起始網址 |
| `tasks` | 是 | scaffold | 任務清單，寫法見 task-design |
| `testers` | 是 | 兩支腳本 | 黑箱測試員，見下表 |
| `target` | 否 | scaffold、prepare | `live` 或 `prototype`，預設 `live`。雛形會帶入內建說明，白箱排第一位 |
| `prototype_source` | 雛形必填 | prepare | 組裝後的單檔雛形路徑 |
| `background` | 否 | scaffold | 任務卡開頭的一句背景 |
| `mistakes` | 否 | scaffold | 故意犯錯，自動接在任務後面。雛形不能設 |
| `login_note` | 否 | scaffold | 給測試員的登入說明 |
| `browser` | 否 | scaffold | 預設 Claude in Chrome |
| `dont_click` | 否 | scaffold | 不能點的東西，要寫原因 |
| `native_dialog_actions` | 否 | scaffold | 會跳原生對話框的動作 |
| `not_issues` | 否 | scaffold | 不算畫面問題的事項 |
| `known_issues` | 否 | scaffold | 已知問題，只寫現象 |
| `authorized_writes` | 否 | scaffold | 使用者同意的寫入與下載 |
| `whitebox` | 否 | scaffold | 白箱設定，不設就不派 W1 |
| `allowed_urls` | 否 | audit | 允許輸入的網址開頭，預設只有 `start_url` |
| `login_url` | 否 | audit | 登入網址，加入允許清單 |

`testers` 每位：

| 欄位 | 必填 | 用途 |
|---|---|---|
| `id` | 是 | 編號，也是資料夾名 |
| `facet` | 否 | `ux` 或 `ui`，預設 `ux` |
| `model` | 否 | 寫等級即可（Opus、Sonnet），開 session 時選該等級最新版 |
| `effort` | 否 | 思考程度：low、medium |
| `sandbox` | 否 | 專屬測試資料。查詢型功能留空 |

`whitebox`：

| 欄位 | 必填 | 用途 |
|---|---|---|
| `repo_path` | 是 | 受測 repo，W1 的 session 開在這裡 |
| `revision` | 是 | 受測版本。查不到寫「未驗證」 |
| `files` | 是 | 要讀的檔案，相對於 `repo_path` |
| `standards` | 是 | 對照基準 |
| `id`、`model`、`effort` | 否 | 預設 W1 |
| `out_of_scope` | 否 | 範圍外的部分 |
