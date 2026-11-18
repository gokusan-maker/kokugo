"""冬休みテキスト（全20日）。基礎・発展それぞれ。

1日分＝漢字テスト（書き取り10・読み10）＋語句テスト（15問）＋長文1題（消去法ワークシート）。
第20日は総まとめテスト：漢字・語句は第1〜19日に出た問題から出し直し、長文は5問。

冊子（book）には、表紙・使い方・学習計画表（チェック表）・20日分・まちがい直しノートを入れ、
解答編は別の冊子にする。1日分ずつのプリント（day）も作れる。

暗記問題は、授業プリントとは別の順番で全体（もとのデータ＋追加分）から選ぶ。
授業で出た問題がもう一度出ることもあるが、冬休みの復習としてそのままにしている。
"""
import random
from functools import lru_cache

from reportlab.lib.colors import black
from reportlab.lib.units import mm

from data.levels import LEVEL
from data.winter import WINTER
from . import anki_pdf, chobun_pdf, lesson_pdf
from .fonts import GOTHIC
from .vlayout import RED, Book, Flow, Para, R, draw_text

DAYS = 20
FOOT = "中学受験 国語 冬休みテキスト"
KANSUJI = "〇一二三四五六七八九十"

# 第20日（総まとめ）の語句テスト：いろいろな分野から3問ずつ
FINAL_GOKU = [("kotowaza", 3), ("kanyoku", 3), ("yoji", 3), ("koji", 3), ("keigo", 3)]


def info(level):
    """冬休みテキストのレベル情報。"""
    lv = LEVEL[level]
    return {"key": "fuyu" + level, "level": level, "name": "冬休み" + lv["name"], "lv": lv,
            "passages": WINTER[level]}


def _ja(n):
    """1〜20 を漢数字に（十一、二十 など）。"""
    if n < 10:
        return KANSUJI[n]
    t, o = divmod(n, 10)
    return ("" if t == 1 else KANSUJI[t]) + "十" + (KANSUJI[o] if o else "")


@lru_cache(maxsize=None)
def course(level, seed):
    """第1〜20日の (漢字の分野と問題, 語句の分野と問題) のタプル。"""
    d = LEVEL[level]["anki"]
    pools, cursor = {}, {}

    def take(key, k):
        if key not in pools:
            rng = random.Random("winter-%s-%s-%s" % (level, key, seed))
            pool = anki_pdf._douon(d) if key == "douon" else anki_pdf.items_for(key, "winter-%s" % seed, d)
            rng.shuffle(pool)
            pools[key], cursor[key] = pool, 0
        pool, out = pools[key], []
        if key == "douon":
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

    days, used = [], {}
    for n in range(1, DAYS):
        kanji = [(key, take(key, k)) for key, k in lesson_pdf.KANJI]
        goku = [(key, take(key, k)) for key, k in lesson_pdf.GOKU_ROTATION[(n - 1) % len(lesson_pdf.GOKU_ROTATION)]]
        for key, items in kanji + goku:
            used.setdefault(key, []).extend(items)
        days.append((tuple(kanji), tuple(goku)))

    # 総まとめ：第1〜19日に出た問題から選び直す
    rng = random.Random("winter-final-%s-%s" % (level, seed))
    kanji = [(key, rng.sample(used[key], k)) for key, k in lesson_pdf.KANJI]
    goku = [(key, rng.sample(used[key], k)) for key, k in FINAL_GOKU]
    days.append((tuple(kanji), tuple(goku)))
    return tuple(days)


def day_sections(level, n, seed="1"):
    kanji, goku = course(level, str(seed))[n - 1]
    return list(kanji), list(goku)


def is_final(n):
    return n == DAYS


def plan(n, goku, n_questions):
    """その日の学習の流れ (内容, 分)。"""
    if is_final(n):
        return [
            ("漢字　総まとめテスト（書き取り十問・読み十問）", 10),
            ("語句　総まとめテスト（五つの分野から三問ずつ）", 10),
            ("長文　総まとめテスト（%s）" % lesson_pdf.q_range(n_questions), 40),
            ("答え合わせ・まちがい直しノートに記入", 20),
        ]
    return [
        ("漢字テスト（書き取り十問・読み十問）", 10),
        ("語句テスト（%s）" % lesson_pdf.goku_name(goku), 10),
        ("答え合わせ、まちがえた問題の直し", 5),
        ("長文を読む（傍線部に注意しながら）", 10),
        ("%s　消去法ワークシート" % lesson_pdf.q_range(n_questions), 25),
        ("答え合わせ・まちがい直しノートに記入", 10),
    ]


