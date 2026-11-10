#!/usr/bin/env python3
"""授業プリントをレベルごとにまとめたZIPを作る（標準ライブラリだけで動く）。

  python3 tools/make_zips.py [web フォルダ]

web/pdf/<レベル>/lessonNN_{student,full}.pdf から
web/pdf/<レベル>/all_student.zip と all_full.zip を作る。
ZIPはサイズが大きく毎回変わるので Git には入れず、公開（デプロイ）のときにこれで作る。
"""
import glob
import os
import re
import sys
import zipfile

LEVEL_NAMES = {"kiso": "基礎", "hatten": "発展"}
KINDS = {"student": "生徒用", "full": "解答つき"}


def make(web_dir):
    made = []
    for level_dir in sorted(glob.glob(os.path.join(web_dir, "pdf", "*"))):
        key = os.path.basename(level_dir)
        name = LEVEL_NAMES.get(key, key)
        for kind, label in KINDS.items():
            files = sorted(glob.glob(os.path.join(level_dir, "lesson*_%s.pdf" % kind)))
            if not files:
                continue
            path = os.path.join(level_dir, "all_%s.zip" % kind)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in files:
                    n = int(re.search(r"lesson(\d+)_", os.path.basename(f)).group(1))
                    info = zipfile.ZipInfo("国語演習_%s_授業プリント_%s/国語演習_%s_第%02d回_%s.pdf"
                                           % (name, label, name, n, label), date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(f, "rb") as fp:
                        z.writestr(info, fp.read())
            made.append(path)
    return made


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in make(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "web")):
        print("作成:", p)
