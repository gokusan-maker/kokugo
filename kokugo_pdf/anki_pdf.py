"""暗記分野：赤シート対応の暗記シートと、確認テスト（解答つき）のPDF。"""
import random
import re

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import NextPageTemplate, PageBreak, Spacer, Table, TableStyle

from data import anki
from .common import (Paragraph, LIGHT, MARGIN, Doc, P, boxed, esc, header_block, red,
                     styles)

FOOT = "中学受験 国語 暗記ドリル"
WIDTH = A4[0] - 2 * MARGIN
_MARK = re.compile(r"〈(.+?)〉")


def underline(s):
    return _MARK.sub(lambda m: "<u>%s</u>" % m.group(1), esc(s))


def blank(s, size=4):
    return _MARK.sub("（" + "　" * size + "）", esc(s))


def fill_red(s):
    return _MARK.sub(lambda m: red(m.group(1)), esc(s))


def inner(s):
    return _MARK.search(s).group(1)


def small(s):
    return '<font size="8.5">%s</font>' % s


# 各問題は dict で次のキーを持つ
#   q  …… 問題（HTML）          qa …… 解答ページの問題（答えを朱色でうめたもの、なければ q）
#   a  …… 答え（解答欄に書く）  sq / sa …… 暗記シートの問題・答え（HTML、朱色が赤シートで消える部分）

def _kaki():
    return [dict(q=underline(s), a=a, sq=underline(s), sa=red(a)) for s, a in anki.KANJI_KAKI]


def _yomi():
    return [dict(q=underline(s), a=a, sq=underline(s), sa=red(a)) for s, a in anki.KANJI_YOMI]


def _yoji(rng):
    out = []
    for w, yomi, mean in anki.YOJI:
        pos = sorted(rng.sample(range(4), 2))
        shown = "".join("□" if i in pos else ch for i, ch in enumerate(w))
        filled = "".join(red(ch) if i in pos else ch for i, ch in enumerate(w))
        out.append(dict(
            q='<font size="14">%s</font><br/>%s' % (shown, small("意味：" + esc(mean))),
            qa='<font size="14">%s</font>%s<br/>%s' % (filled, small(red("（%s）" % yomi)), small("意味：" + esc(mean))),
            a=w, sq=esc(mean), sa=red("%s（%s）" % (w, yomi))))
    return out


def _proverb(rows, with_yomi=False):
    out = []
    for row in rows:
        text, mean = row[0], row[-1]
        yomi = small(red("（%s）" % row[1])) if with_yomi else ""
        out.append(dict(
            q="%s<br/>%s" % (blank(text), small("意味：" + esc(mean))),
            qa="%s%s<br/>%s" % (fill_red(text), yomi, small("意味：" + esc(mean))),
            a=inner(text), sq=fill_red(text) + yomi, sa=small(esc(mean))))
    return out


def _pair(rows, mark, rng):
    out = []
    for w, ans in rows:
        diff = [i for i, ch in enumerate(ans) if ch not in w]
        pos = rng.choice(diff or [0])
        shown = "".join("□" if i == pos else ch for i, ch in enumerate(ans))
        filled = "".join(red(ch) if i == pos else ch for i, ch in enumerate(ans))
        out.append(dict(
            q='<font size="13">%s　%s　%s</font>' % (w, mark, shown),
            qa='<font size="13">%s　%s　%s</font>' % (w, mark, filled),
            a=ans[pos], sq="%s　%s" % (w, mark), sa=red(ans)))
    return out


def _douon():
    return [[dict(q=underline(s), a=a, sq=underline(s), sa=red(a)) for s, a in rows]
            for _yomi, rows in anki.DOUON]


def _keigo():
    return [dict(q="%s　%s" % (underline(s), small("［%sに］" % kind)),
                 a=a, sq="%s　%s" % (underline(s), small("［%s］" % kind)), sa=red(a))
            for s, kind, a in anki.KEIGO]


