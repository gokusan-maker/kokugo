"""学習アプリ（web/）用に、授業プリントと同じ問題を data.js に書き出し、PDFを web/pdf/ に置く。"""
import json
import os
import re
import shutil

from data.levels import LEVELS
from data.passages import MISTAKE_TYPES
from . import anki_pdf, chobun_pdf, lesson_pdf, vertical


def _segments(line):
    """1行を、タグが同じ文字のまとまりに分ける。[{"t": 文字列, "tags": [...]}]"""
    segs = []
    for ch, tags in line:
        tags = sorted(tags)
        if segs and segs[-1]["tags"] == tags:
            segs[-1]["t"] += ch
        else:
            segs.append({"t": ch, "tags": tags})
    return segs


def _passage(p):
    lines, ranges, qs = chobun_pdf.analyze(p)
    questions = []
    for it in qs:
        q = it["q"]
        us, ue, utext = it["u"]
        questions.append({
            "no": q["no"],
            "kanji": chobun_pdf.KANSUJI[q["no"]],
            "kind": q["kind"],
            "prompt": q["prompt"].format(u=utext),
            "point": q["point"],
            "u": [us, ue],
            "window": list(it["window"]),
            "answer": it["answer"],
            "evidence": [{"tag": t, "s": ranges[t][0], "e": ranges[t][1], "text": ranges[t][2]}
                         for t in it["evidence"]],
            "choices": [{
                "kana": chobun_pdf.KANA[i],
                "parts": c["parts"],
                "ok": bool(c.get("ok")),
                "bad": c.get("bad"),
                "type": chobun_pdf.CODES[c["type"]] if c.get("type") else None,
                "why": chobun_pdf.fill_refs(c["why"], ranges),
            } for i, c in enumerate(q["choices"])],
        })
    return {"id": p["id"], "kind": p["kind"], "title": p["title"], "about": p["about"],
            "lines": [_segments(l) for l in lines], "questions": questions}


def _runs(runs):
    """R のリストを [{"t": 文字列, "u": 傍線か, "s": 小さい字か}] にする。"""
    segs = []
    for r in runs:
        seg = {"t": r.text, "u": r.side == "line", "s": bool(r.size and r.size < 10)}
        if segs and segs[-1]["u"] == seg["u"] and segs[-1]["s"] == seg["s"]:
            segs[-1]["t"] += seg["t"]
        else:
            segs.append(seg)
    return segs


def _accept(a):
    """正解として認める書き方。「いらっしゃる（おいでになる・お見えになる）」なら3つ。"""
    alts = [re.sub(r"（.*?）", "", a)]
    for inner in re.findall(r"（(.*?)）", a):
        alts += inner.split("・")
    return [x for x in alts if x]


def _test(title, sections):
    return {
        "title": title,
        "sections": [{
            "name": anki_pdf.CAT[key][1],
            "inst": anki_pdf.CAT[key][2],
            "items": [{"q": _runs(it["q"]), "mean": it.get("mean"), "a": it["a"], "accept": _accept(it["a"])}
                      for it in items],
        } for key, items in sections],
    }


def _lesson(lv, n, seed):
    p = lv["passages"][(n - 1) % len(lv["passages"])]
    kanji, goku = lesson_pdf.lesson_sections(n, seed, lv["key"])
    pdf = "pdf/%s/lesson%02d_%%s.pdf" % (lv["key"], n)
    return {
        "no": n,
        "plan": [{"what": w, "min": m} for w, m in lesson_pdf.plan(goku)],
        "kanji": _test("漢字テスト", kanji),
        "goku": _test("語句テスト（%s）" % lesson_pdf.goku_name(goku), goku),
        "passage": _passage(p),
        "pdf": {"student": pdf % "student", "full": pdf % "full"},
    }


def export(web_dir, seed):
    """全レベル・全回のデータを data.js に、授業プリントを pdf/<レベル>/ に書き出す。"""
    data = {
        "types": [{"code": chobun_pdf.CODES[k], "name": v, "hint": chobun_pdf.HINTS[k]}
                  for k, v in MISTAKE_TYPES.items()],
        "steps": [{"title": h, "body": b} for h, b in chobun_pdf.STEPS],
        "circled": vertical.CIRCLED,
        "levels": [],
    }
    made = []
    for lv in LEVELS:
        os.makedirs(os.path.join(web_dir, "pdf", lv["key"]), exist_ok=True)
        level = {"key": lv["key"], "name": lv["name"], "desc": lv["desc"], "lessons": []}
        for n in range(1, len(lv["passages"]) + 1):
            lesson = _lesson(lv, n, seed)
            level["lessons"].append(lesson)
            for kind, answers in (("student", False), ("full", True)):
                path = os.path.join(web_dir, lesson["pdf"][kind])
                lesson_pdf.build_lesson(path, n, seed, answers=answers, level=lv["key"])
                made.append(path)
        data["levels"].append(level)
    path = os.path.join(web_dir, "data.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("// generate.py web で自動生成。手で編集しないでください。\n")
        f.write("window.KOKUGO = ")
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    made.append(path)
    return made


def clean_pdfs(web_dir):
    d = os.path.join(web_dir, "pdf")
    if os.path.isdir(d):
        shutil.rmtree(d)
