"""日本語フォントの登録。

IPAex明朝・IPAexゴシック（またはIPA明朝・IPAゴシック）を探して登録する。
見つからない場合は環境変数 KOKUGO_FONT_MINCHO / KOKUGO_FONT_GOTHIC で
TrueType フォント（.ttf / .ttc）のパスを指定できる。
"""
import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

MINCHO = "Mincho"
GOTHIC = "Gothic"

_CANDIDATES = {
    MINCHO: [
        "/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf",
        "/usr/share/fonts/truetype/ipaexfont-mincho/ipaexm.ttf",
        "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
        "/Library/Fonts/ipaexm.ttf",
        os.path.expanduser("~/Library/Fonts/ipaexm.ttf"),
        "C:/Windows/Fonts/ipaexm.ttf",
        "C:/Windows/Fonts/msmincho.ttc",
    ],
    GOTHIC: [
        "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
        "/usr/share/fonts/truetype/ipaexfont-gothic/ipaexg.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/Library/Fonts/ipaexg.ttf",
        os.path.expanduser("~/Library/Fonts/ipaexg.ttf"),
        "C:/Windows/Fonts/ipaexg.ttf",
        "C:/Windows/Fonts/msgothic.ttc",
    ],
}

_ENV = {MINCHO: "KOKUGO_FONT_MINCHO", GOTHIC: "KOKUGO_FONT_GOTHIC"}
_registered = False


def _find(name):
    env = os.environ.get(_ENV[name])
    paths = ([env] if env else []) + _CANDIDATES[name]
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def register():
    global _registered
    if _registered:
        return
    found = {n: _find(n) for n in (MINCHO, GOTHIC)}
    if not found[MINCHO] and not found[GOTHIC]:
        raise SystemExit(
            "日本語フォントが見つかりません。IPAexフォントをインストールするか、\n"
            "環境変数 KOKUGO_FONT_MINCHO にフォントファイルのパスを指定してください。\n"
            "  例) sudo apt install fonts-ipaexfont"
        )
    # 片方しかなければもう片方で代用する
    found[MINCHO] = found[MINCHO] or found[GOTHIC]
    found[GOTHIC] = found[GOTHIC] or found[MINCHO]
    for name, path in found.items():
        if path.lower().endswith(".ttc"):
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(name, path))
    _registered = True