def day_title(w, n):
    return "%s　第%d日%s" % (w["name"], n, "　総まとめテスト" if is_final(n) else "")


def goku_title(n, goku):
    if is_final(n):
        return "２　語句総まとめテスト"
    return "２　語句テスト（%s）" % lesson_pdf.goku_name(goku)


def cover(book, w, n, p, kanji, goku):
    minutes = sum(m for _, m in plan(n, goku, len(p["questions"])))
    flow = Flow(book, header=(day_title(w, n),
                              "中学受験 国語　%d分　長文　%s「%s」" % (minutes, p["kind"], p["title"])))
    if is_final(n):
        aims = ["一　冬休みに覚えた漢字・語句が、本当に身についているかたしかめる。",
                "二　長い問題でも、傍線部の前後十行から根拠をさがし、消去法で選びきる。"]
    else:
        aims = ["一　漢字と%sを、書けるところまで確実に覚える。" % lesson_pdf.goku_name(goku),
                "二　傍線部の前後十行から根拠をさがし、消去法で選択肢を選ぶ。"]
    flow.box([Para([R("今日のめあて")], font=GOTHIC, size=12, after=3)] +
             [Para([R(a)], size=10.5, hang=2, after=2) for a in aims])
    flow.space(4)
    flow.para(Para([R("学習の流れ")], font=GOTHIC, size=12, after=4))
    for i, (what, m) in enumerate(plan(n, goku, len(p["questions"])), 1):
        flow.para(Para([R("%d　" % i, font=GOTHIC), R(what), R("……%d分" % m, font=GOTHIC, size=9.5)],
                       size=10.5, hang=2, after=3))
    flow.rule(gap=6)
    flow.para(Para([R("今日の得点")], font=GOTHIC, size=12, after=4))
    lesson_pdf.score_strip(flow, "漢字", lesson_pdf.total(kanji))
    lesson_pdf.score_strip(flow, "語句", lesson_pdf.total(goku))
    lesson_pdf.score_strip(flow, "長文", len(p["questions"]))
    flow.rule(gap=6)
    flow.box([
        Para([R("ふり返り（学習計画表にも記録しよう）")], font=GOTHIC, size=12, after=3),
        Para([R("今日わかったこと・次に気をつけること\n\n\n\n")], size=10.5, after=0),
        Para([R("ひっかかった×の種類（Ａ〜Ｆ）\n\n")], size=10.5, after=0),
    ])


def student_pages(book, w, n, seed, guide=False):
    p = w["passages"][n - 1]
    kanji, goku = day_sections(w["level"], n, seed)
    lines, _ranges, qs = chobun_pdf.analyze(p)
    sub = "%s　目標時間10分" % day_title(w, n)
    cover(book, w, n, p, kanji, goku)
    anki_pdf.sections_page(book, "１　漢字%sテスト" % ("総まとめ" if is_final(n) else ""), sub, kanji, False)
    anki_pdf.sections_page(book, goku_title(n, goku), sub, goku, False)
    if guide:
        chobun_pdf.guide(book)
    chobun_pdf.passage_pages(book, p, lines, "　本文")
    chobun_pdf.question_pages(book, p, qs)


def answer_pages(book, w, n, seed):
    p = w["passages"][n - 1]
    kanji, goku = day_sections(w["level"], n, seed)
    lines, ranges, qs = chobun_pdf.analyze(p)
    sub = day_title(w, n)
    anki_pdf.sections_page(book, "１　漢字テスト　解答", sub, kanji, True)
    anki_pdf.sections_page(book, goku_title(n, goku) + "　解答", sub, goku, True)
    chobun_pdf.answer_pages(book, p, qs, ranges)
    marks = [(it["q"]["no"],) + it["window"] for it in qs]
    shade = set(t for it in qs for t in it["evidence"])
    chobun_pdf.passage_pages(book, p, lines, "　解答用本文（網かけ＝根拠）", evidence=shade, marks=marks)


