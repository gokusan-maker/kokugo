"""長文読解：傍線部の前後10行から根拠をさがし、消去法で正解を選ぶ演習PDF。

構成（1題につき1ファイル）
  1. 消去法の解き方ガイド
  2. 本文（縦書き・行番号つき・傍線部）
  3. 設問＋消去法ワークシート（1問1ページ）
  4. 解答・解説（選択肢ごとに、どこが×か・×の種類・根拠の行）
  5. 解答用本文（根拠に網かけ、「前後10行」の範囲を表示）
"""
import re

from reportlab.lib.units import mm

from data.passages import MISTAKE_TYPES
from . import vertical
from .fonts import GOTHIC
from .vlayout import (MARGIN, MID, PAGE, RED, TOP, Book, Flow, Para, R, draw_column,
                      draw_text, layout, name_box)

FOOT = "中学受験 国語 長文読解 消去法トレーニング"
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


# ---------------------------------------------------------------- 本文ページ

def passage_pages(book, p, lines, label, evidence=(), marks=()):
    """本文を横向きページに縦書きで描く。右はしに題名、左はしに名前らん。"""
    W, H = PAGE
    x_right = W - MARGIN - 20 * mm
    y_top = H - TOP - 10
    left = MARGIN + 19 * mm
    per_page = int((x_right - left) // PITCH) + 1
    total = (len(lines) + per_page - 1) // per_page
    for k in range(total):
        c = book.new_page()
        x = W - MARGIN - 3 * mm
        x -= draw_text(c, [R("%s「%s」%s" % (p["kind"], p["title"], label))], x, H - TOP, H - 2 * TOP,
                       font=GOTHIC, size=14)
        draw_text(c, [R("（%d／%d）本文はこの教材のための書き下ろし。上の数字は行番号。" % (k + 1, total))],
                  x - 4, H - TOP, H - 2 * TOP, font=GOTHIC, size=7.5)
        c.setLineWidth(1.2)
        c.line(W - MARGIN - 18 * mm, H - TOP, W - MARGIN - 18 * mm, TOP)
        name_box(c)
        chunk = lines[k * per_page:(k + 1) * per_page]
        vertical.draw_page(c, chunk, k * per_page + 1, x_right - PITCH / 2, y_top, FONT_SIZE, PITCH,
                           evidence=evidence, ranges_to_mark=marks, x_min=left)


# ---------------------------------------------------------------- ガイド

HINTS = {
    "ない": "本文のどこにも書かれていないことがまざっている。",
    "逆": "本文と反対の内容になっている。（うれしい⇔くやしい　など）",
    "言いすぎ": "「必ず」「すべて」「どんなときも」「〜だけ」など、本文より強く言いきっている。",
    "人物": "その気持ちや行動をしたのは、別の人物である。",
    "理由": "書かれている内容は本文にあるが、理由やつながり方がちがう。",
    "時": "別の場面（前やあと）の気持ち・できごとを持ちこんでいる。",
}

STEPS = [
    ("ステップ１　範囲を決める",
     "傍線部が何行目にあるかを確認し、その前後十行を［　］で囲みます。"
     "答えの根拠（理由・気持ち・言いかえ）は、ほとんどがこの範囲の中にあります。"),
    ("ステップ２　根拠に線を引く",
     "設問が聞いていること（理由？　気持ち？　どういうこと？）に合う部分を、範囲の中からさがして線を引きます。"
     "「だから」「つまり」「〜からだ」などのつなぎ言葉や、人物の行動・せりふに注目しましょう。"),
    ("ステップ３　選択肢を区切る",
     "選択肢を「／」で二〜四つに区切ります。区切った一つずつを本文と照らし合わせ、"
     "合っていれば○、ちがえば×、本文に書いていなければ×をつけます。"),
    ("ステップ４　×を消して、残ったものが答え",
     "一か所でも×がある選択肢は答えになりません。×の種類（左の表）を書きこんでおくと、"
     "自分がよくひっかかるパターンがわかります。"),
]


def guide(book):
    flow = Flow(book, header=("消去法の解き方ガイド", "長文の選択問題は「根拠をさがす↓選択肢を区切る↓×を消す」"))
    for h, b in STEPS:
        flow.box([Para([R(h)], font=GOTHIC, size=12, after=2), Para([R(b)], size=10.5, after=0)])
    flow.space(6)
    flow.para(Para([R("■×の種類（ひっかけのパターン）")], font=GOTHIC, size=12, after=4))
    for k, name in MISTAKE_TYPES.items():
        flow.para(Para([R("%s　%s" % (CODES[k], name), font=GOTHIC), R("……" + HINTS[k], size=9.5)],
                       size=10.5, hang=2, after=4))
    flow.space(6)
    flow.para(Para([R("※正解の選択肢は、本文の言葉をそのまま使わず「言いかえ」ていることが多いです。"
                      "言葉が同じかどうかではなく、内容が同じかどうかで判断しましょう。")], size=9.5))


# ---------------------------------------------------------------- 設問ページ

def parts_runs(c, mark=False, size=11):
    """選択肢を「／」区切りにした R のリスト。mark=True なら解説用に○×をつける。"""
    out = []
    for i, part in enumerate(c["parts"]):
        if i:
            out.append(R("／", color=MID))
        if not mark:
            out += [R(part), R("□", size=size + 1)]
        elif c.get("ok") or i != c.get("bad"):
            out += [R(part), R("○", size=size - 2)]
        else:
            out += [R(part, color=RED, side="red"), R("×", color=RED)]
    return out


CELL_KIND = 16 * mm
CELL_LINE = 26 * mm


def choice_strip(flow, kana, choice):
    """ワークシートの選択肢1つ分。上に区切った選択肢、下に「種類」「根拠」のらん。"""
    cols = layout([R(kana + "　", font=GOTHIC)] + parts_runs(choice), flow.H - CELL_KIND - CELL_LINE - 4 * mm,
                  size=11, hang=2)
    w = sum(col.w for col in cols) + 4 * mm

    def draw(c, x0, x1, top, bottom):
        x = x1 - 2 * mm
        for col in cols:
            draw_column(c, col, x - col.w / 2, top)
            x -= col.w
        c.setLineWidth(0.6)
        c.rect(x0, bottom, w, top - bottom)
        y = bottom + CELL_LINE
        c.line(x0, y, x1, y)
        c.line(x0, y + CELL_KIND, x1, y + CELL_KIND)
        draw_text(c, [R("種類")], x1 - 2.5 * mm, y + CELL_KIND - 1.5, CELL_KIND, font=GOTHIC, size=6.5)
        draw_text(c, [R("根拠")], x1 - 2.5 * mm, y - 1.5, CELL_LINE, font=GOTHIC, size=6.5)
        draw_text(c, [R("行目")], (x0 + x1) / 2, bottom + 2 * 7 + 2, 20, font=GOTHIC, size=7)

    flow.fixed(w, draw)
    flow.space(2)


def answer_box(flow):
    def draw(c, x0, x1, top, bottom):
        c.setLineWidth(1)
        c.rect(x0, top - 55 * mm, x1 - x0, 55 * mm)
        c.line(x0, top - 10 * mm, x1, top - 10 * mm)
        draw_text(c, [R("答え")], (x0 + x1) / 2, top - 1.5 * mm, 10 * mm, font=GOTHIC, size=9)
    flow.fixed(13 * mm, draw)


def question_pages(book, p, qs):
    for item in qs:
        q, utext = item["q"], item["u"][2]
        no = q["no"]
        flow = Flow(book, header=("問%s　%s" % (KANSUJI[no], q["kind"]),
                                  "%s「%s」　消去法ワークシート" % (p["kind"], p["title"])))
        flow.para(Para([R(q["prompt"].format(u=utext))], size=11, after=4))
        for k, c in zip(KANA, q["choices"]):
            flow.para(Para([R(k + "　", font=GOTHIC), R("".join(c["parts"]))], size=11, hang=2, after=1))
        flow.space(6)
        circ = vertical.CIRCLED[no]
        flow.box([
            Para([R("ステップ１　", font=GOTHIC), R("傍線部%sは（　　　）行目にある。\n" % circ),
                  R("↓根拠をさがす範囲は（　　　）行目〜（　　　）行目。本文のこの範囲を［　］で囲もう。")],
                 size=10.5, hang=6, after=6),
            Para([R("ステップ２　", font=GOTHIC), R("範囲の中から根拠をさがして線を引こう。\n"),
                  R("根拠は（　　　）行目〜（　　　）行目。\n"), R("根拠を書きぬこう。\n\n\n\n")],
                 size=10.5, hang=6, after=0),
        ])
        flow.para(Para([R("ステップ３　", font=GOTHIC),
                        R("選択肢を区切って、□に○か×を書こう。×があれば種類（Ａ〜Ｆ、ガイド参照）と、本文の何行目とちがうかを書こう。")],
                       size=10.5, hang=6, after=4))
        for k, c in zip(KANA, q["choices"]):
            choice_strip(flow, k, c)
        flow.space(4)
        flow.para(Para([R("ステップ４　", font=GOTHIC), R("×のない選択肢が答え")], size=10.5, after=3))
        answer_box(flow)


# ---------------------------------------------------------------- 解答・解説

def answer_pages(book, p, qs, ranges):
    flow = Flow(book, header=("解答・解説", "%s「%s」" % (p["kind"], p["title"])))
    for n, item in enumerate(qs):
        q, (us, ue, _) = item["q"], item["u"]
        no = q["no"]
        lo, hi = item["window"]
        if n:
            flow.rule(gap=5, width=1.2)
        flow.need(70 * mm)
        flow.para(Para([R("問%s　答え　" % KANSUJI[no], font=GOTHIC, size=13),
                        R(item["answer"], size=18, color=RED)], after=4))
        ev = [R("根拠（解答用本文では網かけ）", font=GOTHIC)]
        for t in item["evidence"]:
            ev.append(R("\n・%s「%s」" % (line_label(*ranges[t][:2]), ranges[t][2])))
        flow.box([
            Para([R("範囲　", font=GOTHIC),
                  R("傍線部%sは%s↓前後十行の%d〜%d行目から根拠をさがす。"
                    % (vertical.CIRCLED[no], line_label(us, ue), lo, hi))], size=10, hang=3, after=4),
            Para(ev, size=10, hang=1, after=4),
            Para([R("ポイント　", font=GOTHIC), R(q["point"])], size=10, hang=5, after=0),
        ])
        for k, c in zip(KANA, q["choices"]):
            if c.get("ok"):
                verdict = [R("判定　", font=GOTHIC), R("○　正解", color=RED, font=GOTHIC)]
            else:
                verdict = [R("判定　", font=GOTHIC),
                           R("×　%s（%s）" % (CODES[c["type"]], MISTAKE_TYPES[c["type"]]), font=GOTHIC)]
            paras = [Para([R(k + "　", font=GOTHIC)] + parts_runs(c, mark=True, size=10), size=10, hang=2, after=1),
                     Para(verdict, size=9, hang=3, after=1),
                     Para([R("解説　", font=GOTHIC), R(fill_refs(c["why"], ranges))], size=9.5, hang=3, after=3)]
            flow.need(sum(pp.width(flow.H) for pp in paras))
            for pp in paras:
                flow.para(pp)
            flow.rule(gap=2, color=MID)


# ---------------------------------------------------------------- 文書

def build_passage(path, p):
    lines, ranges, qs = analyze(p)
    book = Book(path, "長文読解 %s「%s」" % (p["kind"], p["title"]), "%s ― %s「%s」" % (FOOT, p["kind"], p["title"]))
    guide(book)
    passage_pages(book, p, lines, "　本文")
    question_pages(book, p, qs)
    answer_pages(book, p, qs, ranges)
    marks = [(it["q"]["no"],) + it["window"] for it in qs]
    shade = set(t for it in qs for t in it["evidence"])
    passage_pages(book, p, lines, "　解答用本文（網かけ＝根拠）", evidence=shade, marks=marks)
    book.save()
    return qs
