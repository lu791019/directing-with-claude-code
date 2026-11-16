# work-item-ops：工單收尾

案子做完時，留言說明做了什麼、指派回負責人、狀態改成待驗收，可連上層工單一起改。預設先預覽，加 `--apply` 才寫入；狀態名先確認存在。預設用 GitHub Issues（`gh` CLI），`Tracker` 介面可換成其他工單系統。

- `SKILL.md`：流程與留言範本
- `scripts/work_item.py`：`python3 scripts/work_item.py --help`
- `tests/test_work_item.py`：用假的工單系統，不呼叫 gh

概念來自團隊的工單流程，這裡是重新寫的通用版。
