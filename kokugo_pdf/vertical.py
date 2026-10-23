"""縦書き本文のレイアウトと描画。

本文は段落（文字列）のリストで、次のタグで範囲を指定できる。
  <u1>…</u1>   傍線部①（数字が設問番号）
  <e1a>…</e1a> 設問①の根拠a（解答・解説で行番号を示し、網かけする）
タグは入れ子にしてよい。
"""
import re

from reportlab.lib.colors import Color, black

from .fonts import MINCHO, GOTHIC

CIRCLED = "⓪①②③④⑤⑥⑦⑧⑨⑩"

# 縦書きで90度回転させる文字
ROTATE = set("ー－―─…‥「」『』（）〈〉《》【】〔〕～〜＝")
# 縦書きで右上に寄せる句読点
PUNCT = set("、。，．")
# 縦書きで右上に少し寄せる小書き文字
SMALL = set("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")
# 行頭に来てはいけない文字（前の行にぶら下げる）
HANG = set("、。，．」』）〉》】")
# 行末に来てはいけない文字（次の行へ送る）
NO_END = set("「『（〈《【〔")

_TAG = re.compile(r"<(/?)([ue]\w+)>")


def parse(text):
    """タグ付き文字列を [(文字, frozenset(タグ))] にする。"""
    out, active, pos = [], [], 0
    for m in _TAG.finditer(text):
        for ch in text[pos:m.start()]:
            out.append((ch, frozenset(active)))
        closing, name = m.group(1), m.group(2)
        if closing:
            active.remove(name)
        else:
            active.append(name)
        pos = m.end()
    for ch in text[pos:]:
        out.append((ch, frozenset(active)))
    if active:
        raise ValueError("閉じていないタグ: %s" % active)
    return out


def layout(paragraphs, cpl):
    """段落を1行 cpl 字の行に分ける。戻り値は行（[(文字, タグ)]）のリスト。"""
    lines = []
    for para in paragraphs:
        chars = parse(para)
        if chars and chars[0][0] not in "「『（　":
            chars.insert(0, ("　", frozenset()))
        line = []
        for ch, tags in chars:
            if len(line) >= cpl:
                if ch in HANG and len(line) < cpl + 2:
                    line.append((ch, tags))
                    continue
                lines.append(line)
                line = []
            if len(line) == cpl - 1 and ch in NO_END:
                lines.append(line)
                line = []
            line.append((ch, tags))
        if line:
            lines.append(line)
    return lines


def tag_ranges(lines):
    """タグ名 -> (最初の行番号, 最後の行番号, その範囲の文字列)。行番号は1始まり。"""
    ranges = {}
    for i, line in enumerate(lines, 1):
        for ch, tags in line:
            for t in tags:
                first, last, text = ranges.get(t, (i, i, ""))
                ranges[t] = (first, i, text + ch)
    return ranges


def _draw_char(c, ch, xc, ycell, size):
    """ycell はマスの上端。xc は列の中心。"""
    em = size
    if ch == "　":
        return
    if ch in ROTATE:
        c.saveState()
        c.translate(xc, ycell - em / 2)
        c.rotate(-90)
        c.drawString(-em / 2, -0.38 * em, ch)
        c.restoreState()
        return
    x = xc - em / 2
    y = ycell - em + 0.12 * em
    if ch in PUNCT:
        x += 0.58 * em
        y += 0.62 * em
    elif ch in SMALL:
        x += 0.1 * em
        y += 0.1 * em
    c.drawString(x, y, ch)


SHADE = Color(0.82, 0.82, 0.82)


def draw_page(c, lines, first_no, x_right, y_top, size, pitch,
              underline=True, evidence=(), ranges_to_mark=()):
    """縦書き本文を1ページ分描く。

    lines        このページに載せる行
    first_no     最初の行の行番号
    x_right      最初の列（右端）の中心x
    y_top        1字目のマス上端y
    evidence     網かけする根拠タグの集合
    ranges_to_mark  [(設問番号, 開始行, 終了行)] 本文下に「前後10行」の範囲を示す
    """
    em = size
    max_len = max((len(l) for l in lines), default=0)

    # 根拠の網かけ（文字より先に描く）
    if evidence:
        c.setFillColor(SHADE)
        for li, line in enumerate(lines):
            xc = x_right - li * pitch
            for ci, (ch, tags) in enumerate(line):
                if tags & evidence:
                    c.rect(xc - em * 0.55, y_top - (ci + 1) * em, em * 1.1, em,
                           stroke=0, fill=1)
        c.setFillColor(black)

    c.setFont(MINCHO, size)
    for li, line in enumerate(lines):
        xc = x_right - li * pitch
        for ci, (ch, _tags) in enumerate(line):
            _draw_char(c, ch, xc, y_top - ci * em, size)

    # 行番号（5行ごと）
    c.setFont(GOTHIC, 6.5)
    for li in range(len(lines)):
        no = first_no + li
        if no % 5 == 0:
            c.drawCentredString(x_right - li * pitch, y_top + 4, str(no))

    # 傍線・根拠の印
    seen_u, seen_e = set(), set()
    for li, line in enumerate(lines):
        xc = x_right - li * pitch
        spans = {}
        for ci, (ch, tags) in enumerate(line):
            for t in tags:
                if (t.startswith("u") and underline) or t in evidence:
                    s, e = spans.get(t, (ci, ci))
                    spans[t] = (s, ci)
        for t, (s, e) in spans.items():
            ya, yb = y_top - s * em, y_top - (e + 1) * em
            if t.startswith("u"):
                xl = xc + em * 0.62
                c.setLineWidth(0.9)
                c.line(xl, ya, xl, yb)
                if t not in seen_u:
                    seen_u.add(t)
                    c.setFont(MINCHO, 7.5)
                    c.drawString(xl + 0.8, ya - 7.5, CIRCLED[int(t[1:])])
            else:
                xl = xc - em * 0.62
                c.setLineWidth(1.6)
                c.line(xl, ya, xl, yb)
                if t not in seen_e:
                    seen_e.add(t)
                    c.setFont(GOTHIC, 6)
                    q = int(re.match(r"e(\d+)", t).group(1))
                    c.drawRightString(xl - 0.8, ya - 6.5, CIRCLED[q])
    c.setLineWidth(1)

    # 「前後10行」の範囲を本文の下に示す
    last_no = first_no + len(lines) - 1
    y = y_top - (max_len + 0.6) * em - 6
    for q, s, e in ranges_to_mark:
        if e < first_no or s > last_no:
            continue
        a, b = max(s, first_no), min(e, last_no)
        xa = x_right - (a - first_no) * pitch + pitch * 0.45
        xb = x_right - (b - first_no) * pitch - pitch * 0.45
        c.setLineWidth(0.8)
        c.line(xb, y, xa, y)
        if a == s:
            c.line(xa, y, xa, y + 4)
        if b == e:
            c.line(xb, y, xb, y + 4)
        c.setFont(GOTHIC, 7)
        label = "%sの根拠をさがす範囲（%d〜%d行目）" % (CIRCLED[q], s, e)
        if a != s:
            label = "（%sの範囲のつづき）" % CIRCLED[q]
        # 読む向き（右→左）に合わせ、範囲の右端にそろえて線の下に書く
        c.drawRightString(xa, y - 9, label)
        y -= 20
    c.setLineWidth(1)
