import re
import sys
import unicodedata


def fullmatch(pattern: str, text: str) -> bool:
    return re.fullmatch(pattern, text) is not None


assert fullmatch(r"\w+", "中文")
assert fullmatch(r"\d+", "１２３")
assert not fullmatch(r"[A-Za-z0-9_]+", "中文")
assert fullmatch(r".", "🙂")
assert not fullmatch(r".", "e\u0301")
assert unicodedata.normalize("NFC", "é") == unicodedata.normalize("NFC", "e\u0301")

date = re.compile(r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})")
match = date.fullmatch("2026-08-31")
assert match is not None
assert match.groupdict() == {"year": "2026", "month": "08", "day": "31"}
assert date.sub(r"\g<day>/\g<month>/\g<year>", "2026-08-31") == "31/08/2026"

print(f"Python {sys.version.split()[0]} regex difference assertions: passed")
