import unittest
from pathlib import Path

from review_intelligence.cli import build_parser


ROOT = Path(__file__).resolve().parents[1]


class DocumentedSurfaceTests(unittest.TestCase):
    """Keep the README honest about what the CLI reaches and what the schemas do."""

    def setUp(self):
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.sources = {path: path.read_text(encoding="utf-8") for path in (ROOT / "src" / "review_intelligence").rglob("*.py")}

    def test_readme_names_every_cli_subcommand(self):
        subparsers = next(action for action in build_parser()._actions if getattr(action, "choices", None))
        for name in subparsers.choices:
            self.assertIn(f"`{name}`", self.readme)

    def test_readme_states_collectors_are_library_only_while_cli_does_not_import_them(self):
        self.assertNotIn("collectors", self.sources[ROOT / "src" / "review_intelligence" / "cli.py"])
        self.assertIn("Library only", self.readme)
        self.assertIn("`fetch_page`", self.readme)

    def test_readme_states_schemas_are_not_enforced_while_no_code_loads_them(self):
        for path, text in self.sources.items():
            self.assertNotIn("schema.json", text, path)
        self.assertIn("No code in `src/` loads or enforces them", self.readme)


if __name__ == "__main__":
    unittest.main()
