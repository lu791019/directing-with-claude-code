# keepwarm：快取保溫

派背景子代理、或要離開 1～8 小時時，每 30 分鐘喚醒主線一次，讓 prompt cache 不過期，回來時不用整段重新計費。規則在 `SKILL.md`；放進 `~/.claude/skills/keepwarm/` 即可用 `/keepwarm` 開。

內容由 Dex 參考公司團隊的做法調整、重寫而成，用來說明自己的工作流程，不在本 repo 的 AGPL-3.0 授權範圍內，見 `LICENSE-NOTICE.md`。
