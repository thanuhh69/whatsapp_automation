import pytest
from backend.services.message_template import render_template

def test_render_template_success():
    tpl = "Hello {{name}}, your email is {{email}}."
    ctx = {"name": "Alice", "email": "alice@example.com"}
    rendered, ok, err = render_template(tpl, ctx)
    assert ok is True
    assert rendered == "Hello Alice, your email is alice@example.com."
    assert err == ""

def test_render_template_missing_variable_lenient():
    tpl = "Hello {{name}}, welcome to {{organization}}!"
    ctx = {"name": "Bob"}
    rendered, ok, err = render_template(tpl, ctx, skip_on_missing=False)
    assert ok is True
    assert "[Missing organization]" in rendered

def test_render_template_missing_variable_strict():
    tpl = "Hello {{name}}, your link is {{link}}."
    ctx = {"name": "Charlie"}
    rendered, ok, err = render_template(tpl, ctx, skip_on_missing=True)
    assert ok is False
    assert "Missing placeholder" in err
