# REVIEW.md — <repo 名稱> 審查重點

> code owner 寫給 reviewer（人或 agent）看，放 repo 根目錄。只寫這個 repo 特有的事；
> 通用規則（分級、收斂、回報格式）在 `~/.claude/rules/common/code-review.md`，不要抄過來。
> 同一條 review 意見出現第二次，就把它寫進這裡或改成 lint／測試，不要等第三次。

## 這裡的「壞掉」長什麼樣
<!-- 寫失敗的樣子，不寫一般原則。例： -->
- <金額不是整數分；累計退款超過已付>
- <文件說的和程式做的不一樣（文件的失敗＝說謊）>
- <設定檔把流量導到錯的環境（設定的失敗＝路由錯）>

## 高風險路徑
命中任一條，風險等級就是高，計畫不得調低（`risk-paths --base <分支>` 讀這個區塊）。

```risk-paths
# 金流／帳務
<src/billing/**>
# 資料庫結構
<migrations/**>
# 部署與 CI
<.github/workflows/**>
```

## 跳過不審
- <vendor/**、產生檔、lockfile、快照>

## 這個 repo 的小意見上限
- 每輪最多 <3> 則；<這個 repo 不在意的風格類別，例如中文註解句尾標點>
