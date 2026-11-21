"""Browser-level: an integer field refuses a fraction with the exact message the BA asked for,
and decimal fields keep accepting fractions (real Chromium, generated app)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.agents.architect import build_architecture
from backend.agents.developer.generator import generate

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "backend" / "agents" / "architect" / "tests" / "fixtures"
needs_browser = pytest.mark.skipif(
    shutil.which("node") is None or not (ROOT / "tests" / "e2e" / "node_modules" / "@playwright").exists(),
    reason="Node.js and the Playwright packages in tests/e2e are needed",
)


def _app(tmp_path, name):
    req = json.loads((FIXTURES / f"{name}.requirements.json").read_text(encoding="utf-8"))
    arch = build_architecture(req)
    generate(req, arch, tmp_path)
    return arch


def _errors(app_dir, values):
    out = subprocess.run(["node", str(ROOT / "tests/e2e/live/field_errors.mjs"), str(app_dir), json.dumps(values)],
                         capture_output=True, text=True, timeout=120, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_generated_app_carries_the_invalid_message(tmp_path):
    arch = _app(tmp_path, "real_llm_inventory_ar")
    assert "يجب أن تكون الكمية عدداً صحيحاً" in (tmp_path / "app.js").read_text(encoding="utf-8")
    assert arch["messages"]["invalid"]  # the screen-level fallback is still there


@needs_browser
def test_fraction_in_integer_field_shows_the_exact_message(tmp_path):
    _app(tmp_path, "real_llm_inventory_ar")
    result = _errors(tmp_path, {"name": "سكر", "quantity": "2.5", "price": "8"})
    assert result["errors"]["quantity"] == "يجب أن تكون الكمية عدداً صحيحاً"
    assert result["errors"]["price"] in (None, "")  # 8 is fine; decimals stay allowed
    assert result["rows"] == 0  # nothing saved


@needs_browser
def test_decimal_fields_still_accept_fractions(tmp_path):
    _app(tmp_path, "real_llm_inventory_ar")
    result = _errors(tmp_path, {"name": "سكر", "quantity": "3", "price": "2.75"})
    assert not any(result["errors"].values()) and result["rows"] == 1


@needs_browser
def test_without_a_custom_message_the_app_language_fallback_is_used(tmp_path):
    arch = _app(tmp_path, "scenario_b_inventory_ar")  # no whole-number criterion: no fields[].messages.invalid
    integer = next(f for f in arch["entity"]["fields"] if f["type"] == "integer")
    values = {f["name"]: ("2.5" if f is integer else ("10" if f["type"] in ("integer", "decimal") else "قيمة"))
              for f in arch["entity"]["fields"] if f["type"] in ("string", "text", "integer", "decimal")}
    result = _errors(tmp_path, values)
    assert result["errors"][integer["name"]] == arch["messages"]["invalid"] == "القيمة غير صحيحة"