CATEGORIES = [
    # key, 名前, 指示文, 列数, 解答欄の幅(mm)
    ("kanji_kaki", "漢字の書き取り", "――線部のカタカナを漢字に直しなさい。", 2, 24),
    ("kanji_yomi", "漢字の読み", "――線部の漢字の読みをひらがなで書きなさい。", 2, 30),
    ("yoji", "四字熟語", "意味を手がかりに、□に漢字を入れて四字熟語を完成させなさい。（答えは四字すべて書きなさい）", 1, 40),
    ("kotowaza", "ことわざ", "意味に合うように、（　）に入る言葉を答えなさい。", 1, 34),
    ("kanyoku", "慣用句", "意味に合うように、（　）に入る言葉を答えなさい。", 1, 30),
    ("koji", "故事成語", "意味に合うように、（　）に入る言葉を漢字で答えなさい。", 1, 34),
    ("taigigo", "対義語", "□に漢字一字を入れて、上の言葉と反対の意味の言葉（対義語）を完成させなさい。", 2, 18),
    ("ruigigo", "類義語", "□に漢字一字を入れて、上の言葉と似た意味の言葉（類義語）を完成させなさい。", 2, 18),
    ("douon", "同音異義語・同訓異字", "――線部のカタカナ・ひらがなを、文に合う漢字に直しなさい。（送りがなは書かなくてよい）", 2, 24),
    ("keigo", "敬語", "――線部を［　］の種類の敬語に直しなさい。", 1, 60),
]
CAT = {c[0]: c for c in CATEGORIES}


def items_for(key, seed):
    rng = random.Random("%s-%s" % (key, seed))
    if key == "kanji_kaki":
        return _kaki()
    if key == "kanji_yomi":
        return _yomi()
    if key == "yoji":
        return _yoji(rng)
    if key == "kotowaza":
        return _proverb(anki.KOTOWAZA)
    if key == "kanyoku":
        return _proverb(anki.KANYOKU)
    if key == "koji":
        return _proverb(anki.KOJI, with_yomi=True)
    if key == "taigigo":
        return _pair(anki.TAIGIGO, "⇔", rng)
    if key == "ruigigo":
        return _pair(anki.RUIGIGO, "＝", rng)
    if key == "douon":
        return [it for g in _douon() for it in g]
    if key == "keigo":
        return _keigo()
    raise KeyError(key)


def make_sets(key, n_sets, per_set, seed):
    """問題をシャッフルして per_set 問ずつ n_sets 回分に分ける（足りなければ一巡して使う）。"""
    rng = random.Random("%s-sets-%s" % (key, seed))
    if key == "douon":
        groups = _douon()
        rng.shuffle(groups)
        sets, gi = [], 0
        for _ in range(n_sets):
            cur = []
            while len(cur) + len(groups[gi % len(groups)]) <= per_set:
                cur.extend(groups[gi % len(groups)])
                gi += 1
            sets.append(cur)
        return sets
    items = items_for(key, seed)
    rng.shuffle(items)
    sets, k = [], 0
    for _ in range(n_sets):
        cur = []
        for _ in range(min(per_set, len(items))):
            cur.append(items[k % len(items)])
            k += 1
        sets.append(cur)
    return sets


# ---------------------------------------------------------------- 表の組み立て

def _answer_cell(it, show):
    if not show:
        return ""
    size = 12 if len(it["a"]) <= 8 else 9.5
    return Paragraph('<font size="%s">%s</font>' % (size, red(esc(it["a"]))), styles()["center"])


def _q_cell(it, show):
    return Paragraph(it.get("qa", it["q"]) if show else it["q"], styles()["q"])


