"""End-to-end UI tests (headless) and licensing tests."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from auditor import licensing, samples

APP = str(Path(__file__).resolve().parent.parent / "app.py")
CODE = "CBA-TEST-CODE-0001"


def make_app(secrets: dict | None = None, provider: str = "AWS") -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in (secrets or {}).items():
        at.secrets[k] = v
    at.session_state["files"] = ((f"{provider}.csv", samples.generate(provider).to_csv(index=False).encode()),)
    return at


def texts(at: AppTest) -> str:
    return " ".join(x.value for x in [*at.warning, *at.info, *at.error, *at.success, *at.caption])


# --- licensing ---------------------------------------------------------------
def test_codes_and_hashes():
    code = licensing.new_code()
    assert code.startswith("CBA-") and len(code) == 23
    h = licensing.hash_code(code)
    assert licensing.is_valid_code(code, [h])
    assert licensing.is_valid_code(code.lower(), [h])          # case-insensitive
    assert licensing.is_valid_code(code, [code])               # plain entries work too
    assert not licensing.is_valid_code("CBA-WRONG", [h])
    assert not licensing.is_valid_code("", [h])


def test_config_parsing_and_open_mode():
    cfg = licensing.Config.from_mapping({"PRO_ACCESS_CODES": "a, b", "FREE_FINDINGS": "5"})
    assert cfg.access_codes == ["a", "b"] and cfg.free_findings == 5 and cfg.monetized
    open_cfg = licensing.Config.from_mapping({})
    assert not open_cfg.monetized
    assert licensing.plan_for("", open_cfg) == licensing.PRO   # no codes configured -> all unlocked


def test_cli_generates_codes(capsys):
    assert licensing.main(["new-code", "2"]) == 0
    out = capsys.readouterr().out
    assert out.count("CODE: CBA-") == 2 and out.count("HASH: sha256:") == 2


# --- app ---------------------------------------------------------------------
def test_open_mode_everything_unlocked():
    at = make_app().run()
    assert not at.exception
    t = texts(at)
    assert "more opportunities" not in t and "Pro feature" not in t
    assert "estimates" in t                                    # disclaimer is visible
    assert len(at.get("download_button")) >= 4                # all exports available


def test_free_plan_is_gated():
    at = make_app({"PRO_ACCESS_CODES": [licensing.hash_code(CODE)], "BUY_URL": "https://example.com/buy",
                   "FREE_FINDINGS": 2}).run()
    assert not at.exception
    t = texts(at)
    assert "more opportunities" in t                           # findings locked
    assert "Report exports are a Pro feature" in t
    assert len(at.get("download_button")) <= 1                 # only explorer CSV
    assert at.get("link_button")                               # upgrade CTA rendered


def test_pro_code_unlocks():
    at = make_app({"PRO_ACCESS_CODES": [licensing.hash_code(CODE)]}).run()
    at.text_input(key="access_code").set_value(CODE).run()
    assert not at.exception
    t = texts(at)
    assert "Pro unlocked" in t or "Pro plan" in t
    assert "more opportunities" not in t and "Pro feature" not in t
    assert len(at.get("download_button")) >= 4


def test_bad_code_rejected():
    at = make_app({"PRO_ACCESS_CODES": [licensing.hash_code(CODE)]}).run()
    at.text_input(key="access_code").set_value("CBA-NOPE").run()
    assert "Invalid access code" in texts(at)


def test_free_plan_line_item_limit():
    at = make_app({"PRO_ACCESS_CODES": [licensing.hash_code(CODE)], "FREE_MAX_LINE_ITEMS": 100}).run()
    assert not at.exception
    assert "free plan analyzes bills up to 100" in texts(at)


def test_owner_key_limited_and_not_given_to_free_users():
    secrets = {"PRO_ACCESS_CODES": [licensing.hash_code(CODE)], "GEMINI_API_KEY": "owner-key",
               "AI_REQUESTS_PER_SESSION": 3}
    at = make_app(secrets).run()
    assert "add your own free Gemini key" in texts(at)        # free users don't get the owner's key
    at.text_input(key="access_code").set_value(CODE).run()
    assert "3 AI requests left" in texts(at)
    at.session_state["ai_used"] = 3
    at.run()
    assert "reached the AI limit" in texts(at)


def test_clear_drops_the_bill():
    at = make_app().run()
    clear = next(b for b in at.button if "Clear" in b.label)
    clear.click().run()
    assert not at.exception
    assert at.session_state["files"] is None if "files" in at.session_state else True
    assert "_analysis" not in at.session_state
    assert any("Upload a bill" in i.value for i in at.info)


@pytest.mark.parametrize("provider", ["GCP", "Azure"])
def test_arabic_ui_renders(provider):
    at = make_app(provider=provider).run()
    at.selectbox(key="lang").set_value("العربية").run()
    assert not at.exception
    assert "تقديرية" in texts(at)
