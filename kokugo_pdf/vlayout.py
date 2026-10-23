"""縦書きの組版エンジン。

文字を上から下へ並べて列をつくり、列を右から左へページに流しこむ。

  R(…)      文字の一続き（書体・大きさ・色・傍線を指定できる）
  Para(…)   段落。高さに合わせて複数の列に折り返す
  Book      横向きA4のPDF（ページ番号・フッター）
  Flow      段落や固定幅のブロックを、右から左へページをまたいで並べる

数字は2〜3けたなら縦中横（横に並べて1字分）、1けたや英字は全角にして縦に立てる。
"""
import re

from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .fonts import GOTHIC, MINCHO, register
from .vertical import HANG, NO_END, draw_char

# 赤シートで消える朱色
RED = HexColor("#E8380D")
LIGHT = Color(0.93, 0.93, 0.93)
MID = Color(0.55, 0.55, 0.55)
PAGE = landscape(A4)
MARGIN = 13 * mm
TOP = 14 * mm
BOTTOM = 15 * mm
PITCH = 1.7          # 列の幅（文字の大きさに対する倍率）

_CHAR_MAP = {"→": "↓", "(": "（", ")": "）", " ": "　", "/": "／", "~": "〜"}


class R:
    """文字の一続き。指定しなかった項目は段落の設定を使う。

    side  傍線（"line"=黒の傍線, "red"=朱色の傍線）
    """

    def __init__(self, text, font=None, size=None, color=None, side=None):
        self.text, self.font, self.size, self.color, self.side = text, font, size, color, side


class Tok:
    __slots__ = ("ch", "font", "size", "color", "side", "tcy", "adv")

    def __init__(self, ch, font, size, color, side, tcy=False):
        self.ch, self.font, self.size, self.color, self.side, self.tcy = ch, font, size, color, side, tcy
        self.adv = size


NL = object()


def _fullwidth(ch):
    if ch in _CHAR_MAP:
        return _CHAR_MAP[ch]
    if "!" <= ch <= "~":
        return chr(ord(ch) + 0xFEE0)
    return ch


def tokens(runs, font, size, color):
    for r in runs:
        if isinstance(r, str):
            r = R(r)
        f, s, col = r.font or font, r.size or size, r.color or color
        for m in re.finditer(r"[0-9]+|.", r.text, re.S):
            t = m.group(0)
            if t == "\n":
                yield NL
            elif t.isascii() and t.isdigit() and 2 <= len(t) <= 3:
                yield Tok(t, f, s, col, r.side, tcy=True)
            else:
                for ch in t:
                    yield Tok(_fullwidth(ch), f, s, col, r.side)


class Column:
    def __init__(self, items, base):
        self.items = items
        self.w = max([t.size for _, t in items] or [base]) * PITCH


def layout(runs, height, font=MINCHO, size=10.5, color=black, indent=0, hang=0):
    """runs を高さ height の列に折り返す。indent は1列目、hang は2列目以降の字下げ（字数）。"""
    cols, cur, y = [], [], indent * size
    for t in tokens(runs, font, size, color):
        if t is NL:
            cols.append(Column(cur, size))
            cur, y = [], hang * size
            continue
        over = y + t.adv > height + 0.01
        if cur and over and not (t.ch in HANG and y + t.adv <= height + t.adv + 0.01):
            cols.append(Column(cur, size))
            cur, y = [], hang * size
        elif cur and t.ch in NO_END and y + 2 * t.adv > height + 0.01:
            cols.append(Column(cur, size))
            cur, y = [], hang * size
        cur.append((y, t))
        y += t.adv
    if cur:
        cols.append(Column(cur, size))
    return cols


def draw_column(c, col, xc, y_top):
    for y, t in col.items:
        c.setFillColor(t.color)
        if t.tcy:
            fs = t.size * min(1.0, 0.95 * t.size / stringWidth(t.ch, t.font, t.size))
            c.setFont(t.font, fs)
            c.drawCentredString(xc, y_top - y - t.size / 2 - 0.35 * fs, t.ch)
        else:
            c.setFont(t.font, t.size)
            draw_char(c, t.ch, xc, y_top - y, t.size)
    c.setFillColor(black)
    # 傍線（右側）
    run = None
    for y, t in col.items + [(None, None)]:
        key = t.side if t is not None else None
        if run and (key != run[0]):
            side, y0, y1, sz = run
            c.setStrokeColor(RED if side == "red" else black)
            c.setLineWidth(0.9)
            x = xc + 0.62 * sz
            c.line(x, y_top - y0, x, y_top - y1)
            run = None
        if key and run is None:
            run = [key, y, y + t.adv, t.size]
        elif key and run:
            run[2] = y + t.adv
    c.setStrokeColor(black)
    c.setLineWidth(1)


def text_height(runs, size):
    return sum(t.adv for t in tokens(runs, MINCHO, size, black) if t is not NL)


