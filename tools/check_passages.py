#!/usr/bin/env python3
"""長文データの検査。

  python3 tools/check_passages.py data/hatten_passages_1.py

各長文について、行数・字数・各設問の「前後10行」の範囲・正解の記号を表示し、
次のことを確かめる（問題があれば終了コード1）。
  - 正解の選択肢がちょうど1つ、×の選択肢に bad と type がある
  - 正解の解説が引用する根拠（{e1a} など）が、傍線部の前後10行に入っている
  - 解説で使っている {e..} / {L:e..} のタグが本文にある
  - bad が parts の範囲内
"""
import importlib.util
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kokugo_pdf import chobun_pdf  # noqa: E402


def load(path):
    spec = importlib.util.spec_from_file_location("passages_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lists = [v for k, v in vars(mod).items() if k.isupper() and isinstance(v, list)
             and v and isinstance(v[0], dict) and "paragraphs" in v[0]]
    return [p for lst in lists for p in lst]


def main():
    ok = True
    answers = Counter()
    for path in sys.argv[1:]:
        for p in load(path):
            try:
                lines, ranges, qs = chobun_pdf.analyze(p)
                for q in p["questions"]:
                    for c in q["choices"]:
                        for t in re.findall(r"\{(?:L:)?(e\w+)\}", c["why"]):
                            if t not in ranges:
                                raise ValueError("問%d: 解説のタグ %s が本文にない" % (q["no"], t))
                        if not c.get("ok") and not (0 <= c["bad"] < len(c["parts"])):
                            raise ValueError("問%d: bad が parts の範囲外" % q["no"])
                    if len(q["choices"]) != 4:
                        raise ValueError("問%d: 選択肢が4つではない" % q["no"])
                chars = sum(len(re.sub(r"<[^>]+>", "", x)) for x in p["paragraphs"])
                print("%s %s「%s」 %d行 %d字 | %s" % (
                    p["id"], p["kind"], p["title"], len(lines), chars,
                    "  ".join("問%d→%s（%d〜%d行）" % (it["q"]["no"], it["answer"], *it["window"]) for it in qs)))
                for it in qs:
                    answers[it["answer"]] += 1
            except Exception as e:  # noqa: BLE001
                ok = False
                print("%s エラー: %s" % (p.get("id"), e))
    print("正解の記号の数:", dict(sorted(answers.items())))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