def question_table(items, cols, box_w, show_answer=False, start_no=1, compact=False):
    box = box_w * mm
    no_w = 9 * mm
    if cols == 2:
        half = WIDTH / 2
        q_w = half - no_w - box - 3 * mm
        n = (len(items) + 1) // 2
        rows, style = [], [
            ("FONT", (0, 0), (-1, -1), "Gothic", 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, LIGHT),
        ]
        for r in range(n):
            row = []
            for c in range(2):
                i = r + c * n
                if i < len(items):
                    row += ["(%d)" % (start_no + i), _q_cell(items[i], show_answer),
                            _answer_cell(items[i], show_answer)]
                    style.append(("BOX", (c * 3 + 2, r), (c * 3 + 2, r), 0.8, black))
                else:
                    row += ["", "", ""]
            rows.append(row)
        widths = [no_w, q_w, box + 3 * mm, no_w, q_w, box]
        t = Table(rows, colWidths=widths, rowHeights=[(11 if compact else 13.5) * mm] * len(rows))
        t.setStyle(TableStyle(style))
        return t
    rows = [["(%d)" % (start_no + i), _q_cell(it, show_answer), _answer_cell(it, show_answer)]
            for i, it in enumerate(items)]
    t = Table(rows, colWidths=[no_w, WIDTH - no_w - box - 2 * mm, box + 2 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Gothic", 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (2, 0), (2, -1), 0.8, black),
        ("INNERGRID", (2, 0), (2, -1), 0.8, black),
        ("LINEBELOW", (0, 0), (1, -1), 0.3, LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 if compact else 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 if compact else 3),
    ]))
    return t


def sheet_table(items):
    """赤シート用の一覧（答えは朱色）。"""
    st = styles()
    rows = [[Paragraph("No.", st["gothsmall"]), Paragraph("問題", st["gothsmall"]),
             Paragraph("答え・意味", st["gothsmall"]), Paragraph("チェック", st["gothsmall"])]]
    for i, it in enumerate(items, 1):
        rows.append([str(i), Paragraph(it["sq"], st["body"]), Paragraph(it["sa"], st["body"]), "□ □ □"])
    t = Table(rows, colWidths=[10 * mm, WIDTH * 0.52, WIDTH * 0.48 - 30 * mm, 20 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Gothic", 8),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.4, black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
    ]))
    return t


# ---------------------------------------------------------------- 文書

def build_category(path, key, n_sets=3, per_set=None, seed=1):
    _, name, inst, cols, box_w = CAT[key]
    # 1ページに収まる問題数（2列なら20問、1列なら15問）
    per_set = per_set or (20 if cols == 2 else 15)
    doc = Doc(path, "%s ドリル" % name, "%s ― %s" % (FOOT, name))
    story = [NextPageTemplate("portrait")]

    story.append(header_block("%s　暗記シート" % name, "朱色の答えは赤シートでかくれます。言えたら□にチェック。"))
    story.append(Spacer(1, 4 * mm))
    story.append(sheet_table(items_for(key, seed)))

    for n, items in enumerate(make_sets(key, n_sets, per_set, seed), 1):
        story.append(PageBreak())
        story.append(header_block("%s　テスト第%d回" % (name, n), FOOT, score=len(items)))
        story.append(Spacer(1, 3 * mm))
        story.append(boxed([P(esc(inst), "goth")], WIDTH))
        story.append(Spacer(1, 3 * mm))
        story.append(question_table(items, cols, box_w))
        story.append(PageBreak())
        story.append(header_block("%s　テスト第%d回　解答" % (name, n), "まちがえた問題は暗記シートでもう一度確認しよう。"))
        story.append(Spacer(1, 3 * mm))
        story.append(question_table(items, cols, box_w, show_answer=True))
    doc.build(story)


def build_mix(path, n_sets=3, seed=1):
    """全分野から2問ずつの総合テスト。"""
    doc = Doc(path, "暗記分野 総合テスト", "%s ― 総合テスト" % FOOT)
    story = [NextPageTemplate("portrait")]
    for n in range(1, n_sets + 1):
        sections = []
        total = 0
        for key, name, inst, cols, box_w in CATEGORIES:
            items = make_sets(key, n_sets, 20, "%s-mix" % seed)[n - 1][:2]
            sections.append((name, inst, items, cols, box_w))
            total += len(items)
        for show in (False, True):
            story.append(header_block("暗記分野　総合テスト　第%d回%s" % (n, "　解答" if show else ""),
                                      "各分野から2問ずつ", score=None if show else total))
            no = 1
            for name, inst, items, cols, box_w in sections:
                story.append(Spacer(1, 1.5 * mm))
                story.append(P("<b>■ %s</b>　<font size=\"8\">%s</font>" % (name, esc(inst)), "goth"))
                story.append(question_table(items, cols, box_w, show_answer=show, start_no=no,
                                            compact=True))
                no += len(items)
            story.append(PageBreak())
    doc.build(story[:-1])
