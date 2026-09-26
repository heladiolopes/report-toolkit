import unittest

from reportkit import Columns, Document, Heading, List, Report, Section


class ModelTests(unittest.TestCase):
    def test_composition_preserves_order_and_nesting(self):
        report = Report("Analysis", author="Ada")
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


if __name__ == "__main__":
    unittest.main()