def build_day(path, level, n, seed="1", answers=True):
    """1日分のプリント。answers=False なら生徒用だけ。"""
    w = info(level)
    book = Book(path, "%s 第%d日" % (w["name"], n), "%s ― %s 第%d日" % (FOOT, w["lv"]["name"], n))
    student_pages(book, w, n, seed, guide=(n == 1))
    if answers:
        flow = Flow(book, header=("%s　解答・解説（おうちの方・先生用）" % day_title(w, n),
                                  "ここから後ろは切りはなして、答え合わせのときに使ってください。"))
        flow.para(Para([R("■　", color=RED), R("漢字・語句テストの解答、長文の解答・解説、根拠に網かけした本文")],
                       size=11, after=6))
        answer_pages(book, w, n, seed)
    book.save()
    return book.page


# ---------------------------------------------------------------- 冊子の前後のページ

def title_page(book, w, answers=False):
    flow = Flow(book)
    flow.space(30 * mm)
    flow.para(Para([R("中学受験　国語")], font=GOTHIC, size=16, after=8))
    flow.para(Para([R("冬休みテキスト" + ("　解答編" if answers else ""))], font=GOTHIC, size=34, after=10))
    flow.para(Para([R("%sレベル　全%d日" % (w["lv"]["name"], DAYS))], font=GOTHIC, size=16, after=14))
    flow.para(Para([R("漢字・語句の毎日テスト／消去法で解く長文読解／総まとめテスト")], size=12, after=24))
    flow.para(Para([R("名前")], font=GOTHIC, size=14, after=0))
    flow.fixed(14 * mm, lambda c, x0, x1, top, bottom: c.line((x0 + x1) / 2, top - 22 * mm, (x0 + x1) / 2, top - 120 * mm))


def how_to(book, w):
    flow = Flow(book, header=("このテキストの使い方", "%s　全%d日" % (w["name"], DAYS)))
    rows = [
        ("毎日の学習", "一日分は約七十分。表紙の「学習の流れ」の順に進めよう。"
                       "時間をはかって、目標時間を守ること。"),
        ("漢字・語句テスト", "答えは解答編で確認し、まちがえた問題は、正しい答えを三回書いて覚え直そう。"),
        ("長文", "傍線部の前後十行から根拠をさがし、選択肢を区切って○×をつける「消去法」で答えを選ぼう。"
                 "やり方は第一日の「解き方ガイド」にある。"),
        ("学習計画表", "終わったら、学習計画表に日付と得点を書き、○をつけよう。おうちの方に確認のサインをもらおう。"),
        ("まちがい直しノート", "長文でまちがえた問題は、×の種類（Ａ〜Ｆ）と、本文の根拠を書きこもう。"
                               "同じ種類の×をくり返していないか、ときどき見直そう。"),
        ("第二十日", "総まとめテスト。冬休みに出た漢字・語句から出し直す。八割以上を目指そう。"),
    ]
    for head, body in rows:
        flow.para(Para([R("■%s" % head, font=GOTHIC)], size=12, after=2))
        flow.para(Para([R(body)], size=11, indent=1, after=8))
    flow.rule(gap=6)
    flow.box([Para([R("×の種類（長文の選択肢）")], font=GOTHIC, size=11, after=3)] +
             [Para([R("%s　%s" % (chobun_pdf.CODES[k], v), font=GOTHIC), R("　" + chobun_pdf.HINTS[k], size=9.5)],
                   size=10.5, hang=2, after=2)
              for k, v in chobun_pdf.MISTAKE_TYPES.items()])


