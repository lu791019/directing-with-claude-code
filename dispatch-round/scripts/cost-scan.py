#!/usr/bin/env python3
"""掃描 ~/.claude/projects 的所有 session 記錄，換算 API 等值成本。

用途：重新量測 SKILL.md「定調」段的成本模型，或在調整流程後驗證是否真的降下來。
輸出：按月、按模型、成本結構、主線vs子代理、子代理 session 長尾。

    python cost-scan.py              # 全部歷史
    python cost-scan.py --days 30    # 只看近 30 天
    python cost-scan.py --until 2026-09-08          # 改動前的乾淨基準
    python cost-scan.py --since 2026-09-10          # 改動後（切點自己填）
    python cost-scan.py --root <路徑>
    python cost-scan.py --root ~/.claude/projects/<專案> --list-agents   # 逐一對 Agent 回報的 totalToolUseCount

同一則 API 回應在 jsonl 裡是多行，scan() 會合併（見其 docstring）；子代理按 agentId 分組。

注意：算的是「如果走 API 要付多少」，不是訂閱實付金額；用途是比較不同做法的相對成本。
"""
import json, os, sys, argparse, collections, datetime

# ── 每 MTok 美元 (input, output)。換代後必須更新，否則結論會錯。最後校對 2026-09-30 ──
PRICE = {
    "opus55":   (4.0, 20.0),    # Opus 5.5
    "opus":     (5.0, 25.0),    # Opus 5 / 4.x
    "sonnet5":  (2.0, 10.0),    # Sonnet 5 / 5.5
    "sonnet46": (3.0, 15.0),
    "haiku":    (1.0, 5.0),
    "fable":    (10.0, 50.0),   # Fable / Mythos
}
# 快取讀取預設 = input × 0.1；下列前綴享優惠費率（每 MTok 美元）
CACHE_READ_OVERRIDE = {"claude-fable-5-1": 0.25, "claude-mythos-5-1": 0.25, "claude-opus-5-5": 0.20}
# 快取寫入倍率：5 分鐘 TTL ×1.25，1 小時 TTL ×2.0
W5X, W1X = 1.25, 2.0
# 視為「開始寫東西」的工具——用來量子代理在探索期花了多少次呼叫
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

def tier(m):
    if not m or m == "<synthetic>": return None   # <synthetic> 是本機合成訊息，無計費
    if m.startswith("claude-opus-5-5"): return "opus55"
    if m.startswith("claude-opus"): return "opus"
    if m.startswith("claude-sonnet-5"): return "sonnet5"
    if m.startswith("claude-sonnet"): return "sonnet46"
    if m.startswith(("claude-haiku", "claude-3-5-haiku")): return "haiku"
    if m.startswith(("claude-fable", "claude-mythos")): return "fable"
    return None

def cache_read_rate(model, pin):
    for pfx, rate in CACHE_READ_OVERRIDE.items():
        if model.startswith(pfx): return rate
    return pin * 0.1

def scan(root, since=None, until=None):
    """每則 API 回應（message.id）合併成一列。

    session jsonl 對同一則回應會寫多行，每行只帶一個 content 區塊（thinking／text／tool_use 各一行）：
    - usage.output_tokens 在子代理記錄的前幾行是串流中途值，最後一行才是最終值 ⇒ 取各行最大值
    - tool_use 通常不在第一行 ⇒ 跨行累加，並以區塊 id 去重（resume／worktree 會把同一則寫進兩個檔）
    - input／cache 欄位各行相同，取第一行即可
    子代理記錄的 sessionId 是父視窗的，子代理身分在 agentId；舊記錄沒有 agentId 時退回 sessionId。
    """
    msgs = {}
    unknown = collections.Counter()
    for dirpath, _, fnames in os.walk(root):
        for fn in fnames:
            if not fn.endswith(".jsonl"): continue
            try:
                fh = open(os.path.join(dirpath, fn), "r", encoding="utf-8", errors="replace")
            except OSError:
                continue
            with fh:
                for line in fh:
                    if '"usage"' not in line: continue
                    try: rec = json.loads(line)
                    except Exception: continue
                    if rec.get("type") != "assistant": continue
                    msg = rec.get("message") or {}
                    u = msg.get("usage") or {}
                    if not u: continue
                    mid = msg.get("id") or f"{fn}:{rec.get('uuid')}"
                    model = msg.get("model") or ""
                    blocks = [b for b in (msg.get("content") or [])
                              if isinstance(b, dict) and b.get("type") == "tool_use"]
                    out = u.get("output_tokens", 0) or 0
                    r = msgs.get(mid)
                    if r is None:
                        side = bool(rec.get("isSidechain"))
                        r = msgs[mid] = {
                            "ts": rec.get("timestamp") or "", "model": model, "u": u, "out": out,
                            "side": "子代理" if side else "主線",
                            "sid": rec.get("sessionId"),
                            "aid": (rec.get("agentId") or rec.get("sessionId")) if side else None,
                            "tool_ids": set(), "names": [],
                        }
                    else:
                        r["out"] = max(r["out"], out)
                    for b in blocks:
                        bid = b.get("id") or f"{mid}#{len(r['names'])}"
                        if bid in r["tool_ids"]: continue
                        r["tool_ids"].add(bid); r["names"].append(b.get("name"))

    rows = []
    for r in msgs.values():
        ts, model, u, out = r["ts"], r["model"], r["u"], r["out"]
        if since and ts[:10] < since: continue
        if until and ts[:10] > until: continue
        t = tier(model)
        if not t:
            if model != "<synthetic>": unknown[model] += 1
            continue
        cc = u.get("cache_creation") or {}
        w5 = cc.get("ephemeral_5m_input_tokens", 0) or 0
        w1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
        tw = u.get("cache_creation_input_tokens", 0) or 0
        if w5 + w1 == 0 and tw: w5 = tw       # 舊格式無細分，當 5m
        inp = u.get("input_tokens", 0) or 0
        rd  = u.get("cache_read_input_tokens", 0) or 0
        pin, pout = PRICE[t]
        parts = {
            "未快取輸入": inp * pin / 1e6,
            "快取寫入(5m)": w5 * pin * W5X / 1e6,
            "快取寫入(1h)": w1 * pin * W1X / 1e6,
            "快取讀取": rd * cache_read_rate(model, pin) / 1e6,
            "輸出": out * pout / 1e6,
        }
        rows.append({
            "ts": ts, "model": model, "cost": sum(parts.values()), "parts": parts,
            "side": r["side"], "sid": r["sid"], "aid": r["aid"], "rd": rd, "out": out,
            "names": r["names"], "tools": len(r["names"]),
        })
    return rows, unknown

