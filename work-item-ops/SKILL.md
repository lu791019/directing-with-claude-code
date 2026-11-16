---
name: work-item-ops
description: 案子做完時回報工單：留言說明做了什麼、指派回負責人、狀態改成待驗收，可連上層工單一起改。寫入前一律先預覽、先確認狀態名存在。預設用 GitHub Issues（gh CLI），可換成其他工單系統。
---

# 工單收尾

一個案子做完，工單要回到負責人手上：他要知道做了什麼、去哪驗、輪到他了。

## 三件事

1. **留言**：做了什麼、怎麼驗收、還沒做的與原因、相關 PR 或 commit。
2. **指派回負責人**：通常是開單的人或 PM。
3. **改狀態**：改成「待驗收」或你們團隊的對等狀態。上層工單（需求、epic）要一起動的，用 `--parent` 帶上。

## 寫留言

```markdown
## 做了什麼
- <一句話一項>

## 怎麼驗收
- <站台網址或指令>：<預期看到什麼>

## 沒做的
- <項目>：<原因>（沒有就寫「無」）

## 相關
- PR #<n>、commit <sha>
```

先寫進檔案（例如 `done.md`），給使用者看過再送。

## 步驟

1. **先看狀態名**（只讀）：

   ```bash
   python3 scripts/work_item.py --repo owner/name statuses
   ```

   GitHub 上狀態用 label 表示，名稱是 `status:<狀態>`；前綴不同就用 `--status-prefix` 指定。

2. **預覽**（不寫入）：

   ```bash
   python3 scripts/work_item.py --repo owner/name finish --issue 42 --parent 40 \
     --comment-file done.md --assignee <負責人帳號> --status 待驗收
   ```

   狀態名不存在會直接報錯、不往下走。把預覽結果給使用者看。

3. **使用者同意後才寫入**：同一行加 `--apply`。

## 規矩

- **沒有使用者同意不加 `--apply`。** 工單是別人也在看的地方，寫錯很難收回。
- 狀態名要先查，不要用猜的；團隊的狀態名常常跟你以為的不一樣。
- 留言只寫一次，寫在主工單；上層工單只改狀態。
- 已經是目標狀態、已經指派過的，腳本會跳過，不重複寫。
- 不在留言裡貼金鑰、帳密、內部網址。

## 換成其他工單系統

`scripts/work_item.py` 裡的 `Tracker` 介面只有五個方法：`get`、`statuses`、`comment`、`assign`、`set_status`。照它寫一個類別（例如用 Jira、GitLab、Linear 的 CLI 或 API），在 `TRACKERS` 註冊，就能用 `--tracker <名稱>` 切換。預覽與狀態驗證的流程不用改。

## 測試

```bash
python3 -m unittest tests/test_work_item.py   # 用假的工單系統，不呼叫 gh
python3 scripts/work_item.py --help
```
