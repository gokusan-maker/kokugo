"""1回分の授業プリント（90分）。全15回のコース。

前半が生徒用（表紙・漢字テスト・語句テスト・解き方ガイド・長文・ワークシート）、
後半が先生用の解答（切りはなして使う）。

各回の問題は course() でまとめて割りふる。分野ごとに問題をシャッフルして先頭から順に使うので、
問題が足りなくなるまでは、同じ問題が別の回にもう一度出ることはない。
"""
import random
from functools import lru_cache

from reportlab.lib.units import mm

from data.passages import PASSAGES
from . import anki_pdf, chobun_pdf
from .fonts import GOTHIC
from .vlayout import RED, Book, Flow, Para, R, draw_text

FOOT = "中学受験 国語 授業プリント"
LESSON_MIN = 90

# 漢字テスト（毎回）：書き取り10問＋読み10問
KANJI = [("kanji_kaki", 10), ("kanji_yomi", 10)]

# 語句テスト（15問）：回ごとに分野を入れかえる（6回で一めぐり）
GOKU_ROTATION = [
    [("kotowaza", 8), ("kanyoku", 7)],
    [("yoji", 15)],
    [("taigigo", 8), ("ruigigo", 7)],
    [("koji", 8), ("kotowaza", 7)],
    [("douon", 15)],
    [("keigo", 8), ("kanyoku", 7)],
]


@lru_cache(maxsize=None)
def course(seed, n_lessons):
    """第1回〜第n_lessons回の [(漢字の分野と問題), (語句の分野と問題)] を返す。"""
    pools, cursor = {}, {}

    def take(key, k):
        if key not in pools:
            rng = random.Random("%s-course-%s" % (key, seed))
            pool = anki_pdf._douon() if key == "douon" else anki_pdf.items_for(key, seed)
            rng.shuffle(pool)
            pools[key], cursor[key] = pool, 0
        pool, out = pools[key], []
        if key == "douon":
            # 同じ読みの組はまとめて出す
            while True:
                group = pool[cursor[key] % len(pool)]
                if out and len(out) + len(group) > k:
                    break
                out.extend(group)
                cursor[key] += 1
            return out
        for _ in range(k):
            out.append(pool[cursor[key] % len(pool)])
            cursor[key] += 1
        return out

    lessons = []
    for n in range(1, n_lessons + 1):
        kanji = [(key, take(key, k)) for key, k in KANJI]
        goku = [(key, take(key, k)) for key, k in GOKU_ROTATION[(n - 1) % len(GOKU_ROTATION)]]
        lessons.append((kanji, goku))
    return tuple(lessons)


def lesson_sections(n, seed):
    return course(str(seed), max(n, len(PASSAGES)))[n - 1]


def goku_name(goku):
    return "・".join(anki_pdf.CAT[key][1] for key, _ in goku)


def plan(goku):
    """授業の流れ (内容, 分)"""
    return [
        ("漢字テスト（書き取り十問・読み十問）", 10),
        ("語句テスト（%s）" % goku_name(goku), 10),
        ("１・２の答え合わせ、まちがえた問題の直し", 5),
        ("消去法の解き方ガイドを読む", 5),
        ("長文を読む（傍線部に注意しながら）", 15),
        ("問一〜問三　消去法ワークシート", 30),
        ("長文の答え合わせ・解説", 15),
    ]


def total(sections):
    return sum(len(items) for _, items in sections)


def score_strip(flow, label, full):
    def draw(c, x0, x1, top, bottom):
        draw_text(c, [R(label)], (x0 + x1) / 2 + 2, top - 2, flow.H - 50 * mm, font=GOTHIC, size=10)
        c.setLineWidth(0.9)
        c.rect(x0 + 3, bottom, x1 - x0 - 6, 45 * mm)
        draw_text(c, [R("／%d" % full)], (x0 + x1) / 2, bottom + 16 * mm, 15 * mm, font=GOTHIC, size=10)
    flow.fixed(15 * mm, draw)


