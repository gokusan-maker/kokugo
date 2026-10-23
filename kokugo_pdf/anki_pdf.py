"""暗記分野：赤シート対応の暗記シートと、確認テスト（解答つき）のPDF。すべて縦書き。"""
import random
import re

from reportlab.lib.colors import black
from reportlab.lib.units import mm

from data import anki
from .fonts import GOTHIC
from .vlayout import (LIGHT, MID, RED, Book, Flow, Para, R, draw_column, draw_text,
                      layout)

FOOT = "中学受験 国語 暗記ドリル"
_MARK = re.compile(r"〈(.+?)〉")


def _split(s):
    """〈〉の外と中を順に返す。[(文字列, 〈〉の中か)]"""
    out, pos = [], 0
    for m in _MARK.finditer(s):
        if m.start() > pos:
            out.append((s[pos:m.start()], False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(s):
        out.append((s[pos:], False))
    return out


def underline(s):
    return [R(t, side="line") if m else R(t) for t, m in _split(s)]


def blank(s):
    return [R("（　　　）") if m else R(t) for t, m in _split(s)]


def fill_red(s):
    return [R(t, color=RED) if m else R(t) for t, m in _split(s)]


def inner(s):
    return _MARK.search(s).group(1)


def small(text, color=None):
    return R(text, size=8.5, color=color)


# 各問題は dict で次のキーを持つ（a 以外は R のリスト）
#   q   問題        qa   解答ページの問題（答えを朱色でうめたもの。なければ q）
#   a   答え（文字列）   mean 意味（問題の左に小さく出す。なければなし）
#   src 〈〉つきの元の文（アプリ用に書き出す。漢字の書き取りとことわざ・慣用句・故事成語のみ）
#   sq / sa  暗記シートの上段・下段（朱色が赤シートで消える部分）

def _kaki():
    return [dict(q=underline(s), a=a, src=s, sq=underline(s), sa=[R(a, color=RED)]) for s, a in anki.KANJI_KAKI]


def _yomi():
    return [dict(q=underline(s), a=a, sq=underline(s), sa=[R(a, color=RED)]) for s, a in anki.KANJI_YOMI]


def _yoji(rng):
    out = []
    for w, yomi, mean in anki.YOJI:
        pos = sorted(rng.sample(range(4), 2))
        out.append(dict(
            q=[R("□" if i in pos else ch) for i, ch in enumerate(w)],
            qa=[R(ch, color=RED if i in pos else None) for i, ch in enumerate(w)]
            + [small("（%s）" % yomi, RED)],
            a=w, mean=mean,
            sq=[small(mean)], sa=[R(w, color=RED), small("（%s）" % yomi, RED)]))
    return out


def _proverb(rows, with_yomi=False):
    out = []
    for row in rows:
        text, mean = row[0], row[-1]
        yomi = [small("（%s）" % row[1], RED)] if with_yomi else []
        out.append(dict(q=blank(text), qa=fill_red(text) + yomi, a=inner(text), mean=mean, src=text,
                        sq=fill_red(text) + yomi, sa=[small(mean)]))
    return out


def _pair(rows, mark, rng):
    out = []
    for w, ans in rows:
        diff = [i for i, ch in enumerate(ans) if ch not in w]
        pos = rng.choice(diff or [0])
        out.append(dict(
            q=[R("%s　%s　" % (w, mark))] + [R("□" if i == pos else ch) for i, ch in enumerate(ans)],
            qa=[R("%s　%s　" % (w, mark))] + [R(ch, color=RED if i == pos else None) for i, ch in enumerate(ans)],
            a=ans[pos], sq=[R("%s　%s" % (w, mark))], sa=[R(ans, color=RED)]))
    return out


def _douon():
    return [[dict(q=underline(s), a=a, sq=underline(s), sa=[R(a, color=RED)]) for s, a in rows]
            for _yomi, rows in anki.DOUON]


def _keigo():
    return [dict(q=underline(s) + [small("　［%sに］" % kind)], a=a,
                 sq=underline(s) + [small("　［%s］" % kind)], sa=[R(a, color=RED)])
            for s, kind, a in anki.KEIGO]


CATEGORIES = [
    # key, 名前, 指示文, 1回の問題数, 解答らんの高さ(mm), 問題の文字の大きさ
    ("kanji_kaki", "漢字の書き取り", "――線部のカタカナを漢字に直しなさい。", 20, 38, 12),
    ("kanji_yomi", "漢字の読み", "――線部の漢字の読みをひらがなで書きなさい。", 20, 50, 12),
    ("yoji", "四字熟語", "意味を手がかりに、□に漢字を入れて四字熟語を完成させなさい。（答えは四字すべて書きなさい）", 15, 46, 12),
    ("kotowaza", "ことわざ", "意味に合うように、（　）に入る言葉を答えなさい。", 15, 42, 12),
    ("kanyoku", "慣用句", "意味に合うように、（　）に入る言葉を答えなさい。", 15, 34, 12),
    ("koji", "故事成語", "意味に合うように、（　）に入る言葉を漢字で答えなさい。", 15, 40, 12),
    ("taigigo", "対義語", "□に漢字一字を入れて、上の言葉と反対の意味の言葉（対義語）を完成させなさい。", 20, 22, 13),
    ("ruigigo", "類義語", "□に漢字一字を入れて、上の言葉と似た意味の言葉（類義語）を完成させなさい。", 20, 22, 13),
    ("douon", "同音異義語・同訓異字", "――線部のカタカナ・ひらがなを、文に合う漢字に直しなさい。（送りがなは書かなくてよい）", 20, 30, 12),
    ("keigo", "敬語", "――線部を［　］の種類の敬語に直しなさい。", 15, 62, 12),
]
CAT = {c[0]: c for c in CATEGORIES}


def items_for(key, seed):
    rng = random.Random("%s-%s" % (key, seed))
    builders = {
        "kanji_kaki": _kaki,
        "kanji_yomi": _yomi,
        "yoji": lambda: _yoji(rng),
        "kotowaza": lambda: _proverb(anki.KOTOWAZA),
        "kanyoku": lambda: _proverb(anki.KANYOKU),
        "koji": lambda: _proverb(anki.KOJI, with_yomi=True),
        "taigigo": lambda: _pair(anki.TAIGIGO, "⇔", rng),
        "ruigigo": lambda: _pair(anki.RUIGIGO, "＝", rng),
        "douon": lambda: [it for g in _douon() for it in g],
        "keigo": _keigo,
    }
    return builders[key]()


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


# ---------------------------------------------------------------- 問題の短冊

NUM_H = 7 * mm


def question_strip(flow, it, no, box_h, size, show_answer):
    """1問分の短冊。上に番号、その下に問題文、下はしに解答らん。意味があれば左に小さく。"""
    box_h *= mm
    q_runs = it.get("qa", it["q"]) if show_answer else it["q"]
    q_cols = layout(q_runs, flow.H - NUM_H - box_h - 3 * mm, size=size)
    q_w = max(sum(col.w for col in q_cols), size * 1.9)
    m_cols = layout([R(it["mean"])], flow.H - NUM_H, size=8) if it.get("mean") else []
    m_w = sum(col.w for col in m_cols)
    w = q_w + m_w + 2 * mm

    def draw(c, x0, x1, top, bottom):
        x = x1 - 1 * mm
        draw_text(c, [R(str(no))], x - q_w / 2, top, NUM_H, font=GOTHIC, size=9)
        for col in q_cols:
            draw_column(c, col, x - col.w / 2, top - NUM_H)
            x -= col.w
        # 解答らん
        bx, bw = x1 - 1 * mm - q_w + 1.5, q_w - 3
        c.setLineWidth(0.9)
        c.rect(bx, bottom, bw, box_h)
        if show_answer:
            fs = min(13, (box_h - 6) / max(len(it["a"]), 1))
            th = fs * len(it["a"])
            draw_text(c, [R(it["a"], color=RED)], bx + bw / 2, bottom + box_h / 2 + th / 2, box_h, size=fs)
        x = x1 - 1 * mm - q_w
        for col in m_cols:
            draw_column(c, col, x - col.w / 2, top - NUM_H)
            x -= col.w
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.6)
        c.line(x0, top, x0, bottom)
        c.setStrokeColor(black)
        c.setLineWidth(1)

    flow.fixed(w, draw)


def test_page(book, title, sub, items, inst, box_h, size, show_answer):
    flow = Flow(book, header=(title, sub), score=None if show_answer else len(items))
    flow.box([Para([R(inst)], font=GOTHIC, size=10, after=0)], pad=5)
    for i, it in enumerate(items, 1):
        question_strip(flow, it, i, box_h, size, show_answer)


# ---------------------------------------------------------------- 暗記シート

def sheet_strip(flow, it, no):
    """暗記シートの1項目。上段に問題、下段に答え（朱色）、下はしにチェック欄。"""
    upper = flow.H * 0.5
    lower = flow.H - upper - NUM_H - 12 * mm
    s_cols = layout(it["sq"], upper - 3 * mm, size=11)
    a_cols = layout(it["sa"], lower, size=11)
    w = max(sum(c.w for c in s_cols), sum(c.w for c in a_cols), 11 * 1.7) + 3 * mm

    def draw(c, x0, x1, top, bottom):
        xc = (x0 + x1) / 2
        draw_text(c, [R(str(no))], xc, top, NUM_H, font=GOTHIC, size=8)
        for cols, y in ((s_cols, top - NUM_H), (a_cols, top - NUM_H - upper)):
            x = xc + sum(col.w for col in cols) / 2
            for col in cols:
                draw_column(c, col, x - col.w / 2, y)
                x -= col.w
        c.setStrokeColor(MID)
        c.setLineWidth(0.5)
        c.setDash(1.5, 1.5)
        y = top - NUM_H - upper + 2 * mm
        c.line(x0, y, x1, y)
        c.setDash()
        c.line(x0, top, x0, bottom)
        for k in range(3):
            c.rect(xc - 4, bottom + 2 + k * 11, 8, 8)
        c.setStrokeColor(black)
        c.setLineWidth(1)

    flow.fixed(w, draw)


# ---------------------------------------------------------------- 文書

def build_category(path, key, n_sets=3, per_set=None, seed=1):
    _, name, inst, default_n, box_h, size = CAT[key]
    book = Book(path, "%s ドリル" % name, "%s ― %s" % (FOOT, name))

    flow = Flow(book, header=("%s　暗記シート" % name, "朱色の答えは赤シートでかくれます。言えたら下の□にチェック。"))
    for i, it in enumerate(items_for(key, seed), 1):
        sheet_strip(flow, it, i)

    for n, items in enumerate(make_sets(key, n_sets, per_set or default_n, seed), 1):
        test_page(book, "%s　テスト第%d回" % (name, n), FOOT, items, inst, box_h, size, False)
        test_page(book, "%s　テスト第%d回　解答" % (name, n), "まちがえた問題は暗記シートでもう一度確認しよう。",
                  items, inst, box_h, size, True)
    book.save()


def build_mix(path, n_sets=3, seed=1):
    """全分野から2問ずつの総合テスト。"""
    book = Book(path, "暗記分野 総合テスト", "%s ― 総合テスト" % FOOT)
    for n in range(1, n_sets + 1):
        sections = []
        for key, name, inst, _n, box_h, size in CATEGORIES:
            items = make_sets(key, n_sets, 20, "%s-mix" % seed)[n - 1][:2]
            sections.append((name, inst, items, box_h, size))
        total = sum(len(s[2]) for s in sections)
        for show in (False, True):
            flow = Flow(book, header=("暗記分野　総合テスト　第%d回%s" % (n, "　解答" if show else ""),
                                      "各分野から2問ずつ"), score=None if show else total)
            no = 1
            for name, inst, items, box_h, size in sections:
                flow.para(Para([R("■%s　" % name, size=10), R(inst, size=8)], font=GOTHIC, after=2))
                for it in items:
                    question_strip(flow, it, no, box_h, min(size, 12), show)
                    no += 1
                flow.rule(gap=2)
    book.save()
