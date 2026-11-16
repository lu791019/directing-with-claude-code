#!/usr/bin/env python3
"""把雛形複製成測試用複本，拿掉給人看的附註，避免測試員讀到答案。

用法：python prepare_prototype.py <trial.json>

產出 <root>/site/<start_url 的檔名>，並印出起站指令。原檔不動。
複本會移除切換模式鈕、SECTION_WORDS 開頭的段落，以及異動雛形的藍框（CHG）。各雛形的段名不一，開工時要親眼確認。
修完雛形要重跑一次。只用標準函式庫。
"""
import argparse
import hashlib
import io
import json
import os
import posixpath
import sys
from urllib.parse import unquote, urlparse

MARKER = '<!-- ux-blackbox-trial 測試複本 -->'
SECTION_WORDS = ('Open Questions', '待確認事項', '決議紀錄', '已裁示', '異動清單', '實作前置', '模擬界線')
CLEANUP = '''<script>
(function () {
  var HIDE = /%s/;
  var HEADS = 'h1,h2,h3,h4,.heading-01';
  var btn = document.getElementById('protoModeBtn');
  if (btn) btn.remove();
  // 藍框標出「跟現況不同的地方」，會把測試員引到新功能上；拿掉框與編號，內容留著
  Array.prototype.forEach.call(document.querySelectorAll('.proto-changed'), function (el) {
    el.classList.remove('proto-changed');
    el.removeAttribute('data-proto-changed');
  });
  function isHeading(el) { return el.matches(HEADS) || !!el.querySelector(HEADS); }
  Array.prototype.forEach.call(document.querySelectorAll(HEADS), function (head) {
    if (!HIDE.test(head.textContent)) return;
    var next = head.nextElementSibling;
    while (next && !isHeading(next)) {
      var gone = next;
      next = next.nextElementSibling;
      gone.remove();
    }
    head.remove();
  });
})();
</script>
'''


def inject(html):
    """腳本要放在組裝殼的腳本之後，殼載入時還要綁模式鈕。"""
    at = html.lower().rfind('</body>')
    if at < 0:
        sys.exit('雛形沒有 </body>，不是組裝後的單檔雛形')
    return html[:at] + MARKER + '\n' + CLEANUP % '|'.join(SECTION_WORDS) + html[at:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial_json')
    args = parser.parse_args()

    with io.open(args.trial_json, encoding='utf-8') as fh:
        trial = json.load(fh)
    if trial.get('target') != 'prototype' or not trial.get('prototype_source'):
        sys.exit('trial.json 要設 target: prototype 與 prototype_source')

    source = trial['prototype_source']
    with io.open(source, encoding='utf-8') as fh:
        html = fh.read()
    if 'id="protoModeBtn"' not in html:
        print('注意：找不到切換模式鈕，確認這是組裝後的雛形')

    url = urlparse(trial['start_url'])
    name = posixpath.basename(unquote(url.path))
    if url.hostname not in ('127.0.0.1', 'localhost') or not url.port or not name:
        sys.exit('start_url 要是 http://127.0.0.1:<埠>/<檔名>，雛形一律走本機站')

    site = os.path.join(os.path.normpath(trial['root']), 'site')
    os.makedirs(site, exist_ok=True)
    target = os.path.join(site, name)
    with io.open(target, 'w', encoding='utf-8', newline='') as fh:
        fh.write(inject(html))

    digest = hashlib.sha1(html.encode('utf-8')).hexdigest()[:8]
    print('寫入：%s（來源 %s）' % (target, digest))
    leftovers = [w for w in ('模擬界線', '不會動', '不過濾') if w in html]
    if leftovers:
        print('注意：雛形含 %s，開工時確認這段已不在畫面上' % '、'.join(leftovers))
    print('起站：python -m http.server %d --bind 127.0.0.1 --directory "%s"' % (url.port, site))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    main()
