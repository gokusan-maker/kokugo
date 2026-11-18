"""冬休みテキストの長文（基礎 W01〜W20、発展 WH01〜WH20）。

ファイルを分けて書いているので、ここで番号順にまとめる。
"""
import importlib


def _load(level):
    out = []
    for i in range(1, 6):
        try:
            mod = importlib.import_module("%s.%s_%d" % (__name__, level, i))
        except ModuleNotFoundError as e:
            if e.name != "%s.%s_%d" % (__name__, level, i):
                raise
            continue
        out += mod.WINTER
    return sorted(out, key=lambda p: int(p["id"].lstrip("WH")))


WINTER = {"kiso": _load("kiso"), "hatten": _load("hatten")}