def main():
    # 主控台編碼不是 UTF-8 時，印 ⚠ 或全形字會丟 UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        try: stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser(r"~\.claude\projects"))
    ap.add_argument("--days", type=int, help="只統計最近 N 天")
    ap.add_argument("--since", help="只統計此日期(YYYY-MM-DD)含以後——改流程的切點用這個，比 --days 精確")
    ap.add_argument("--until", help="只統計此日期(YYYY-MM-DD)含以前——取改動前的乾淨基準用")
    ap.add_argument("--list-agents", action="store_true",
                    help="逐一列出每個子代理的工具呼叫次數（搭配 --root 指到單一專案做驗證）")
    a = ap.parse_args()
    if a.days and a.since:
        sys.exit("--days 與 --since 擇一")
    since = a.since
    if a.days:
        since = (datetime.date.today() - datetime.timedelta(days=a.days - 1)).isoformat()
    list_agents = a.list_agents
    rows, unknown = scan(a.root, since, a.until)
    if not rows:
        print("沒有掃到任何計費訊息。"); return
    T = sum(r["cost"] for r in rows)
    span = (f"近 {a.days} 天" if a.days
            else f"{since or '起始'} ～ {a.until or '今天'}" if (since or a.until)
            else "全期")
    print(f"{span}：{len(rows):,} 則計費訊息，API 等值 ${T:,.0f}")
    if unknown:
        print(f"⚠ 未計價的未知模型（定價表要補）：{dict(unknown)}")
    print()

    def group(keyfn, title, extra=False):
        g = collections.defaultdict(lambda: collections.defaultdict(float))
        for r in rows:
            b = g[keyfn(r)]
            b["cost"] += r["cost"]; b["msgs"] += 1
            b["tools"] += r["tools"]; b["rd"] += r["rd"]; b["out"] += r["out"]
        print(f"=== {title} ===")
        for k in sorted(g, key=lambda x: -g[x]["cost"]):
            b = g[k]
            line = f"  {str(k):<26}{int(b['msgs']):>8,} 則  ${b['cost']:>9,.0f}  {b['cost']/T*100:>5.1f}%"
            if extra:
                line += f"   讀/寫比 {b['rd']/max(b['out'],1):>5.0f}:1   工具 {int(b['tools']):>7,}"
            print(line)
        print()
        return g

    days = sorted({r["ts"][:10] for r in rows if r["ts"]})
    mg = collections.defaultdict(float); md = collections.defaultdict(set)
    for r in rows:
        m = r["ts"][:7]; mg[m] += r["cost"]; md[m].add(r["ts"][:10])
    print("=== 按月 ===")
    for m in sorted(mg):
        d = len(md[m])
        print(f"  {m}   活躍 {d:>2} 天   ${mg[m]:>8,.0f}   每活躍日 ${mg[m]/max(d,1):>6,.0f}")
    print()
    group(lambda r: r["model"], "按模型")
    group(lambda r: r["side"], "主線 vs 子代理", extra=True)

    comp = collections.defaultdict(float)
    for r in rows:
        for k, v in r["parts"].items(): comp[k] += v
    print("=== 成本結構 ===")
    for k, v in sorted(comp.items(), key=lambda x: -x[1]):
        print(f"  {k:<14} ${v:>9,.0f}   {v/T*100:>5.1f}%")
    ctx = sum(v for k, v in comp.items() if k != "輸出")
    print(f"  → context 進出佔 {ctx/T*100:.1f}%，輸出僅 {comp['輸出']/T*100:.1f}%")
    print()

    # 子代理按 agentId 分組——sessionId 是父視窗的，按它分會把整個視窗的子代理併成一個
    sess = collections.defaultdict(float)
    stat = collections.defaultdict(lambda: collections.defaultdict(float))
    first_write = {}                      # aid -> 第幾次工具呼叫才第一次寫檔
    span_ts = {}                          # aid -> 首則時間，給 --list-agents 排序
    for r in sorted((r for r in rows if r["side"] == "子代理"), key=lambda r: r["ts"]):
        aid = r["aid"]
        sess[aid] += r["cost"]
        span_ts.setdefault(aid, r["ts"])
        s = stat[aid]
        if aid not in first_write:
            for i, name in enumerate(r["names"]):
                if name in WRITE_TOOLS:
                    first_write[aid] = int(s["tools"]) + i + 1; break
        s["tools"] += r["tools"]; s["rd"] += r["rd"]; s["out"] += r["out"]
    if sess:
        vals = sorted(sess.values(), reverse=True)
        tot = sum(vals)
        med = sorted(vals)[len(vals)//2]
        print(f"=== 子代理長尾（按 agentId，{len(vals):,} 個，${tot:,.0f}）===")
        print(f"  中位數 ${med:.2f}   平均 ${tot/len(vals):.2f}   最貴 ${vals[0]:,.0f}（中位數的 {vals[0]/max(med,1e-9):.0f} 倍）")
        for n in (10, 25, 50):
            if n < len(vals):
                print(f"  最貴 {n:>3} 個佔 {sum(vals[:n])/tot*100:>4.1f}%")
        q = len(vals) // 4
        if q:
            print(f"  最貴 25%（{q} 個）佔 {sum(vals[:q])/tot*100:>4.1f}%")

        def pct(xs, p): return xs[min(len(xs) - 1, int(len(xs) * p))]
        tl = sorted(int(stat[x]["tools"]) for x in sess)
        print(); print(f"  工具呼叫次數：p50={pct(tl,.5)}  p75={pct(tl,.75)}  p90={pct(tl,.9)}  最多={tl[-1]}"
              f"   （>100 次：{sum(t > 100 for t in tl)} 個）")
        print("  成本按工具次數分桶（熔斷閾值看這裡校準）：")
        big_n = big_c = 0
        for lo, hi in ((0, 40), (41, 100), (101, 200), (201, 10**9)):
            ss = [x for x in sess if lo <= stat[x]["tools"] <= hi]
            c = sum(sess[x] for x in ss)
            if lo > 100: big_n += len(ss); big_c += c
            print(f"    {lo:>3}~{'∞' if hi > 10**8 else hi:<4}: {len(ss):>5} 個 {len(ss)/len(vals)*100:>5.1f}%"
                  f"  ${c:>7,.0f}  成本 {c/tot*100:>5.1f}%")
        print(f"    >100 合計：{big_n/len(vals)*100:.1f}% 的子代理吃 {big_c/tot*100:.1f}% 的成本")
        fw = sorted(first_write.values())
        if fw:
            n40 = sum(v > 40 for v in fw)
            print(f"  首次寫檔前的呼叫數（{len(fw)} 個有寫檔）：p50={pct(fw,.5)}  p90={pct(fw,.9)}  最多={fw[-1]}"
                  f"   （>40 次：{n40} 個，{n40/len(fw)*100:.1f}%）——探索期門檻會在這些代理寫第一個檔前砍掉它")

        print(); print("  最貴 5 個：")
        for aid in sorted(sess, key=lambda x: -sess[x])[:5]:
            s = stat[aid]
            print(f"    ${sess[aid]:>7,.0f}  工具 {int(s['tools']):>5,} 次  讀/寫比 {s['rd']/max(s['out'],1):>5.0f}:1"
                  f"  首次寫檔@{first_write.get(aid, '—')}  {span_ts[aid][:10]}  {aid}")

        if list_agents:
            print(); print("  各子代理工具呼叫次數（依首則時間；可對 Agent 回報的 totalToolUseCount）：")
            for aid in sorted(sess, key=lambda x: span_ts[x]):
                print(f"    {span_ts[aid][:19]}  {aid}  {int(stat[aid]['tools']):>5}")

if __name__ == "__main__":
    main()
