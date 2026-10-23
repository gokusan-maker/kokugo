"""長文読解：傍線部の前後10行から根拠をさがし、消去法で正解を選ぶ演習PDF。

構成（1題につき1ファイル）
  1. 消去法の解き方ガイド
  2. 本文（縦書き・行番号つき・傍線部）
  3. 設問＋消去法ワークシート（1問1ページ）
  4. 解答・解説（選択肢ごとに、どこが×か・×の種類・根拠の行）
  5. 解答用本文（根拠に網かけ、「前後10行」の範囲を表示）
"""
import re

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (CondPageBreak, KeepTogether, NextPageTemplate,
                                PageBreak, Spacer, Table, TableStyle)

from data.passages import MISTAKE_TYPES
from . import vertical
from .common import (Paragraph, LIGHT, MARGIN, MID, CanvasPage, Doc, P, boxed, esc,
                     header_block, red, styles)
from .fonts import GOTHIC

FOOT = "中学受験 国語 長文読解 消去法トレーニング"
WIDTH = A4[0] - 2 * MARGIN
KANA = "アイウエオ"
KANSUJI = "〇一二三四五六七八九十"
CPL = 30          # 1行の字数
WINDOW = 10       # 傍線部の前後何行をさがすか
FONT_SIZE = 12
PITCH = FONT_SIZE * 1.9

CODES = {k: "ABCDEF"[i] for i, k in enumerate(MISTAKE_TYPES)}


class PassageError(ValueError):
    pass


# ---------------------------------------------------------------- 解析

def analyze(p):
    """行分け・タグ位置・各設問の範囲を計算し、根拠が範囲内にあるか検査する。"""
    lines = vertical.layout(p["paragraphs"], CPL)
    ranges = vertical.tag_ranges(lines)
    n = len(lines)
    qs = []
    for q in p["questions"]:
        no = q["no"]
        us, ue, utext = ranges["u%d" % no]
        lo, hi = max(1, us - WINDOW), min(n, ue + WINDOW)
        oks = [c for c in q["choices"] if c.get("ok")]
        if len(oks) != 1:
            raise PassageError("%s 問%d: 正解がちょうど1つではありません" % (p["id"], no))
        for c in q["choices"]:
            if not c.get("ok") and (c.get("bad") is None or c.get("type") not in MISTAKE_TYPES):
                raise PassageError("%s 問%d: ×の選択肢に bad/type がありません" % (p["id"], no))
        ev = sorted(set(re.findall(r"\{(?:L:)?(e\w+)\}", oks[0]["why"])))
        if not ev:
            raise PassageError("%s 問%d: 正解の解説に根拠タグがありません" % (p["id"], no))
        for t in ev:
            s, e, _ = ranges[t]
            if s < lo or e > hi:
                raise PassageError("%s 問%d: 根拠 %s（%d〜%d行目）が範囲 %d〜%d行目の外です"
                                   % (p["id"], no, t, s, e, lo, hi))
        qs.append(dict(q=q, u=(us, ue, utext), window=(lo, hi), evidence=ev,
                       answer=KANA[q["choices"].index(oks[0])]))
    return lines, ranges, qs


def line_label(s, e):
    return "%d行目" % s if s == e else "%d〜%d行目" % (s, e)


def fill_refs(text, ranges):
    def rep(m):
        lonly, tag = m.group(1), m.group(2)
        s, e, t = ranges[tag]
        if lonly:
            return line_label(s, e)
        return "%s「%s」" % (line_label(s, e), t)
    return re.sub(r"\{(L:)?(e\w+)\}", rep, text)


# ---------------------------------------------------------------- 縦書きページ

