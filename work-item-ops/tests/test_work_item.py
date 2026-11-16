"""work_item.py 單元測試：用假的工單系統，不呼叫 gh、不碰任何真實 repo。
執行：python3 -m unittest work-item-ops/tests/test_work_item.py"""
import importlib.util, pathlib, sys, unittest

spec = importlib.util.spec_from_file_location(
    "work_item", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "work_item.py")
wi = importlib.util.module_from_spec(spec); sys.modules["work_item"] = wi; spec.loader.exec_module(wi)


class FakeTracker:
    def __init__(self):
        self.items = {"42": wi.Item("42", "匯出功能", "進行中", ("dev",)),
                      "40": wi.Item("40", "上層需求", "進行中", ("pm",))}
        self.writes = []

    def statuses(self): return ["進行中", "待驗收", "完成"]
    def get(self, n): return self.items[n]
    def comment(self, n, body): self.writes.append(("comment", n, body))
    def assign(self, n, a): self.writes.append(("assign", n, a))
    def set_status(self, n, s): self.writes.append(("set_status", n, s))


class T(unittest.TestCase):
    def test_unknown_status_refused_before_any_write(self):
        t = FakeTracker()
        with self.assertRaises(wi.TrackerError):
            wi.plan_finish(t, ["42"], "done", "pm", "待驗證")
        self.assertEqual(t.writes, [])

    def test_plan_is_read_only(self):
        t = FakeTracker()
        steps = wi.plan_finish(t, ["42", "40"], "done", "pm", "待驗收")
        self.assertEqual(t.writes, [])
        self.assertEqual([(s.number, s.action) for s in steps],
                         [("42", "comment"), ("42", "assign"), ("42", "set_status"), ("40", "set_status")])

    def test_comment_only_on_main_item_and_skip_existing_assignee(self):
        t = FakeTracker()
        steps = wi.plan_finish(t, ["42", "40"], "done", "pm", "待驗收")
        self.assertNotIn(("40", "comment"), [(s.number, s.action) for s in steps])
        self.assertNotIn(("40", "assign"), [(s.number, s.action) for s in steps])

    def test_apply_writes_planned_steps(self):
        t = FakeTracker()
        steps = wi.plan_finish(t, ["42"], "done", "pm", "待驗收")
        wi.apply_steps(t, steps, "done", "pm", "待驗收")
        self.assertEqual(t.writes, [("comment", "42", "done"), ("assign", "42", "pm"), ("set_status", "42", "待驗收")])

    def test_github_adapter_status_from_labels(self):
        class R:
            returncode, stderr = 0, ""
            def __init__(self, out): self.stdout = out
        calls = []
        def runner(cmd, **kw):
            calls.append(cmd)
            return R('[{"name":"status:待驗收"},{"name":"bug"},{"name":"status:完成"}]')
        gh = wi.GitHubIssues(repo="example/demo", runner=runner)
        self.assertEqual(gh.statuses(), ["完成", "待驗收"])
        self.assertEqual(calls[0][:3], ["gh", "label", "list"])


if __name__ == "__main__":
    unittest.main()
