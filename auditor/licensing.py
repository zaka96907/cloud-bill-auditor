"""Plans, access codes and usage limits — a lightweight way to sell the app.

How selling works (no backend needed):
1. Create a payment link (Stripe Payment Link, Lemon Squeezy, Gumroad, PayPal…)
   and put it in ``BUY_URL``.
2. For every customer, generate an access code:
       python -m auditor.licensing new-code
   Send the code to the customer and add its *hash* to ``PRO_ACCESS_CODES``
   in Streamlit secrets. Storing hashes means leaked secrets don't leak codes.
3. To revoke a customer, delete their hash and reboot the app.

If ``PRO_ACCESS_CODES`` is empty, monetization is off and everyone gets every
feature (useful for self-hosting, demos and development).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets as _secrets
import sys
from dataclasses import dataclass, field
from typing import Mapping

FREE, PRO = "free", "pro"


def hash_code(code: str) -> str:
    return "sha256:" + hashlib.sha256(code.strip().upper().encode()).hexdigest()


def new_code() -> str:
    raw = _secrets.token_hex(8).upper()
    return f"CBA-{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:]}"


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = value.replace("\n", ",").split(",")
    return [str(v).strip() for v in value if str(v).strip()]


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    access_codes: list[str] = field(default_factory=list)   # "sha256:<hex>" or plain codes
    buy_url: str = ""
    price_label: str = ""
    contact_email: str = "support@cloudauditor.com"
    ai_requests_per_session: int = 10      # only applies when the owner's Gemini key is used
    free_findings: int = 3                 # findings shown in full on the free plan
    free_max_line_items: int = 50_000

    @property
    def monetized(self) -> bool:
        return bool(self.access_codes)

    @classmethod
    def from_mapping(cls, m: Mapping | None) -> "Config":
        m = m or {}
        get = (lambda k, d=None: m.get(k, d)) if hasattr(m, "get") else (lambda k, d=None: d)
        return cls(
            access_codes=_as_list(get("PRO_ACCESS_CODES")),
            buy_url=str(get("BUY_URL", "") or ""),
            price_label=str(get("PRICE_LABEL", "") or ""),
            contact_email=str(get("CONTACT_EMAIL", "") or "support@cloudauditor.com"),
            ai_requests_per_session=_as_int(get("AI_REQUESTS_PER_SESSION"), 10),
            free_findings=_as_int(get("FREE_FINDINGS"), 3),
            free_max_line_items=_as_int(get("FREE_MAX_LINE_ITEMS"), 50_000),
        )


def is_valid_code(code: str, allowed: list[str]) -> bool:
    if not code or not code.strip():
        return False
    hashed = hash_code(code)
    plain = code.strip().upper()
    ok = False
    for entry in allowed:                      # constant-time compare against every entry
        if entry.startswith("sha256:"):
            ok |= hmac.compare_digest(hashed, entry.lower())
        else:
            ok |= hmac.compare_digest(plain, entry.upper())
    return ok


def plan_for(code: str, cfg: Config) -> str:
    if not cfg.monetized:
        return PRO
    return PRO if is_valid_code(code, cfg.access_codes) else FREE


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("new-code", "hash"):
        print("usage: python -m auditor.licensing new-code [N] | hash CODE")
        return 2
    if argv[0] == "hash":
        print(hash_code(argv[1]))
        return 0
    n = int(argv[1]) if len(argv) > 1 else 1
    print("# Give the CODE to the customer; add the HASH to PRO_ACCESS_CODES in secrets.")
    for _ in range(n):
        c = new_code()
        print(f"CODE: {c}\nHASH: {hash_code(c)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
