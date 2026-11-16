#!/usr/bin/env python3
"""從各 {cxo}-latest.md 產生 situation-board 的「現況」「各角色最近更新」「近 30 天決策」。

用法：
  python3 scripts/build-situation-board.py            寫回 state/situation-board.md
  python3 scripts/build-situation-board.py --dry-run  只印差異，不寫檔
  python3 scripts/build-situation-board.py --check    產生區與重新產生的結果不同時回傳 1，不寫檔
  --root <dir>  repo 根目錄（預設本腳本的上一層）；--today YYYY-MM-DD（預設今天，供「近 30 天」與測試用）

只改 BEGIN／END 標記之間；標記外（檔頭、承諾表、Board 會議紀錄）一字不動。
產生內容不含產生時間，同樣的 latest 一定產生同樣的結果，--check 才可靠。
"""
import argparse, datetime, difflib, pathlib, re, sys

BEGIN = '<!-- BEGIN generated: build-situation-board.py（勿手改；改 latest 後重跑） -->'
END = '<!-- END generated -->'
DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')
TAIL_DATE = re.compile(r'[（(](\d{4}-\d{2}-\d{2})[）)][。.]?\s*$')
WINDOW_DAYS = 30
MAX_STATUS = 3

def read_roster(root):
    rows = []
    for line in (root / 'state' / 'cxo-roster.md').read_text(encoding='utf-8').splitlines():
        cols = [c.strip() for c in line.split('|')]
        if len(cols) > 4 and re.fullmatch(r'[a-z]+', cols[1] or ''):
            rows.append({'code': cols[1], 'name': cols[2], 'status': cols[3]})
    if not rows:
        raise SystemExit('錯誤：roster 讀不到任何角色')
    return rows

def section(lines, title):
    """回傳 ### title 底下、到下一個 ### 或 ## 之前的行。"""
    out, on = [], False
    for l in lines:
        if l.startswith('### '):
            on = l[4:].strip().startswith(title); continue
        if l.startswith('## '):
            on = False; continue
        if on: out.append(l)
    return out

def top_bullets(lines):
    return [l.rstrip() for l in lines if l.startswith('- ')]

def parse_latest(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    head = next((l for l in lines if l.startswith('## 最近更新')), '')
    m = DATE.search(head)
    note = re.search(r'[（(](.*)[）)]\s*$', head)
    decisions = []
    for b in top_bullets(section(lines, '仍有效的決策')):
        t = TAIL_DATE.search(b)
        if t: decisions.append((t.group(1), b[2:]))
    return {'date': m.group(1) if m else None, 'note': note.group(1) if note else '',
            'status': top_bullets(section(lines, '現況'))[:MAX_STATUS], 'decisions': decisions}

def generate(root, today):
    roster = read_roster(root)
    active = [r for r in roster if r['status'] == '活躍']
    dormant = [r for r in roster if r['status'] == '休眠']
    data = {r['code']: parse_latest(root / 'state' / 'cxo-context' / f"{r['code']}-latest.md") for r in active}
    as_of = max((d['date'] for d in data.values() if d['date']), default='—')
    out = [BEGIN, f'## 現況（自動產生，資料截至 {as_of}）']
    for r in active:
        d = data[r['code']]
        out.append(f"- **{r['name']}**（{d['date'] or '無日期'}）")
        out += ['  ' + s for s in d['status']] or ['  - （latest 沒有「現況」條目）']
        out.append(f"  - 完整見 `state/cxo-context/{r['code']}-latest.md`")
    if dormant:
        out.append('- 休眠：' + '、'.join(r['name'] for r in dormant) + '（見 `state/cxo-roster.md`）')
    out += ['', '## 各角色最近更新']
    for r in sorted(active, key=lambda r: data[r['code']]['date'] or '', reverse=True):
        d = data[r['code']]
        out.append(f"- {d['date'] or '無日期'} {r['name']}：{d['note'] or '（無摘要）'}")
    since = (today - datetime.timedelta(days=WINDOW_DAYS)).isoformat()
    recent = sorted(((day, r['name'], text) for r in active for day, text in data[r['code']]['decisions']
                     if since <= day <= today.isoformat()), reverse=True)
    if recent:
        out += ['', f'## 近 {WINDOW_DAYS} 天決策（句尾有完整日期的「仍有效的決策」）']
        out += [f'- {day} {name}：{text}' for day, name, text in recent]
    out.append(END)
    return '\n'.join(out) + '\n'

def split_board(text):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit(f'錯誤：situation-board 的產生區標記必須各出現一次（BEGIN {text.count(BEGIN)}、END {text.count(END)}），不寫檔')
    a = text.index(BEGIN); b = text.index(END) + len(END)
    if b < a:
        raise SystemExit('錯誤：END 標記在 BEGIN 之前，不寫檔')
    if text[b:b+1] == '\n': b += 1
    return text[:a], text[a:b], text[b:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument('--today', default=datetime.date.today().isoformat())
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--check', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    board = root / 'state' / 'situation-board.md'
    text = board.read_text(encoding='utf-8')
    pre, old, post = split_board(text)
    new = generate(root, datetime.date.fromisoformat(a.today))
    if a.check:
        if old != new:
            print('situation-board 產生區已過期：請跑 python3 scripts/build-situation-board.py', file=sys.stderr)
            return 1
        return 0
    if a.dry_run:
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'situation-board（目前）', 'situation-board（重新產生）'))
        return 0
    if old != new:
        board.write_text(pre + new + post, encoding='utf-8')
        print('已更新 situation-board 產生區')
    else:
        print('產生區已是最新，未改檔')
    return 0

if __name__ == '__main__':
    sys.exit(main())
