#!/usr/bin/env python3
"""解析測試員的 Claude Code 逐字紀錄，核對規則遵守，不採信自報。

用法：python audit_transcripts.py <trial.json> [--projects <~/.claude/projects>]

產出 <root>/_coordinator/audit.md。只抓機械性訊號，結果要人工判讀。
找不到紀錄會明講，不會當成 0 次違規。只用標準函式庫。
"""
import argparse
import glob
import io
import json
import os
import re
import sys
from datetime import datetime

FORBIDDEN = {'read_page', 'javascript_tool', 'read_network_requests', 'read_console_messages'}
DENIED = re.compile(r'denied|not allowed|Auto-Mode|Modify Shared|Credential|classifier|rejected', re.I)
FILE_TOOLS = {'Read', 'Glob', 'Grep', 'NotebookRead'}
SHELL_TOOLS = {'Bash', 'PowerShell'}


def encode_project(path):
    """Claude Code 以路徑命名專案資料夾：英數以外都換成連字號。"""
    return re.sub(r'[^A-Za-z0-9]', '-', os.path.normpath(path))


def local_time(stamp):
    if not stamp:
        return '?'
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone().strftime('%H:%M:%S')


def tool_uses(content):
    for block in content:
        if block.get('type') != 'tool_use':
            continue
        name = block['name'].split('__')[-1]
        data = block.get('input') or {}
        if name == 'browser_batch':
            for action in data.get('actions') or []:
                yield action.get('name', ''), action.get('input') or {}
        else:
            yield name, data


def result_text(block):
    content = block.get('content')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ' '.join(c.get('text', '') for c in content if isinstance(c, dict))
    return ''


def audit_file(path, ctx, out):
    for raw in io.open(path, encoding='utf-8', errors='replace'):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        msg = entry.get('message') or {}
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        stamp = entry.get('timestamp')
        if stamp:
            out['first'] = out['first'] or stamp
            out['last'] = stamp
        when = local_time(stamp)
        if entry.get('type') == 'assistant':
            if msg.get('model') and msg['model'] not in out['models']:
                out['models'].append(msg['model'])
            for name, data in tool_uses(content):
                out['tools'] += 1
                if name in FORBIDDEN:
                    out['forbidden'].append('%s %s' % (when, name))
                elif name == 'navigate':
                    url = str(data.get('url', ''))
                    if not any(url.startswith(u) for u in ctx['allowed_urls']) and url not in ('back', 'forward'):
                        out['urls'].append('%s %s' % (when, url[:120]))
                elif name in FILE_TOOLS:
                    target = str(data.get('file_path') or data.get('path') or data.get('pattern') or '')
                    full = os.path.normpath(target) if target else ''
                    # 桌面版 app 開場會自己查 side-session-notes，不是測試員的行為
                    if 'side-session-notes' in target:
                        continue
                    if ctx['folder'] and not full.lower().startswith(ctx['folder'].lower()):
                        out['reads'].append('%s %s %s' % (when, name, target[:120]))
                elif name in SHELL_TOOLS:
                    out['shell'].append('%s %s' % (when, str(data.get('command', ''))[:120]))
                elif name == 'find':
                    out['finds'].append('%s %s' % (when, str(data.get('query', ''))[:80]))
                elif name == 'form_input':
                    out['form_inputs'].append('%s %s' % (when, str(data.get('ref', ''))[:40]))
        else:
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_result' and block.get('is_error'):
                    text = result_text(block)
                    if DENIED.search(text):
                        out['denied'].append('%s %s' % (when, text[:140].replace('\n', ' ')))


def audit_tester(tester_id, folder, projects, allowed_urls):
    project = os.path.join(projects, encode_project(folder))
    files = sorted(glob.glob(os.path.join(project, '*.jsonl')))
    out = {'id': tester_id, 'found': len(files), 'project': project, 'first': None, 'last': None, 'models': [],
           'tools': 0, 'forbidden': [], 'urls': [], 'reads': [], 'shell': [], 'finds': [], 'form_inputs': [],
           'denied': []}
    ctx = {'folder': os.path.normpath(folder), 'allowed_urls': allowed_urls}
    for path in files:
        audit_file(path, ctx, out)
    return out


def section(title, items):
    lines = ['- %s：%d' % (title, len(items))]
    lines += ['  - ' + i for i in items[:30]]
    if len(items) > 30:
        lines.append('  - …另有 %d 筆' % (len(items) - 30))
    return lines


def render(results):
    lines = ['# 規則遵守稽核', '', '機械性訊號，要人工判讀。find 要看是否定位畫面上看得到的元素，form_input 只准用在原生下拉。', '']
    lines += ['| 測試員 | 紀錄檔 | 開始 | 結束 | 工具次數 | 禁用工具 | 網址 | 檔案 | 指令 | 權限拒絕 |',
              '|---|---|---|---|---|---|---|---|---|---|']
    for r in results:
        if not r['found']:
            lines.append('| %s | 找不到 | | | | 未核 | 未核 | 未核 | 未核 | 未核 |' % r['id'])
            continue
        lines.append('| %s | %d | %s | %s | %d | %d | %d | %d | %d | %d |' % (
            r['id'], r['found'], local_time(r['first']), local_time(r['last']), r['tools'],
            len(r['forbidden']), len(r['urls']), len(r['reads']), len(r['shell']), len(r['denied'])))
    lines.append('')
    for r in results:
        lines.append('## ' + r['id'])
        if not r['found']:
            lines += ['- 找不到逐字紀錄：`%s`。報告要寫「遵守度未核」。' % r['project'], '']
            continue
        lines.append('- 模型：' + ('、'.join(r['models']) or '未知'))
        lines += section('禁用工具', r['forbidden'])
        lines += section('不在允許清單的網址', r['urls'])
        lines += section('資料夾以外的檔案', r['reads'])
        lines += section('執行指令', r['shell'])
        lines += section('find', r['finds'])
        lines += section('form_input', r['form_inputs'])
        lines += section('權限拒絕', r['denied'])
        lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial_json')
    parser.add_argument('--projects', default=os.path.expanduser('~/.claude/projects'))
    args = parser.parse_args()

    with io.open(args.trial_json, encoding='utf-8') as fh:
        trial = json.load(fh)
    root = trial['root']
    allowed = list(trial.get('allowed_urls') or [trial['start_url']])
    if trial.get('login_url'):
        allowed.append(trial['login_url'])
    results = [audit_tester(t['id'], os.path.join(root, t['id']), args.projects, allowed) for t in trial['testers']]
    report = render(results)
    path = os.path.join(root, '_coordinator', 'audit.md')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(report)
    missing = [r['id'] for r in results if not r['found']]
    print('寫入：%s' % path)
    print('測試員 %d 位，找不到紀錄：%s' % (len(results), '、'.join(missing) or '無'))
    for r in results:
        if r['found']:
            print('%s 工具 %d 次，禁用 %d，網址 %d，外部檔案 %d，權限拒絕 %d' % (
                r['id'], r['tools'], len(r['forbidden']), len(r['urls']), len(r['reads']), len(r['denied'])))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
