#!/usr/bin/env python3
"""依 trial.json 產生各測試員資料夾與開 session 指引。

用法：python scaffold_trial.py <trial.json>

產出：
  <root>/<編號>/prompt.md、tasks.md
  <root>/_coordinator/launch.md、status.md
已存在的 prompt.md 不覆蓋，除非加 --force。只用標準函式庫。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
CHECKLIST = os.path.normpath(os.path.join(HERE, '..', 'references', 'ux-checklist.md'))
FACETS = {'ux': ('UX 挑剔', 'facet-ux.md'), 'ui': ('UI 視覺', 'facet-ui.md')}
REQUIRED = ('title', 'root', 'start_url', 'tasks', 'testers')
TARGETS = ('live', 'prototype')
PROTOTYPE_NOT_ISSUES = [
    '這是尚未開發的雛形，資料是示意值，重新整理後會回到初始狀態。',
    '雛形沒有接線的按鈕按下去不會有反應。遇到時在逐步紀錄寫「已找到，未接線」，該步當作已完成並繼續，'
    '不要重試，也不要記成「沒有回饋」。但結果畫面若完全沒有畫出來，要記下是哪個結果沒畫。',
    '標著「畫面切換」「狀態切換」「結果狀態」的列是雛形的控制列，不是系統畫面。'
    '可以用它換畫面或看不同狀態，它本身不算畫面問題。系統左側選單在雛形裡沒有畫，也不算問題。',
    '黃框是還沒確認的需求，看到照常操作，不用另外回報。',
    '彈窗內容可能固定只畫一筆示範資料，內容和你點的那一列不同時，記下來即可，由協調窗判斷。',
]
PROTOTYPE_WHITEBOX = (
    '## 受測物是雛形\n\n'
    '- 逐條查 Scenario 的 Then 在畫面上有沒有對應內容。只寫在 `proto-impl-note` 的算沒畫，那段只在實作模式顯示。\n'
    '- 另外列出文件之間互相矛盾的地方，以及文件沒定義、畫面卻碰得到的情況。\n'
    '- 走查表中只能靠實際行為判定的條目，寫「N/A－雛形不含」，不要判缺陷。\n'
    '- 只讀 body 片段，不讀組裝後的單檔雛形與組裝殼，檔案太大。\n'
)


def read(path):
    with io.open(path, encoding='utf-8') as fh:
        return fh.read()


def write(path, text, force):
    if os.path.exists(path) and not force:
        print('略過（已存在）：' + path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print('寫入：' + path)


def bullets(items, empty='（無）'):
    return '\n'.join('- ' + i for i in items) if items else empty


def fill(template, values):
    for key, value in values.items():
        template = template.replace('{{' + key + '}}', value)
    return template


def dont_click_block(items):
    return '\n'.join('- 🔴 不要點：' + i for i in items) + '\n' if items else ''


def native_block(items):
    if not items:
        return ''
    return (
        '\n## 瀏覽器原生對話框（工具限制，不是畫面問題）\n\n'
        'Chrome 工具操作不了瀏覽器自己跳出的小視窗。它一跳出來，分頁會卡住，工具回報逾時。'
        '下列動作在畫面上找到按鈕後，要這樣處理：\n\n'
        '1. 截圖，在逐步紀錄寫一行「打算按：按鈕文字｜位置」。\n'
        '2. 🔴 不要按下去。這一步記「已找到，未按（工具限制）」，當作已完成，繼續往下走。協調窗會代測。\n\n'
        + bullets(items) + '\n\n'
        '其他情況按下按鈕後工具回報逾時，同樣是跳了原生對話框，對話框不會自己消失。不要重試，也不要等：'
        '關掉卡住的分頁，開新分頁回起始網址，結果當作「取消」，記進工具問題紀錄，然後繼續。\n'
    )


def authorized_block(text):
    if not text:
        return ''
    return (
        '## 寫入授權\n\n' + text + '\n\n'
        '此外的規則都不放寬。如果仍被權限機制擋下：不要重試、不要拆開重送、不要換方法，'
        '記進工具問題紀錄，該步驟記「未做（權限）」，其餘步驟照做。\n\n'
    )


def tasks_text(trial):
    lines = ['# 任務卡', '']
    if trial.get('background'):
        lines += ['背景：' + trial['background'] + ' 任務照順序做，每個任務只看情境，自己從畫面上找方法。', '']
    for n, task in enumerate(trial['tasks'], 1):
        lines += ['## 任務 %d' % n, task, '']
    mistakes = trial.get('mistakes') or []
    if mistakes:
        n = len(trial['tasks']) + 1
        lines += [
            '## 任務 %d：故意犯錯' % n,
            '前面的任務都做完、結果都寫進回饋檔之後才做。每項都要有結果，做不到也要寫原因。只用你自己的測試資料。',
            '',
        ]
        lines += ['%d. %s' % (i, m) for i, m in enumerate(mistakes, 1)]
        lines.append('')
    return '\n'.join(lines)


def is_prototype(trial):
    return trial.get('target', 'live') == 'prototype'


def mistakes_item(trial):
    if trial.get('mistakes'):
        return '4. 故意犯錯表：每項一列，寫做了什麼、結果；做不到也要寫原因。'
    return '4. 故意犯錯：本輪沒有列，寫「本輪未列」，不要自己發明。'


def tester_prompt(trial, tester):
    facet = tester.get('facet', 'ux')
    if facet not in FACETS:
        sys.exit('未知的 facet：%s（只支援 ux、ui）' % facet)
    label, facet_file = FACETS[facet]
    login = trial.get('login_note')
    not_issues = (PROTOTYPE_NOT_ISSUES if is_prototype(trial) else []) + (trial.get('not_issues') or [])
    return fill(read(os.path.join(ASSETS, 'tester-common.md')), {
        'id': tester['id'],
        'facet_label': label,
        'model': tester.get('model', ''),
        'effort': tester.get('effort', ''),
        'sandbox': tester.get('sandbox') or '本功能沒有專屬測試資料。',
        'start_url': trial['start_url'],
        'login_note': '- 登入：' + login if login else '',
        'browser': trial.get('browser', 'Claude in Chrome'),
        'authorized_writes': authorized_block(trial.get('authorized_writes', '')),
        'dont_click': dont_click_block(trial.get('dont_click') or []),
        'native_dialogs': native_block(trial.get('native_dialog_actions') or []),
        'not_issues': bullets(not_issues, ''),
        'known_issues': bullets(trial.get('known_issues') or []),
        'facet_block': read(os.path.join(ASSETS, facet_file)).rstrip(),
        'mistakes_item': mistakes_item(trial),
    })


def whitebox_prompt(trial, box, folder):
    tester_id = box.get('id', 'W1')
    return fill(read(os.path.join(ASSETS, 'tester-whitebox.md')), {
        'id': tester_id,
        'output_path': os.path.join(folder, tester_id + '-白箱UI規範對照.md'),
        'revision': box.get('revision', ''),
        'repo_path': box.get('repo_path', ''),
        'files': bullets(box.get('files') or []),
        'standards': bullets(box.get('standards') or []),
        'checklist_path': CHECKLIST,
        'known_issues': bullets(trial.get('known_issues') or []),
        'out_of_scope': box.get('out_of_scope', ''),
        'target_block': PROTOTYPE_WHITEBOX if is_prototype(trial) else '',
    })


def card(n, total, tester_id, label, folder, model, effort, sentence):
    return (
        '## 第 %d／%d 張：%s（%s）\n\n'
        '1. 開一個新 session。\n'
        '2. 資料夾選：`%s`\n'
        '3. 模型選 **%s**，思考程度選 **%s**。\n'
        '4. 貼上下面這句，送出：\n\n'
        '```text\n%s\n```\n\n'
        '開好回一聲「好了」。\n\n' % (n, total, tester_id, label, folder, model, effort, sentence)
    )


def launch_text(trial, rows):
    lines = ['# 開 session 指引：%s\n' % trial['title']]
    lines.append('每位測試員各開一個 session。協調窗可以代開時，不需要照這份做。\n')
    lines.append('用終端機開的話，黑箱測試員要用 `claude --chrome` 啟動，否則碰不到瀏覽器。\n')
    if is_prototype(trial):
        lines.append('開始前確認：本機站已起、雛形複本是最新的。\n')
        lines.append('照順序跑：先開白箱，修完雛形重跑 `prepare_prototype.py`，再開黑箱。\n')
    else:
        lines.append('開始前確認：站台版本正確、Chrome 已登入正確帳號、測試資料已建好。\n')
    lines.append('| 編號 | 面向 | 模型 | 思考程度 | 資料夾 |\n|---|---|---|---|---|')
    for r in rows:
        lines.append('| %s | %s | %s | %s | `%s` |' % (r['id'], r['label'], r['model'], r['effort'], r['folder']))
    lines.append('')
    for i, r in enumerate(rows, 1):
        lines.append(card(i, len(rows), r['id'], r['label'], r['folder'], r['model'], r['effort'], r['sentence']))
    return '\n'.join(lines)


def status_text(trial, rows):
    lines = [
        '# 試跑狀態：%s' % trial['title'],
        '',
        '- 開工時間：',
        '- 測試版本：',
        '- 登入帳號：',
        '',
        '| 編號 | 狀態 | 開始 | 結束 | 回饋檔 | 備註 |',
        '|---|---|---|---|---|---|',
    ]
    lines += ['| %s | 未開始 | | | | |' % r['id'] for r in rows]
    lines += ['', '## 人工介入', '', '## 與計畫的偏差', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial_json')
    parser.add_argument('--force', action='store_true', help='覆蓋已存在的檔案')
    args = parser.parse_args()

    trial = json.loads(read(args.trial_json))
    missing = [k for k in REQUIRED if not trial.get(k)]
    if missing:
        sys.exit('trial.json 缺少欄位：' + '、'.join(missing))
    ids = [t['id'] for t in trial['testers']]
    if len(ids) != len(set(ids)):
        sys.exit('測試員編號重複')
    if trial.get('target', 'live') not in TARGETS:
        sys.exit('未知的 target：%s（只支援 %s）' % (trial['target'], '、'.join(TARGETS)))
    if is_prototype(trial):
        if not trial.get('prototype_source'):
            sys.exit('target 是 prototype 時要有 prototype_source')
        if trial.get('mistakes'):
            sys.exit('雛形沒有防呆邏輯，不做故意犯錯，請移除 mistakes')

    root = os.path.normpath(trial['root'])
    rows = []
    sentence = '請讀本資料夾的 prompt.md，照裡面做。'
    for tester in trial['testers']:
        folder = os.path.normpath(os.path.join(root, tester['id']))
        write(os.path.join(folder, 'prompt.md'), tester_prompt(trial, tester), args.force)
        write(os.path.join(folder, 'tasks.md'), tasks_text(trial), args.force)
        rows.append({'id': tester['id'], 'label': FACETS[tester.get('facet', 'ux')][0], 'folder': folder,
                     'model': tester.get('model', ''), 'effort': tester.get('effort', ''), 'sentence': sentence})

    box = trial.get('whitebox')
    if box:
        tester_id = box.get('id', 'W1')
        folder = os.path.normpath(os.path.join(root, tester_id))
        prompt_path = os.path.join(folder, 'prompt.md')
        write(prompt_path, whitebox_prompt(trial, box, folder), args.force)
        row = {'id': tester_id, 'label': '白箱規範', 'folder': os.path.normpath(box.get('repo_path', '.')),
               'model': box.get('model', ''), 'effort': box.get('effort', ''),
               'sentence': '請讀 %s，照裡面做。' % prompt_path}
        rows.insert(0 if is_prototype(trial) else len(rows), row)

    coord = os.path.join(root, '_coordinator')
    write(os.path.join(coord, 'launch.md'), launch_text(trial, rows), args.force)
    write(os.path.join(coord, 'status.md'), status_text(trial, rows), args.force)
    print('完成：%d 位測試員' % len(rows))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    main()
