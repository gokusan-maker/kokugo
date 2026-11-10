"""あとから追加する暗記データ（毎日の自動更新でここに書き足す）。

レベルごとに、data/anki.py と同じ名前・同じ形のリストに追加する。
  - ここに足した問題は、授業プリントでは「まだ使っていない回」から順に使われる。
    すでに作った回の問題は（問題が一巡していなければ）変わらない。
  - 暗記ドリル（分野ごとのPDF）には、すぐに加わる。
  - data/anki.py・data/anki_hatten.py にすでにある問題と重複させないこと。
"""

NAMES = ["KANJI_KAKI", "KANJI_YOMI", "YOJI", "KOTOWAZA", "KANYOKU", "KOJI",
         "TAIGIGO", "RUIGIGO", "DOUON", "KEIGO"]

ADDED = {
    "kiso": {
        "KANJI_KAKI": [],
        "KANJI_YOMI": [],
        "YOJI": [],
        "KOTOWAZA": [],
        "KANYOKU": [],
        "KOJI": [],
        "TAIGIGO": [],
        "RUIGIGO": [],
        "DOUON": [],
        "KEIGO": [],
    },
    "hatten": {
        "KANJI_KAKI": [],
        "KANJI_YOMI": [],
        "YOJI": [],
        "KOTOWAZA": [],
        "KANYOKU": [],
        "KOJI": [],
        "TAIGIGO": [],
        "RUIGIGO": [],
        "DOUON": [],
        "KEIGO": [],
    },
}
