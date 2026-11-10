#!/usr/bin/env python3
"""暗記問題の在庫チェック。

授業プリントは、分野ごとにシャッフルした問題を先頭から順に使う。
今ある回（＋余裕 --ahead 回）で使う問題数に対して在庫が足りないと、問題が一巡して
くり返しになり、さらにあとから問題を足したときに既存の回の問題が入れかわってしまう。
足りない分野と数を表示する（足りなければ終了コード1）。

  python3 tools/check_pools.py [--ahead 3]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.levels import LEVELS  # noqa: E402
from kokugo_pdf import anki_pdf, lesson_pdf  # noqa: E402

KEY2NAME = {"kanji_kaki": "KANJI_KAKI", "kanji_yomi": "KANJI_YOMI", "yoji": "YOJI", "kotowaza": "KOTOWAZA",
            "kanyoku": "KANYOKU", "koji": "KOJI", "taigigo": "TAIGIGO", "ruigigo": "RUIGIGO",
            "douon": "DOUON", "keigo": "KEIGO"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ahead", type=int, default=3, help="今ある回より何回先まで在庫を確保するか")
    a = ap.parse_args()
    short = False
    for lv in LEVELS:
        n = len(lv["passages"]) + a.ahead
        need = {}
        for i in range(1, n + 1):
            for key, k in lesson_pdf.KANJI + lesson_pdf.GOKU_ROTATION[(i - 1) % len(lesson_pdf.GOKU_ROTATION)]:
                need[key] = need.get(key, 0) + k
        print("■ %s（第%d回まで）" % (lv["name"], n))
        for key, k in need.items():
            if key == "douon":
                have = sum(len(rows) for _, rows in lv["anki"].DOUON)
            else:
                have = len(getattr(lv["anki"], KEY2NAME[key]))
            flag = "" if have >= k else "  ← %d問たりない" % (k - have)
            short |= have < k
            print("  %-10s 必要%4d  在庫%4d%s" % (anki_pdf.CAT[key][1], k, have, flag))
    sys.exit(1 if short else 0)


if __name__ == "__main__":
    main()
