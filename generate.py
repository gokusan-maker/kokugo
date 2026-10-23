#!/usr/bin/env python3
"""中学受験 国語ドリル PDF ジェネレーター

使い方:
  python3 generate.py                 # すべてのPDFを pdf/ に作る
  python3 generate.py anki            # 暗記分野だけ
  python3 generate.py chobun          # 長文読解だけ
  python3 generate.py anki --only kanji_kaki yoji --sets 5 --seed 7
  python3 generate.py --list          # 分野の一覧

--seed を変えると、確認テストの出題順・出題範囲が変わります（同じ seed なら毎回同じ問題）。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from data.passages import PASSAGES  # noqa: E402
from kokugo_pdf import anki_pdf, chobun_pdf  # noqa: E402


def gen_anki(out, keys, sets, per_set, seed):
    d = os.path.join(out, "暗記分野")
    os.makedirs(d, exist_ok=True)
    for i, (key, name, *_rest) in enumerate(anki_pdf.CATEGORIES, 1):
        if keys and key not in keys:
            continue
        path = os.path.join(d, "%02d_%s.pdf" % (i, name.replace("・", "と")))
        anki_pdf.build_category(path, key, n_sets=sets, per_set=per_set, seed=seed)
        print("作成:", os.path.relpath(path, HERE))
    if not keys:
        path = os.path.join(d, "%02d_総合テスト.pdf" % (len(anki_pdf.CATEGORIES) + 1))
        anki_pdf.build_mix(path, n_sets=sets, seed=seed)
        print("作成:", os.path.relpath(path, HERE))


def gen_chobun(out):
    d = os.path.join(out, "長文読解")
    os.makedirs(d, exist_ok=True)
    for p in PASSAGES:
        path = os.path.join(d, "%s_%s_%s.pdf" % (p["id"], p["kind"], p["title"]))
        qs = chobun_pdf.build_passage(path, p)
        info = "、".join("問%d→%s（%d〜%d行目）" % (q["q"]["no"], q["answer"], *q["window"]) for q in qs)
        print("作成:", os.path.relpath(path, HERE), "｜", info)


def main():
    ap = argparse.ArgumentParser(description="中学受験 国語ドリルのPDFを作ります。")
    ap.add_argument("target", nargs="?", choices=["all", "anki", "chobun"], default="all",
                    help="作るもの（all=すべて / anki=暗記分野 / chobun=長文読解）")
    ap.add_argument("--only", nargs="*", default=[], metavar="分野キー",
                    help="暗記分野のうち作る分野（--list で一覧）")
    ap.add_argument("--sets", type=int, default=3, help="確認テストの回数（分野ごと、既定3）")
    ap.add_argument("--per-set", type=int, default=None,
                    help="1回あたりの問題数（既定：2列の分野は20問、1列の分野は15問）")
    ap.add_argument("--seed", default="1", help="出題を変えるための番号（既定1）")
    ap.add_argument("--out", default=os.path.join(HERE, "pdf"), help="出力先フォルダ")
    ap.add_argument("--list", action="store_true", help="分野と長文の一覧を表示")
    a = ap.parse_args()

    if a.list:
        print("暗記分野（--only に指定するキー）")
        for key, name, *_ in anki_pdf.CATEGORIES:
            print("  %-11s %s（%d問）" % (key, name, len(anki_pdf.items_for(key, a.seed))))
        print("長文読解")
        for p in PASSAGES:
            print("  %s %s「%s」 %s" % (p["id"], p["kind"], p["title"], p["about"]))
        return
    unknown = [k for k in a.only if k not in anki_pdf.CAT]
    if unknown:
        ap.error("知らない分野キー: %s（--list で一覧）" % " ".join(unknown))
    if a.target in ("all", "anki"):
        gen_anki(a.out, a.only, a.sets, a.per_set, a.seed)
    if a.target in ("all", "chobun"):
        gen_chobun(a.out)


if __name__ == "__main__":
    main()