def plan_table(book, w, seed):
    """学習計画表（チェック表）。1日＝1列。"""
    flow = Flow(book, header=("学習計画表・チェック表", "%s　終わったら日付と得点を書き、○をつけよう。" % w["name"]))
    labels = [("", 16), ("日付", 18), ("漢字", 20), ("語句", 20), ("長文", 20), ("できた", 16), ("おうちの方", 0)]

    def cell_tops(top, bottom):
        fixed = sum(h for _, h in labels if h) * mm
        hs = [(h * mm if h else (top - bottom - fixed)) for _, h in labels]
        ys, y = [], top
        for h in hs:
            ys.append((y, y - h))
            y -= h
        return ys

    def head(c, x0, x1, top, bottom):
        c.setLineWidth(0.8)
        c.rect(x0, bottom, x1 - x0, top - bottom)
        for (label, _), (y0, y1) in zip(labels, cell_tops(top, bottom)):
            c.line(x0, y1, x1, y1)
            draw_text(c, [R(label)], (x0 + x1) / 2, y0 - 2 * mm, y0 - y1, font=GOTHIC, size=8.5)
    flow.fixed(9 * mm, head)

    for n in range(1, DAYS + 1):
        p = w["passages"][n - 1]
        kanji, goku = day_sections(w["level"], n, seed)
        fulls = ["", "", "／%d" % lesson_pdf.total(kanji), "／%d" % lesson_pdf.total(goku),
                 "／%d" % len(p["questions"]), "", ""]

        def col(c, x0, x1, top, bottom, n=n, fulls=fulls):
            c.setLineWidth(0.8)
            c.rect(x0, bottom, x1 - x0, top - bottom)
            for i, ((y0, y1), full) in enumerate(zip(cell_tops(top, bottom), fulls)):
                c.line(x0, y1, x1, y1)
                xc = (x0 + x1) / 2
                if i == 0:
                    draw_text(c, [R("%s日" % _ja(n))], xc, y0 - 1.5 * mm, y0 - y1, font=GOTHIC,
                              size=8.5, color=RED if is_final(n) else black)
                elif i == 5:
                    c.circle(xc, (y0 + y1) / 2, 3.2 * mm)
                elif full:
                    draw_text(c, [R(full)], xc, y1 + 9 * mm, 9 * mm, font=GOTHIC, size=7.5)
        flow.fixed(10.4 * mm, col)


def mistake_notes(book, w, pages=4):
    """まちがい直しノート。1列＝1問。"""
    cells = [("日・問", 16), ("×の種類", 18), ("自分の答え→正答", 32), ("まちがえた理由", 0),
             ("正しい根拠（本文の何行目）", 0)]
    for pg in range(pages):
        flow = Flow(book, header=("まちがい直しノート", "長文でまちがえた問題を書きこもう。×の種類はＡ〜Ｆ（使い方のページ参照）。"))

        def head(c, x0, x1, top, bottom):
            free = (top - bottom - sum(h for _, h in cells) * mm) / 2
            y = top
            c.setLineWidth(0.8)
            c.rect(x0, bottom, x1 - x0, top - bottom)
            for label, h in cells:
                h = h * mm or free
                draw_text(c, [R(label)], (x0 + x1) / 2, y - 2 * mm, h, font=GOTHIC, size=8)
                y -= h
                c.line(x0, y, x1, y)
        flow.fixed(9 * mm, head)

        def col(c, x0, x1, top, bottom):
            free = (top - bottom - sum(h for _, h in cells) * mm) / 2
            y = top
            c.setLineWidth(0.6)
            c.rect(x0, bottom, x1 - x0, top - bottom)
            for _, h in cells:
                y -= h * mm or free
                c.line(x0, y, x1, y)
        while flow.room() >= 19 * mm:
            flow.fixed(19 * mm, col)


def build_book(path, level, seed="1", answers=False):
    """冊子。answers=False なら問題編（表紙・使い方・計画表・20日分・まちがい直しノート）、True なら解答編。"""
    w = info(level)
    book = Book(path, "%s テキスト%s" % (w["name"], "（解答編）" if answers else ""),
                "%s ― %s%s" % (FOOT, w["lv"]["name"], "　解答編" if answers else ""))
    title_page(book, w, answers)
    if answers:
        for n in range(1, DAYS + 1):
            flow = Flow(book, header=(day_title(w, n) + "　解答", None))
            flow.para(Para([R("■　", color=RED), R("漢字・語句テストの解答、長文の解答・解説、根拠に網かけした本文")],
                           size=11, after=6))
            answer_pages(book, w, n, seed)
    else:
        how_to(book, w)
        plan_table(book, w, seed)
        for n in range(1, DAYS + 1):
            student_pages(book, w, n, seed, guide=(n == 1))
        mistake_notes(book, w)
    book.save()
    return book.page