def draw_text(c, runs, xc, y_top, height, font=MINCHO, size=10.5, color=black, indent=0, hang=0):
    """runs を xc の列から左へ折り返して描き、使った幅を返す。"""
    cols = layout(runs, height, font, size, color, indent, hang)
    x = xc + (cols[0].w / 2 if cols else 0)
    for col in cols:
        draw_column(c, col, x - col.w / 2, y_top)
        x -= col.w
    return sum(col.w for col in cols)


class Para:
    def __init__(self, runs, font=MINCHO, size=10.5, color=black, indent=0, hang=0, after=3):
        self.runs = [R(runs)] if isinstance(runs, str) else runs
        self.font, self.size, self.color = font, size, color
        self.indent, self.hang, self.after = indent, hang, after

    def columns(self, height):
        return layout(self.runs, height, self.font, self.size, self.color, self.indent, self.hang)

    def width(self, height):
        return sum(c.w for c in self.columns(height)) + self.after


# ---------------------------------------------------------------- ページ

class Book:
    """横向きA4のPDF。new_page() のたびにフッターとページ番号を描く。"""

    def __init__(self, path, title, footer):
        register()
        self.c = canvas.Canvas(path, pagesize=PAGE)
        self.c.setTitle(title)
        self.c.setAuthor("中学受験 国語ドリル")
        self.footer = footer
        self.page = 0

    def new_page(self):
        if self.page:
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFont(GOTHIC, 7)
        c.setFillColor(MID)
        c.drawString(MARGIN, 7 * mm, self.footer)
        c.drawRightString(PAGE[0] - MARGIN, 7 * mm, str(self.page))
        c.setFillColor(black)
        return c

    def save(self):
        self.c.showPage()
        self.c.save()


def name_box(c, score=None):
    """左はしの名前・日付・得点の欄。使った幅を返す。"""
    w = 15 * mm
    x0, y0, y1 = MARGIN, BOTTOM, PAGE[1] - TOP
    c.setLineWidth(0.8)
    c.rect(x0, y0, w, y1 - y0)
    cells = [("月　　日", 32 * mm), ("名前", None)] + ([("得点", 34 * mm)] if score else [])
    fixed = sum(h for _, h in cells if h)
    y = y1
    for label, h in cells:
        h = h or (y1 - y0 - fixed)
        draw_text(c, [R(label)], x0 + w - 4.5 * mm, y - 2.5 * mm, h, font=GOTHIC, size=8.5)
        if label == "得点":
            draw_text(c, [R("／%d" % score)], x0 + w / 2, y - h + 14 * mm, 14 * mm, font=GOTHIC, size=10)
        y -= h
        if y > y0 + 1:
            c.line(x0, y, x0 + w, y)
    return w + 4 * mm


class Flow:
    """右から左へ列を流しこむ。ページが足りなくなったら次のページへ。"""

    def __init__(self, book, header=None, score=None):
        self.book, self.header, self.score = book, header, score
        self.top = PAGE[1] - TOP
        self.bottom = BOTTOM
        self.H = self.top - self.bottom
        self.x = None
        self.new_page()

    def new_page(self, first_header=True):
        c = self.book.new_page()
        self.c = c
        self.left = MARGIN + name_box(c, self.score)
        self.x = PAGE[0] - MARGIN
        if self.header:
            title, sub = self.header
            self.para(Para([R(title)], font=GOTHIC, size=16, after=0))
            if sub:
                self.para(Para([R(sub)], font=GOTHIC, size=8.5, after=2))
            self.rule(gap=4, width=1.4)

    def room(self):
        return self.x - self.left

    def need(self, w):
        if self.room() < w:
            self.new_page()

    def space(self, w):
        self.x -= w

    def rule(self, gap=3, width=0.5, color=black):
        self.need(2 * gap)
        x = self.x - gap
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.line(x, self.top, x, self.bottom)
        self.c.setStrokeColor(black)
        self.c.setLineWidth(1)
        self.x -= 2 * gap

    def para(self, p, top=0, height=None):
        for col in p.columns((height or self.H) - top):
            if col.w > self.room():
                self.new_page()
            draw_column(self.c, col, self.x - col.w / 2, self.top - top)
            self.x -= col.w
        self.x -= p.after

    def fixed(self, w, draw):
        """幅 w の領域を確保して draw(c, x_left, x_right, y_top, y_bottom) を呼ぶ。"""
        self.need(w)
        draw(self.c, self.x - w, self.x, self.top, self.bottom)
        self.x -= w

    def box(self, paras, pad=6, bg=LIGHT):
        """段落のまとまりを網かけの枠で囲む。"""
        inner = self.H - 2 * pad
        w = sum(p.width(inner) for p in paras) + 2 * pad
        self.need(w)
        c = self.c
        c.setFillColor(bg)
        c.setStrokeColor(MID)
        c.setLineWidth(0.6)
        c.rect(self.x - w, self.bottom, w, self.H, stroke=1, fill=1)
        c.setFillColor(black)
        c.setStrokeColor(black)
        x = self.x - pad
        for p in paras:
            for col in p.columns(inner):
                draw_column(c, col, x - col.w / 2, self.top - pad)
                x -= col.w
            x -= p.after
        self.x -= w + 4
