"""build-situation-board.py 單元測試（暫存目錄，不碰正式檔）。執行：python3 -m unittest tests/test_build_situation_board.py"""
import hashlib, pathlib, subprocess, sys, tempfile, unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'build-situation-board.py'
BEGIN = '<!-- BEGIN generated: build-situation-board.py（勿手改；改 latest 後重跑） -->'
END = '<!-- END generated -->'
ROSTER = """# roster
| 代號 | 名稱 | 狀態 | 休眠起始日 | 喚醒條件 | 下次檢討日 |
|---|---|---|---|---|---|
| cmo | CMO 行銷長 | 活躍 | — | — | — |
| cpo | CPO 產品長 | 活躍 | — | — | — |
| cfo | CFO 財務長 | 休眠 | 2026-10-17 | x | 2027-01-17 |
"""
HEAD = '# DayDreamDex Situation Board\n> 最近更新：2026-10-17（承諾表手寫）\n\n## 承諾（Dex 確認要做的）\n| 事項 | 誰提的 |\n|---|---|\n| 甲 | CMO |\n\n'
TAIL = '\n## Board 會議紀錄\n- 2026-10-01 /board：測試｜摘要：state/board/x.md\n'

def latest(code, date, status, decisions=()):
    dec = '\n'.join(f'- {d}' for d in decisions) or '- 無日期的決策'
    return (f'# {code}\n## 最近更新：{date}（{code} 摘要）\n\n### 現況\n'
            + '\n'.join(f'- {s}' for s in status) + f'\n\n### 仍有效的決策\n{dec}\n\n### 待辦\n- t\n')

class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); r = pathlib.Path(self.tmp.name)
        (r / 'state' / 'cxo-context').mkdir(parents=True)
        (r / 'state' / 'cxo-roster.md').write_text(ROSTER, encoding='utf-8')
        self.write('cmo', latest('cmo', '2026-10-17', ['甲一', '甲二', '甲三', '甲四'], ['新決策（2026-10-10）', '舊決策（2026-08-01）']))
        self.write('cpo', latest('cpo', '2026-10-15', ['乙一']))
        self.board = r / 'state' / 'situation-board.md'
        self.board.write_text(HEAD + BEGIN + '\n舊內容\n' + END + '\n' + TAIL, encoding='utf-8')
        self.root = r

    def tearDown(self): self.tmp.cleanup()
    def write(self, code, text):
        (pathlib.Path(self.tmp.name) / 'state' / 'cxo-context' / f'{code}-latest.md').write_text(text, encoding='utf-8')
    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), '--today', '2026-10-17', *args], capture_output=True, text=True)
    def sha(self): return hashlib.sha256(self.board.read_bytes()).hexdigest()

    def test_outside_markers_untouched(self):
        self.assertEqual(self.run_script().returncode, 0)
        t = self.board.read_text(encoding='utf-8')
        self.assertTrue(t.startswith(HEAD)); self.assertTrue(t.endswith(TAIL))
        self.assertNotIn('舊內容', t)

    def test_content(self):
        self.run_script(); t = self.board.read_text(encoding='utf-8')
        self.assertIn('資料截至 2026-10-17', t)
        self.assertIn('  - 甲三', t); self.assertNotIn('甲四', t)           # 每位最多 3 條
        self.assertIn('完整見 `state/cxo-context/cmo-latest.md`', t)
        self.assertIn('- 休眠：CFO 財務長（見 `state/cxo-roster.md`）', t)    # 休眠行來自 roster
        self.assertLess(t.index('2026-10-17 CMO 行銷長'), t.index('2026-10-15 CPO 產品長'))
        self.assertIn('- 2026-10-10 CMO 行銷長：新決策（2026-10-10）', t)   # 近 30 天
        self.assertNotIn('舊決策', t)                                        # 超過 30 天

    def test_no_recent_decisions_section_when_zero(self):
        self.write('cmo', latest('cmo', '2026-10-17', ['甲一']))
        self.run_script(); self.assertNotIn('近 30 天決策', self.board.read_text(encoding='utf-8'))

    def test_dry_run_does_not_write(self):
        before = self.sha(); r = self.run_script('--dry-run')
        self.assertEqual(r.returncode, 0); self.assertIn('+## 現況', r.stdout); self.assertEqual(before, self.sha())

    def test_check(self):
        self.assertEqual(self.run_script('--check').returncode, 1)            # 舊內容 ≠ 重新產生
        self.run_script(); self.assertEqual(self.run_script('--check').returncode, 0)
        self.write('cpo', latest('cpo', '2026-10-16', ['乙改']))              # 改 latest 後
        before = self.sha(); self.assertEqual(self.run_script('--check').returncode, 1)
        self.assertEqual(before, self.sha())                                  # --check 不寫檔
        self.run_script(); self.assertEqual(self.run_script('--check').returncode, 0)

    def test_missing_markers_refuses(self):
        self.board.write_text(HEAD + TAIL, encoding='utf-8'); before = self.sha()
        r = self.run_script(); self.assertNotEqual(r.returncode, 0); self.assertIn('標記', r.stderr); self.assertEqual(before, self.sha())

    def test_idempotent(self):
        self.run_script(); first = self.sha(); self.run_script(); self.assertEqual(first, self.sha())

if __name__ == '__main__': unittest.main()
