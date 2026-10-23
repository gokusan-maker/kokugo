"""1回分の授業プリント（90分）。

前半が生徒用（表紙・漢字テスト・ことわざ／慣用句テスト・解き方ガイド・長文・ワークシート）、
後半が先生用の解答（切りはなして使う）。
"""
from reportlab.lib.units import mm

from data.passages import PASSAGES
from . import anki_pdf, chobun_pdf
from .fonts import GOTHIC
from .vlayout import RED, Book, Flow, Para, R, draw_text

FOOT = "中学受験 国語 授業プリント"
LESSON_MIN = 90

# (内容, 分)
PLAN = [
    ("漢字の書き取りテスト（二十問）", 10),
    ("ことわざ・慣用句テスト（十五問）", 10),
    ("１・２の答え合わせ、まちがえた問題の直し", 5),
    ("消去法の解き方ガイドを読む", 5),
    ("長文を読む（傍線部に注意しながら）", 15),
    ("問一〜問三　消去法ワークシート", 30),
    ("長文の答え合わせ・解説", 15),
]


def lesson_items(n, seed):
    kanji = anki_pdf.make_sets("kanji_kaki", n, 20, seed)[n - 1]
    goku = (anki_pdf.make_sets("kotowaza", n, 8, seed)[n - 1]
            + anki_pdf.make_sets("kanyoku", n, 7, seed)[n - 1])
    return kanji, goku


def score_strip(flow, label, full):
    def draw(c, x0, x1, top, bottom):
        draw_text(c, [R(label)], (x0 + x1) / 2 + 2, top - 2, flow.H - 50 * mm, font=GOTHIC, size=10)
        c.setLineWidth(0.9)
        c.rect(x0 + 3, bottom, x1 - x0 - 6, 45 * mm)
        draw_text(c, [R("／%d" % full)], (x0 + x1) / 2, bottom + 16 * mm, 15 * mm, font=GOTHIC, size=10)
    flow.fixed(15 * mm, draw)


def cover(book, n, p):
    flow = Flow(book, header=("第%d回　国語演習　授業プリント" % n,
                              "中学受験 国語　%d分　長文　%s「%s」" % (LESSON_MIN, p["kind"], p["title"])))
    flow.box([
        Para([R("今日のめあて")], font=GOTHIC, size=12, after=3),
        Para([R("一　漢字・ことわざ・慣用句を、書けるところまで確実に覚える。")], size=10.5, hang=2, after=2),
        Para([R("二　傍線部の前後十行から根拠をさがし、消去法で選択肢を選べるようになる。")], size=10.5, hang=2, after=0),
    ])
    flow.space(4)
    flow.para(Para([R("授業の流れ")], font=GOTHIC, size=12, after=4))
    for i, (what, minutes) in enumerate(PLAN, 1):
        flow.para(Para([R("%d　" % i, font=GOTHIC), R(what), R("……%d分" % minutes, font=GOTHIC, size=9.5)],
                       size=10.5, hang=2, after=3))
    flow.rule(gap=6)
    flow.para(Para([R("今日の得点")], font=GOTHIC, size=12, after=4))
    score_strip(flow, "漢字の書き取り", 20)
    score_strip(flow, "ことわざ・慣用句", 15)
    score_strip(flow, "長文（問一〜問三）", 3)
    flow.rule(gap=6)
    flow.box([
        Para([R("ふり返り")], font=GOTHIC, size=12, after=3),
        Para([R("今日わかったこと・次に気をつけること\n\n\n\n\n")], size=10.5, after=0),
        Para([R("よくひっかかった×の種類（Ａ〜Ｆ）\n\n")], size=10.5, after=0),
    ])


def answer_divider(book, n):
    flow = Flow(book, header=("第%d回　解答・解説（先生用）" % n,
                              "ここから後ろは切りはなして、答え合わせのときに使ってください。"))
    for line in ("漢字の書き取りテスト　解答", "ことわざ・慣用句テスト　解答",
                 "長文　解答・解説（選択肢ごとの×の部分・×の種類・根拠の行）",
                 "長文　解答用本文（根拠に網かけ・前後十行の範囲つき）"):
        flow.para(Para([R("■　", color=RED), R(line)], size=11, after=6))


def build_lesson(path, n=1, seed="1", answers=True):
    """第n回の授業プリント。answers=False なら生徒用のページだけにする。"""
    p = PASSAGES[(n - 1) % len(PASSAGES)]
    kanji, goku = lesson_items(n, seed)
    _, kname, kinst, _, kbox, ksize = anki_pdf.CAT["kanji_kaki"]
    _, _, ginst, _, gbox, gsize = anki_pdf.CAT["kotowaza"]
    lines, ranges, qs = chobun_pdf.analyze(p)
    book = Book(path, "第%d回 国語演習 授業プリント" % n, "%s ― 第%d回" % (FOOT, n))

    # 生徒用
    cover(book, n, p)
    anki_pdf.test_page(book, "１　漢字の書き取りテスト", "第%d回　目標時間10分" % n, kanji, kinst, kbox, ksize, False)
    anki_pdf.test_page(book, "２　ことわざ・慣用句テスト", "第%d回　目標時間10分" % n, goku, ginst, gbox, gsize, False)
    chobun_pdf.guide(book)
    chobun_pdf.passage_pages(book, p, lines, "　本文")
    chobun_pdf.question_pages(book, p, qs)

    if not answers:
        book.save()
        return book.page

    # 先生用（解答）
    answer_divider(book, n)
    anki_pdf.test_page(book, "１　漢字の書き取りテスト　解答", "第%d回" % n, kanji, kinst, kbox, ksize, True)
    anki_pdf.test_page(book, "２　ことわざ・慣用句テスト　解答", "第%d回" % n, goku, ginst, gbox, gsize, True)
    chobun_pdf.answer_pages(book, p, qs, ranges)
    marks = [(it["q"]["no"],) + it["window"] for it in qs]
    shade = set(t for it in qs for t in it["evidence"])
    chobun_pdf.passage_pages(book, p, lines, "　解答用本文（網かけ＝根拠）", evidence=shade, marks=marks)
    book.save()
    return book.page
