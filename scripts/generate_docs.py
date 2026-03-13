"""Generate reference documentation from settings and matchers metadata."""

from pathlib import Path

from skivvy.skivvy import matchers_markdown, settings_markdown

docs = Path(__file__).parent.parent / "docs"
docs.mkdir(exist_ok=True)

(docs / "settings.md").write_text(settings_markdown())
(docs / "matchers.md").write_text(matchers_markdown())

print(f"Docs written to {docs}/")
