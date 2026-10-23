"""PDF共通部品（文書テンプレート・文字スタイル・見出し）。"""
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate
from reportlab.platypus import Paragraph as _Paragraph
from reportlab.platypus import Table, TableStyle

from .fonts import GOTHIC, MINCHO, register

# 赤シートで消える朱色
RED = HexColor("#E8380D")
RED_HEX = "#E8380D"
LIGHT = Color(0.93, 0.93, 0.93)
MID = Color(0.6, 0.6, 0.6)

MARGIN = 14 * mm


class Paragraph(_Paragraph):
    """全角スペースが詰められないようにした Paragraph。

    reportlab は U+3000 を空白として詰めてしまうので、詰められない
    U+00A0（約0.29字分）4つに置きかえる。
    """

    def __init__(self, text, *a, **kw):
        super().__init__(text.replace("\u3000", "\u00a0" * 4), *a, **kw)


def style(name, font=MINCHO, size=10.5, leading=None, **kw):
    return ParagraphStyle(name, fontName=font, fontSize=size,
                          leading=leading or size * 1.55, wordWrap="CJK", **kw)


S = {}


def styles():
    if not S:
        register()
        S.update({
            "body": style("body"),
            "small": style("small", size=8.5),
            "tiny": style("tiny", size=7.5),
            "q": style("q", size=11),
            "goth": style("goth", font=GOTHIC, size=10),
            "gothsmall": style("gothsmall", font=GOTHIC, size=8.5),
            "h1": style("h1", font=GOTHIC, size=15, leading=20),
            "h2": style("h2", font=GOTHIC, size=12.5, leading=18, spaceBefore=4, spaceAfter=3),
            "center": style("center", alignment=1),
            "big": style("big", size=15, leading=20),
        })
    return S


def esc(s):
    return escape(s)


def red(s):
    return '<font color="%s">%s</font>' % (RED_HEX, s)


def P(text, st="body"):
    return Paragraph(text, styles()[st])


class Doc(BaseDocTemplate):
    """縦向き（portrait）と横向き（landscape）のページを混ぜられる文書。"""

    def __init__(self, path, title, footer):
        super().__init__(path, pagesize=A4, title=title, author="中学受験 国語ドリル",
                         leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN + 4 * mm)
        self.footer = footer
        pw, ph = A4
        portrait = Frame(MARGIN, MARGIN + 4 * mm, pw - 2 * MARGIN, ph - 2 * MARGIN - 4 * mm,
                         id="p", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        lw, lh = landscape(A4)
        land = Frame(0, 0, lw, lh, id="l", leftPadding=0, rightPadding=0,
                     topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate("portrait", [portrait], onPage=self._foot, pagesize=A4),
            PageTemplate("landscape", [land], onPage=self._foot, pagesize=landscape(A4)),
        ])

    def _foot(self, c, doc):
        c.saveState()
        c.setFont(GOTHIC, 7.5)
        c.setFillColor(MID)
        w = c._pagesize[0]
        c.drawString(MARGIN, 8 * mm, self.footer)
        c.drawRightString(w - MARGIN, 8 * mm, "%d" % doc.page)
        c.restoreState()


def header_block(title, subtitle="", score=None, width=None):
    """テストの見出し：タイトル・日付・名前・得点欄。"""
    st = styles()
    width = width or (A4[0] - 2 * MARGIN)
    left = [Paragraph(esc(title), st["h1"])]
    if subtitle:
        left.append(Paragraph(esc(subtitle), st["gothsmall"]))
    rows = [[Paragraph("　月　日", st["goth"]), Paragraph("名前", st["goth"]), ""]]
    if score:
        rows.append([Paragraph("得点", st["goth"]), Paragraph("　　　　／%d" % score, st["goth"]), ""])
    right = Table(rows, colWidths=[22 * mm, 14 * mm, 38 * mm], rowHeights=[9 * mm] * len(rows))
    right.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ] + ([("SPAN", (1, 1), (2, 1))] if score else [])))
    t = Table([[left, right]], colWidths=[width - 76 * mm, 76 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.6, black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    return t


def boxed(flowables, width, bg=LIGHT, pad=6):
    t = Table([[flowables]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, MID),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
    ]))
    return t


class CanvasPage(Flowable):
    """横向きページ全体を、関数 draw(canvas, width, height) で自由に描く。"""

    def __init__(self, draw):
        super().__init__()
        self._draw = draw

    def wrap(self, aw, ah):
        self._size = (aw, ah)
        return aw, ah

    def draw(self):
        self._draw(self.canv, *self._size)