def cover(book, n, p, kanji, goku):
    flow = Flow(book, header=("第%d回　国語演習　授業プリント" % n,
                              "中学受験 国語　%d分　長文　%s「%s」" % (LESSON_MIN, p["kind"], p["title"])))
    flow.box([
        Para([R("今日のめあて")], font=GOTHIC, size=12, after=3),
        Para([R("一　漢字と%sを、書けるところまで確実に覚える。" % goku_name(goku))], size=10.5, hang=2, after=2),
        Para([R("二　傍線部の前後十行から根拠をさがし、消去法で選択肢を選べるようになる。")], size=10.5, hang=2, after=0),
    ])
    flow.space(4)
    flow.para(Para([R("授業の流れ")], font=GOTHIC, size=12, after=4))
    for i, (what, minutes) in enumerate(plan(goku), 1):
        flow.para(Para([R("%d　" % i, font=GOTHIC), R(what), R("……%d分" % minutes, font=GOTHIC, size=9.5)],
                       size=10.5, hang=2, after=3))
    flow.rule(gap=6)
    flow.para(Para([R("今日の得点")], font=GOTHIC, size=12, after=4))
    score_strip(flow, "漢字テスト", total(kanji))
    score_strip(flow, "語句テスト", total(goku))
    score_strip(flow, "長文（問一〜問三）", len(p["questions"]))
    flow.rule(gap=6)
    flow.box([
        Para([R("ふり返り")], font=GOTHIC, size=12, after=3),
        Para([R("今日わかったこと・次に気をつけること\n\n\n\n\n")], size=10.5, after=0),
        Para([R("よくひっかかった×の種類（Ａ〜Ｆ）\n\n")], size=10.5, after=0),
    ])


def answer_divider(book, n):
    flow = Flow(book, header=("第%d回　解答・解説（先生用）" % n,
                              "ここから後ろは切りはなして、答え合わせのときに使ってください。"))
    for line in ("漢字テスト　解答", "語句テスト　解答",
                 "長文　解答・解説（選択肢ごとの×の部分・×の種類・根拠の行）",
                 "長文　解答用本文（根拠に網かけ・前後十行の範囲つき）"):
        flow.para(Para([R("■　", color=RED), R(line)], size=11, after=6))


def build_lesson(path, n=1, seed="1", answers=True):
    """第n回の授業プリント。answers=False なら生徒用のページだけにする。"""
    p = PASSAGES[(n - 1) % len(PASSAGES)]
    kanji, goku = lesson_sections(n, seed)
    lines, ranges, qs = chobun_pdf.analyze(p)
    book = Book(path, "第%d回 国語演習 授業プリント" % n, "%s ― 第%d回" % (FOOT, n))
    ktitle, gtitle = "１　漢字テスト", "２　語句テスト（%s）" % goku_name(goku)

    # 生徒用
    cover(book, n, p, kanji, goku)
    anki_pdf.sections_page(book, ktitle, "第%d回　目標時間10分" % n, kanji, False)
    anki_pdf.sections_page(book, gtitle, "第%d回　目標時間10分" % n, goku, False)
    chobun_pdf.guide(book)
    chobun_pdf.passage_pages(book, p, lines, "　本文")
    chobun_pdf.question_pages(book, p, qs)

    if not answers:
        book.save()
        return book.page

    # 先生用（解答）
    answer_divider(book, n)
    anki_pdf.sections_page(book, ktitle + "　解答", "第%d回" % n, kanji, True)
    anki_pdf.sections_page(book, gtitle + "　解答", "第%d回" % n, goku, True)
    chobun_pdf.answer_pages(book, p, qs, ranges)
    marks = [(it["q"]["no"],) + it["window"] for it in qs]
    shade = set(t for it in qs for t in it["evidence"])
    chobun_pdf.passage_pages(book, p, lines, "　解答用本文（網かけ＝根拠）", evidence=shade, marks=marks)
    book.save()
    return book.page
