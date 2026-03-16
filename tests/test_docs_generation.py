from skivvy import matchers
from skivvy.skivvy import matchers_markdown, settings_markdown


def test_settings_markdown_includes_reference_header_and_table():
    markdown = settings_markdown()

    assert markdown.startswith("# Settings Reference\n\n")
    assert "[README](../README.md) · [Matchers Reference](matchers.md)" in markdown
    assert "| Setting | Default | Description |" in markdown


def test_matchers_markdown_includes_reference_header_and_table(monkeypatch):
    matcher_dict = {
        "$demo": lambda expected, actual: (True, "ok"),
    }
    matcher_dict["$demo"].__doc__ = "Demo matcher."
    monkeypatch.setattr(matchers, "matcher_dict", matcher_dict)

    markdown = matchers_markdown()

    assert markdown.startswith("# Matchers Reference\n\n")
    assert "[README](../README.md) · [Settings Reference](settings.md)" in markdown
    assert "| Matcher | Description |" in markdown
    assert "| `$demo` | Demo matcher. |" in markdown
