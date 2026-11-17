import unittest
from pathlib import Path

from proofloop.appmap import check, coverage, load, parse, unreachable

GOOD = '''# App map: Demo
app: com.example.demo

## screen: home
anchors: "Home", "Add"
- tap "Add" -> editor
- tap "Buy" -> ? (not taken: purchase)
- back -> exit
- rule: lists items
- hazard: banner covers the list

## screen: editor
anchors: "New item"
- tap "Save" -> home

## screen: orphan
anchors: "Lost"

## route: add-item
1. home: tap "Add"
2. editor: tap "Save"
'''


class AppMapTest(unittest.TestCase):
    def test_parse_and_check(self):
        m = parse(GOOD)
        self.assertEqual(m.app, "com.example.demo")
        self.assertEqual(list(m.screens), ["home", "editor", "orphan"])
        self.assertEqual(m.screens["home"].edges[1].reason, "not taken: purchase")
        self.assertEqual(m.screens["home"].notes, [("rule", "lists items"), ("hazard", "banner covers the list")])
        self.assertEqual(check(m), [])
        self.assertEqual(unreachable(m), ["orphan"])

    def test_errors(self):
        bad = GOOD.replace('-> editor', '-> nowhere').replace('- rule:', '- tip:') \
                  .replace('anchors: "Lost"', '').replace('1. home:', '1. attic:')
        errs = "\n".join(check(parse(bad)))
        for want in ("unknown screen 'nowhere'", "unknown note kind 'tip'",
                     "'orphan' has no anchors", "route 'add-item': unknown screen 'attic'"):
            self.assertIn(want, errs)

    def test_coverage(self):
        flow = '- launchApp:\n    stopApp: false\n- tapOn: "Add"\n- assertVisible: "New item"\n'
        cov = coverage(parse(GOOD), [flow])
        self.assertEqual(cov["screens"], {"home": True, "editor": True, "orphan": False})
        self.assertTrue(cov["edges"]['home: tap "Add" -> editor'])
        self.assertFalse(cov["edges"]['editor: tap "Save" -> home'])
        self.assertNotIn('home: tap "Buy" -> ?', cov["edges"])  # untaken actions are not coverage gaps

    def test_checked_in_maps_are_valid(self):
        root = Path(__file__).resolve().parent.parent / "tasks"
        maps = sorted(root.glob("*/app-map.md"))
        self.assertTrue(maps)
        for p in maps:
            self.assertEqual(check(load(p)), [], p)


if __name__ == "__main__":
    unittest.main()
