import unittest

from reportkit import Report


class TreeTests(unittest.TestCase):
    def test_tree_preserves_node_and_list_hierarchy(self):
        report = Report('Example')
        report.heading(1, 'Overview')
        report.paragraph('First line\nsecond line')
        with report.section('Details'):
            with report.columns(2):
                report.raw_html('<b>Note</b>')
                report.add(object(), caption='Chart')
            report.ordered(['Parent', ['Child', ['Grandchild']], 'Sibling'])

        self.assertEqual(
            report.to_tree(),
            """Document(title='Example')
└── Section(level=1, title='Overview')
    ├── Markdown('First line second line')
    └── Section(level=2, title='Details')
        ├── Columns(count=2)
        │   ├── RawHTML('<b>Note</b>')
        │   └── Artifact(builtins.object, caption='Chart')
        └── List(ordered=True)
            ├── Item('Parent')
            │   └── List(ordered=True)
            │       └── Item('Child')
            │           └── List(ordered=True)
            │               └── Item('Grandchild')
            └── Item('Sibling')""",
        )

    def test_artifact_values_are_not_inspected_or_rendered(self):
        class Artifact:
            def __repr__(self):
                raise AssertionError('artifact repr was called')

            def to_html(self):
                raise AssertionError('artifact was rendered')

        report = Report()
        self.assertEqual(report.to_tree(), 'Document(title=None)')
        report.add(Artifact())
        self.assertIn('Artifact(', report.to_tree())

    def test_long_text_is_abbreviated(self):
        report = Report()
        report.markdown('Long text ' * 100)
        tree = report.to_tree()
        self.assertIn('...', tree)
        self.assertEqual(len(tree.splitlines()), 2)
        self.assertLess(len(tree), 120)


if __name__ == '__main__':
    unittest.main()
