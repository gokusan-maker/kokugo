"""レベルごとの長文と暗記データ。

  key     ファイル名・アプリのURLで使う名前
  name    表示名
  passages 長文（1回に1題。第16回以降は data/extra_*.py に追加していく）
  anki    暗記データ（data/anki.py と同じ変数をもつ。anki_base ＋ data/anki_added.py の追加分）
"""
from types import SimpleNamespace

from . import anki, anki_hatten
from .anki_added import ADDED, NAMES
from .extra_hatten import EXTRA_HATTEN
from .extra_kiso import EXTRA_KISO
from .hatten_passages import HATTEN_PASSAGES
from .passages import PASSAGES

def _added(key):
    return SimpleNamespace(**{n: list(ADDED[key].get(n, [])) for n in NAMES})


def _merged(base, added):
    """もとのデータのあとに、追加したデータをつなげたもの（暗記ドリル用）。"""
    return SimpleNamespace(**{n: list(getattr(base, n)) + list(getattr(added, n)) for n in NAMES})


LEVELS = [
    {"key": "kiso", "name": "基礎", "desc": "小学5〜6年の標準レベル。消去法の手順を身につける。",
     "passages": PASSAGES + EXTRA_KISO, "anki_base": anki, "anki_added": _added("kiso")},
    {"key": "hatten", "name": "発展", "desc": "難関中学レベル。長めの文章と、まぎらわしい選択肢で実戦力をつける。",
     "passages": HATTEN_PASSAGES + EXTRA_HATTEN, "anki_base": anki_hatten, "anki_added": _added("hatten")},
]
for _lv in LEVELS:
    _lv["anki"] = _merged(_lv["anki_base"], _lv["anki_added"])
LEVEL = {lv["key"]: lv for lv in LEVELS}
