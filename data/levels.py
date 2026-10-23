"""レベルごとの長文と暗記データ。

  key     ファイル名・アプリのURLで使う名前
  name    表示名
  passages 長文（1回に1題）
  anki    暗記データのモジュール（data/anki.py と同じ変数をもつ）
"""
from . import anki, anki_hatten
from .hatten_passages import HATTEN_PASSAGES
from .passages import PASSAGES

LEVELS = [
    {"key": "kiso", "name": "基礎", "desc": "小学5〜6年の標準レベル。消去法の手順を身につける。",
     "passages": PASSAGES, "anki": anki},
    {"key": "hatten", "name": "発展", "desc": "難関中学レベル。長めの文章と、まぎらわしい選択肢で実戦力をつける。",
     "passages": HATTEN_PASSAGES, "anki": anki_hatten},
]
LEVEL = {lv["key"]: lv for lv in LEVELS}
