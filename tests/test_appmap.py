import unittest
from pathlib import Path

from proofloop.appmap import ambiguous_anchors, check, coverage, load, parse, unreachable

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

    def test_ambiguous_anchors(self):
        self.assertEqual(ambiguous_anchors(parse(GOOD)), {})  # "Add" is tapped on its own screen only
        tabs = GOOD.replace('anchors: "New item"', 'anchors: "New item", "Lost"').replace(
            '- tap "Save" -> home', '- tap "Save" -> home\n- tap "Home" -> home')
        self.assertEqual(ambiguous_anchors(parse(tabs)),
                         {("home", "Home"): ["editor"], ("editor", "Lost"): ["orphan"], ("orphan", "Lost"): ["editor"]})

    def test_sunflower_tab_labels_are_ambiguous(self):
        amb = ambiguous_anchors(load(Path(__file__).parent.parent / "tasks" / "sunflower" / "app-map.md"))
        self.assertIn(("garden", "My garden"), amb)  # the anchor that recorded a wrong edge (ADR 0004)

    def test_shared_anchors_do_not_exempt_waits(self):
        from proofloop.flow import map_anchors
        anchors = map_anchors(Path(__file__).parent.parent / "tasks" / "sunflower" / "app-map.md")
        self.assertNotIn("Plant list", anchors)  # a tab on two screens
        self.assertNotIn("My garden", anchors)
        self.assertIn("Watering needs", anchors)

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
