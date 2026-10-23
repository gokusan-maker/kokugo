"""学習アプリ（web/）用に、授業プリントと同じ問題を data.js に書き出し、PDFを web/pdf/ に置く。"""
import json
import os
import shutil

from data.passages import MISTAKE_TYPES, PASSAGES
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


def _lesson(n, seed):
    p = PASSAGES[(n - 1) % len(PASSAGES)]
    kanji, goku = lesson_pdf.lesson_items(n, seed)
    return {
        "no": n,
        "plan": [{"what": w, "min": m} for w, m in lesson_pdf.PLAN],
        "kanji": {"inst": anki_pdf.CAT["kanji_kaki"][2],
                  "items": [{"src": it["src"], "a": it["a"]} for it in kanji]},
        "goku": {"inst": anki_pdf.CAT["kotowaza"][2],
                 "items": [{"src": it["src"], "a": it["a"], "mean": it["mean"]} for it in goku]},
        "passage": _passage(p),
        "pdf": {"student": "pdf/lesson%02d_student.pdf" % n, "full": "pdf/lesson%02d_full.pdf" % n},
    }


def export(web_dir, lessons, seed):
    pdf_dir = os.path.join(web_dir, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    data = {
        "types": [{"code": chobun_pdf.CODES[k], "name": v, "hint": chobun_pdf.HINTS[k]}
                  for k, v in MISTAKE_TYPES.items()],
        "steps": [{"title": h, "body": b} for h, b in chobun_pdf.STEPS],
        "circled": vertical.CIRCLED,
        "lessons": [],
    }
    made = []
    for n in lessons:
        lesson = _lesson(n, seed)
        data["lessons"].append(lesson)
        for kind, answers in (("student", False), ("full", True)):
            path = os.path.join(web_dir, lesson["pdf"][kind])
            lesson_pdf.build_lesson(path, n, seed, answers=answers)
            made.append(path)
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