def passage_pages(p, lines, label, evidence=(), marks=()):
    """本文を横向きページに分けて描く Flowable のリスト。"""
    lw, lh = landscape(A4)
    x_right = lw - 20 * mm
    usable = x_right - 16 * mm
    per_page = int(usable // PITCH) + 1
    pages = []
    total = (len(lines) + per_page - 1) // per_page
    for k in range(total):
        chunk = lines[k * per_page:(k + 1) * per_page]
        first = k * per_page + 1

        def draw(c, w, h, chunk=chunk, first=first, k=k):
            c.setFont(GOTHIC, 11)
            c.drawString(16 * mm, h - 14 * mm, "%s「%s」%s" % (p["kind"], p["title"], label))
            c.setFont(GOTHIC, 8)
            c.drawRightString(w - 16 * mm, h - 14 * mm, "（%d／%d）　名前　　　　　　　　　　" % (k + 1, total))
            c.setStrokeColor(black)
            c.line(16 * mm, h - 17 * mm, w - 16 * mm, h - 17 * mm)
            vertical.draw_page(c, chunk, first, x_right, h - 27 * mm, FONT_SIZE, PITCH,
                               evidence=evidence, ranges_to_mark=marks)
            c.setFont(GOTHIC, 7)
            c.setFillColor(MID)
            c.drawString(16 * mm, 14 * mm, "※ 本文はこの教材のための書き下ろしです。上の数字は行番号です。")
            c.setFillColor(black)
        pages.append(CanvasPage(draw))
    return pages


# ---------------------------------------------------------------- ガイド

def guide():
    st = styles()
    out = [header_block("消去法の解き方ガイド", "長文の選択問題は「根拠をさがす → 選択肢を区切る → ×を消す」")]
    steps = [
        ("STEP 1　範囲を決める",
         "傍線部が何行目にあるかを確認し、<b>その前後10行</b>を［　］で囲みます。"
         "答えの根拠（理由・気持ち・言いかえ）は、ほとんどがこの範囲の中にあります。"),
        ("STEP 2　根拠に線を引く",
         "設問が聞いていること（理由？気持ち？どういうこと？）に合う部分を、範囲の中からさがして線を引きます。"
         "「だから」「つまり」「〜からだ」などのつなぎ言葉や、人物の行動・せりふに注目しましょう。"),
        ("STEP 3　選択肢を区切る",
         "選択肢を「／」で2〜4つに区切ります。区切った一つずつを本文と照らし合わせ、"
         "合っていれば○、ちがえば×、本文に書いていなければ×をつけます。"),
        ("STEP 4　×を消して、残ったものが答え",
         "一か所でも×がある選択肢は答えになりません。×の種類（下の表）を書きこんでおくと、"
         "自分がよくひっかかるパターンがわかります。"),
    ]
    for h, b in steps:
        out.append(Spacer(1, 3 * mm))
        out.append(boxed([P(h, "h2"), P(b)], WIDTH))
    out.append(Spacer(1, 5 * mm))
    out.append(P("■ ×の種類（ひっかけのパターン）", "h2"))
    hints = {
        "ない": "本文のどこにも書かれていないことがまざっている。",
        "逆": "本文と反対の内容になっている。（うれしい⇔くやしい など）",
        "言いすぎ": "「必ず」「すべて」「どんなときも」「〜だけ」など、本文より強く言いきっている。",
        "人物": "その気持ちや行動をしたのは、別の人物である。",
        "理由": "書かれている内容は本文にあるが、理由やつながり方がちがう。",
        "時": "別の場面（前やあと）の気持ち・できごとを持ちこんでいる。",
    }
    rows = [[P("記号", "gothsmall"), P("×の種類", "gothsmall"), P("見分け方", "gothsmall")]]
    for k, name in MISTAKE_TYPES.items():
        rows.append([P("<b>%s</b>" % CODES[k], "center"), P(esc(name), "goth"), P(esc(hints[k]), "small")])
    t = Table(rows, colWidths=[14 * mm, 60 * mm, WIDTH - 74 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, black),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    out.append(t)
    out.append(Spacer(1, 4 * mm))
    out.append(P("※ 正解の選択肢は、本文の言葉をそのまま使わず「言いかえ」ていることが多いです。"
                 "言葉が同じかどうかではなく、<b>内容が同じかどうか</b>で判断しましょう。", "small"))
    return out


# ---------------------------------------------------------------- 設問ページ

def parts_html(c, mark=False):
    """選択肢を「／」区切りで表示。mark=True なら解説用に○×をつける。"""
    segs = []
    for i, part in enumerate(c["parts"]):
        if not mark:
            segs.append("%s<font size=\"13\">□</font>" % esc(part))
        elif c.get("ok") or i != c.get("bad"):
            segs.append("%s<font size=\"9\">○</font>" % esc(part))
        else:
            segs.append("<u>%s</u>%s" % (red(esc(part)), red("<b>×</b>")))
    return "<font color=\"#888888\">／</font>".join(segs)


def question_pages(p, qs):
    st = styles()
    out = []
    for item in qs:
        q, (us, ue, utext) = item["q"], item["u"]
        no = q["no"]
        out.append(header_block("問%s　%s" % (KANSUJI[no], q["kind"]),
                                "%s「%s」　消去法ワークシート" % (p["kind"], p["title"])))
        out.append(Spacer(1, 3 * mm))
        out.append(P(esc(q["prompt"].format(u=utext)), "q"))
        out.append(Spacer(1, 2 * mm))
        for k, c in zip(KANA, q["choices"]):
            out.append(P("<b>%s</b>　%s" % (k, esc("".join(c["parts"]))), "body"))
        out.append(Spacer(1, 4 * mm))

        out.append(boxed([
            P("<b>STEP 1</b>　傍線部%sは（　　　）行目にある。<br/>"
              "　→ 根拠をさがす範囲は（　　　）行目〜（　　　）行目。本文のこの範囲を［　］で囲もう。"
              % vertical.CIRCLED[no], "body"),
            Spacer(1, 2 * mm),
            P("<b>STEP 2</b>　範囲の中から根拠をさがして線を引こう。　根拠は（　　　）行目〜（　　　）行目。", "body"),
            P("　根拠を書きぬこう：", "body"),
            Spacer(1, 8 * mm),
        ], WIDTH))
        out.append(Spacer(1, 3 * mm))
        out.append(P("<b>STEP 3</b>　選択肢を区切って、□に○か×を書こう。×があれば種類（A〜F）と、本文の何行目とちがうかを書こう。", "body"))
        rows = [[P("記号", "gothsmall"), P("区切った選択肢（□に○×）", "gothsmall"),
                 P("×の種類", "gothsmall"), P("根拠の行", "gothsmall")]]
        for k, c in zip(KANA, q["choices"]):
            rows.append([P("<b>%s</b>" % k, "center"), P(parts_html(c), "body"), "", P("行目", "small")])
        t = Table(rows, colWidths=[12 * mm, WIDTH - 52 * mm, 18 * mm, 22 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, black),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("VALIGN", (3, 1), (3, -1), "BOTTOM"),
            ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ]))
        out.append(t)
        out.append(Spacer(1, 4 * mm))
        ans = Table([[P("<b>STEP 4</b>　×のない選択肢が答え", "body"), P("答え", "goth"), ""]],
                    colWidths=[WIDTH - 50 * mm, 16 * mm, 34 * mm], rowHeights=[14 * mm])
        ans.setStyle(TableStyle([
            ("BOX", (1, 0), (2, 0), 1, black), ("LINEBEFORE", (2, 0), (2, 0), 0.5, black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        out.append(ans)
        out.append(Spacer(1, 3 * mm))
        out.append(P("×の種類　A：本文に書いていない　B：本文と反対　C：言いすぎ　D：人物のとりちがえ　E：理由・つながりがちがう　F：時・場面のずれ", "tiny"))
        out.append(PageBreak())
    return out


# ---------------------------------------------------------------- 解答・解説

def answer_pages(p, qs, ranges):
    out = [header_block("解答・解説", "%s「%s」" % (p["kind"], p["title"]))]
    for item in qs:
        q, (us, ue, utext) = item["q"], item["u"]
        no = q["no"]
        lo, hi = item["window"]
        block = [Spacer(1, 4 * mm),
                 P("問%s　答え　<font size=\"16\">%s</font>" % (KANSUJI[no], red(item["answer"])), "h2")]
        ev = "<br/>".join("・%s「%s」" % (line_label(*ranges[t][:2]), esc(ranges[t][2]))
                          for t in item["evidence"])
        block.append(boxed([
            P("<b>範囲</b>　傍線部%sは%s → 前後10行の <b>%d〜%d行目</b> から根拠をさがす。"
              % (vertical.CIRCLED[no], line_label(us, ue), lo, hi), "body"),
            P("<b>根拠</b>（解答用本文では網かけ）<br/>%s" % ev, "body"),
            P("<b>ポイント</b>　%s" % esc(q["point"]), "body"),
        ], WIDTH))
        block.append(Spacer(1, 2 * mm))
        rows = [[P("記号", "gothsmall"), P("選択肢（×の部分に下線）", "gothsmall"),
                 P("判定", "gothsmall"), P("解説", "gothsmall")]]
        for k, c in zip(KANA, q["choices"]):
            verdict = red("<b>○ 正解</b>") if c.get("ok") else "<b>×</b>　%s<br/><font size=\"7\">%s</font>" % (
                CODES[c["type"]], esc(MISTAKE_TYPES[c["type"]]))
            rows.append([P("<b>%s</b>" % k, "center"), P(parts_html(c, mark=True), "small"),
                         P(verdict, "small"), P(esc(fill_refs(c["why"], ranges)), "small")])
        t = Table(rows, colWidths=[10 * mm, 68 * mm, 26 * mm, WIDTH - 104 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, black),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        block.append(t)
        out.append(CondPageBreak(90 * mm))
        out.append(KeepTogether(block))
    return out


# ---------------------------------------------------------------- 文書

def build_passage(path, p):
    lines, ranges, qs = analyze(p)
    doc = Doc(path, "長文読解 %s「%s」" % (p["kind"], p["title"]), "%s ― %s「%s」" % (FOOT, p["kind"], p["title"]))
    story = [NextPageTemplate("portrait")]
    story += guide()
    story += [NextPageTemplate("landscape"), PageBreak()]
    pages = passage_pages(p, lines, "　本文")
    for i, pg in enumerate(pages):
        story.append(pg)
        story.append(NextPageTemplate("portrait" if i == len(pages) - 1 else "landscape"))
        story.append(PageBreak())
    story += question_pages(p, qs)
    story += answer_pages(p, qs, ranges)
    story += [NextPageTemplate("landscape"), PageBreak()]
    marks = [(it["q"]["no"],) + it["window"] for it in qs]
    shade = set(t for it in qs for t in it["evidence"])
    pages = passage_pages(p, lines, "　解答用本文（網かけ＝根拠）", evidence=shade, marks=marks)
    for i, pg in enumerate(pages):
        story.append(pg)
        if i < len(pages) - 1:
            story.append(PageBreak())
    doc.build(story)
    return qs
