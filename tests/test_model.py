import unittest

from reportkit import Columns, Document, Heading, List, Markdown, RawHTML, Report, Section


class ModelTests(unittest.TestCase):
    def test_composition_preserves_order_and_nesting(self):
        report = Report(author="Ada")
        report.heading(2, "Summary")
        with report.section("Details") as section:
            report.markdown("A *finding*.")
            with report.columns(2) as columns:
                report.add(object(), caption="Left")
                report.add(object(), caption="Right")
        report.list(["done"])

        self.assertEqual([type(n) for n in report.document.children], [Heading, Section, List])
        self.assertIs(report.document.children[1], section)
        self.assertIs(section.children[1], columns)
        self.assertEqual(len(columns.children), 2)
        self.assertEqual(columns.children[0].caption, "Left")

    def test_context_restores_parent_after_exception(self):
        report = Report()
        with self.assertRaisesRegex(RuntimeError, "stop"):
            with report.section("Before"):
                raise RuntimeError("stop")
        report.markdown("After")
        self.assertEqual(len(report.document.children), 2)

    def test_structural_validation(self):
        self.assertEqual(Report("page title").document.title, "page title")
        self.assertEqual(Document(title="page title").title, "page title")
        with self.assertRaisesRegex(TypeError, "title"):
            Report(title=123)
        root = Document()
        node = Heading(1, "One")
        root.append(node)
        with self.assertRaisesRegex(ValueError, "one container"):
            Section("Two").append(node)
        with self.assertRaisesRegex(ValueError, "cannot be nested"):
            root.append(Document())
        with self.assertRaisesRegex(ValueError, "heading level"):
            Heading(0, "Invalid")
        with self.assertRaisesRegex(ValueError, "column count"):
            Columns(0)
        with self.assertRaisesRegex(TypeError, "iterable"):
            List("not a list")

    def test_composition_does_not_render_artifact(self):
        class Explodes:
            def to_html(self):
                raise AssertionError("rendered during composition")

        report = Report()
        report.add(Explodes())
        self.assertEqual(len(report.document.children), 1)

    def test_list_shortcuts_and_nested_validation(self):
        report = Report()
        ordered = report.ordered(["one", ["child", ["grandchild"]], "two"])
        unordered = report.unordered(["last"])
        self.assertTrue(ordered.ordered)
        self.assertFalse(unordered.ordered)
        self.assertEqual(ordered.items, ("one", ("child", ("grandchild",)), "two"))
        with self.assertRaisesRegex(ValueError, "nested list must follow"):
            report.list([["orphan"]])
        with self.assertRaisesRegex(ValueError, "nested list must follow"):
            report.list(["one", ["child"], ["orphan"]])
        with self.assertRaisesRegex(TypeError, "strings or nested lists"):
            report.list([123])

    def test_paragraph_and_raw_html_nodes(self):
        report = Report()
        self.assertIsInstance(report.paragraph("**Hello**"), Markdown)
        self.assertIsInstance(report.add("<strong>trusted</strong>"), RawHTML)
        self.assertIsInstance(report.raw_html("<hr>"), RawHTML)
        with self.assertRaisesRegex(ValueError, "caption"):
            report.add("<b>text</b>", caption="Lost")
        self.assertEqual(len(report.document.children), 3)

    def test_concat_copies_structure_and_keeps_artifact_references(self):
        value = object()
        left = Report("Left title", description="Left", author="Ada", date="2026-09-25")
        with left.section("First"):
            with left.columns(2):
                left.add(value)
                left.list(["parent", ["child"]])
        right = Report("Right title", description="Right", author="Bob")
        right.heading(2, "Second")

        combined = left.concat(right)
        self.assertEqual([node.title for node in combined.document.children], ["First", "Second"])
        self.assertEqual(
            (combined.document.title, combined.document.description,
             combined.document.author, combined.document.date),
            ("Left title", "Left", "Ada", "2026-09-25"),
        )
        copied_section = combined.document.children[0]
        copied_columns = copied_section.children[0]
        self.assertIsNot(copied_section, left.document.children[0])
        self.assertIsNot(copied_columns, left.document.children[0].children[0])
        self.assertIs(copied_columns.children[0].value, value)
        self.assertIs(copied_section._parent, combined.document)
        self.assertIs(copied_columns._parent, copied_section)
        copied_section.append(Heading(3, "Only in combined"))
        left.heading(1, "Only in left")
        self.assertEqual(len(left.document.children[0].children), 1)
        self.assertEqual(len(combined.document.children), 2)
        self.assertEqual([node.title for node in (left + right).document.children],
                         ["First", "Only in left", "Second"])
        with self.assertRaises(TypeError):
            left.concat("bad")
        with self.assertRaises(TypeError):
            _ = left + "bad"


if __name__ == "__main__":
    unittest.main()
