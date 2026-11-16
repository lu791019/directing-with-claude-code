# 爬分輪：給代理一個數字，讓它往上爬，但畫面不准變

> 做法來自 Felix Rieseberg〈Made by mechanical means〉（2026-09）：給 thread 明確指標（幀率、draw call），
> 每輪優化後多角度截圖算像素差，確定是真的變快、不是畫質偷偷變差。這裡改寫成我們的派工流程。

## 什麼案子適用

有**一個能用指令量出來的數字**，而且有**一道能自動判「畫面／行為沒變」的守門**。兩者缺一就不是爬分，是普通實作輪。

| 指標 | 量法 | 守門 |
|---|---|---|
| Lighthouse Performance／LCP／TBT | `npm run test:lighthouse -- --base <本機 preview>`（3 次取中位數） | `npm run test:visual` + `test:e2e` + `test:unit` |
| bundle 大小、傳輸量 | build 後 `du`／Lighthouse `total-byte-weight` | 同上 |
| 測試套件時間、API p95 | 固定指令跑 3 次取中位數 | 既有測試全綠 |

## 三件必備（派工前主線先備好）

1. **指標量法固定**：指令、環境（本機 preview 或正式站）、次數、取中位數，全部寫進派工單。
   量之前看負載：`uptime` 的 1 分鐘值超過核心數就不作數（Lighthouse 腳本會自己標 `load_warning`）。
2. **守門先綠**：爬分前先跑一次守門，紅的先修或先記錄；基準圖（`*-snapshots/`）在爬分前就拍好並入庫。
3. **逐輪紀錄表**：一個 markdown 檔，每輪一列，代理填、主線核。

```markdown
| 輪 | 改了什麼（一件事） | 指標前 → 後 | 守門 | 採用？ | commit |
|---|---|---|---|---|---|
| 1 | hero 圖改 webp + width/height | Perf 71 → 78；LCP 3.9s → 2.6s | visual 12/12、e2e 全綠 | ✅ | abc1234 |
| 2 | 字型 preload | 78 → 78 | 綠 | ❌ 沒進步，revert | — |
```

## 派工單（接第二節模板，只列爬分輪特有的段落）

```
TESTS=locked
## 目標指標
Lighthouse Performance（手機模式），`npm run test:lighthouse -- --base http://localhost:<port>`，3 次取中位數。
現況 <N>，目標 ≥ 90。只看這一個數；LCP／TBT 當線索，不當目標。
## 守門（每輪改完必跑，紅就 revert 這輪）
npm run test:visual　→ 必須 12/12，不准改 11-visual.spec.ts、不准跑 test:visual:update、不准動 *-snapshots/
npm run test:e2e && npm run test:unit　→ 全綠
## 紀律
- 每輪只改一件事，量一次，守門一次，填一列紀錄表，一輪一個 commit（訊息寫「perf(round N): …」）。
- 沒進步（<1 分或 <2%）就 revert，不留著。
- 想做會改畫面的事（延遲載入首屏圖、拿掉動畫、縮圖降畫質）→ 不做，寫進「待裁示」。畫面要不要變是 Dex 決定，不是代理。
## 停止條件
達標；或連 3 輪沒進步；或守門紅且本輪 revert 後仍紅（代表不是你弄壞的，立刻回報）。
## 回報
紀錄表全文 + 最終指標 + 待裁示清單（每項給建議）。
```

## 主線複驗（不採信代理數字，照第四節的精神）

- 自己重量一次指標（同指令、同環境）；代理回報的數字和自己量的差超過 3 分或 5%，以自己的為準並追問。
- `npm run test:visual` 自己跑；`git diff --stat -- 'tests/e2e/*-snapshots/' tests/e2e/11-visual.spec.ts playwright.config.ts` **必須是空的**——基準圖或門檻被動過＝這輪作廢。
- 看結果檔有沒有 `load_warning: true`；有就重量。
- 紀錄表每一列對得上一個 commit，`git log --oneline` 數量一致。

## 反模式（實際會發生）

- 代理為了過守門去更新基準圖或放寬 `maxDiffPixels`——這是作弊，hook 擋不到 Bash 寫入，靠複驗的 `git diff` 抓。
- 砍功能換分數（拿掉 GA、移除字型、首屏圖改 lazy）——分數會漂亮，但那是產品決策。
- 一輪改三件事，分數動了不知道是哪件的功勞，下一輪沒法 revert 單項。
- 在負載 >核心數的機器上量，前後差 10 分以內全是雜訊。

## 部落格現況（2026-10-27）

守門已備：`test:visual`（6 頁 × 桌機／手機，`maxDiffPixels: 500`，影片遮罩）、`test:e2e`（387）、`test:unit`（59）。
指標腳本：`tests/lighthouse/audit.js`，支援 `--base`、`--runs`，缺依賴／負載高都會明講。
基線數字見 `notes/lighthouse-results.md`。實際去衝分是另一個案子，另開計畫。
