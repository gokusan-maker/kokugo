/* 国語演習アプリ
 * data.js（generate.py web で生成）の授業データを使い、授業プリントと同じ問題をブラウザで解く。
 * 進み具合はこのブラウザの localStorage に保存する（使えない環境では保存せずに動く）。
 */
(function () {
  "use strict";

  var D = window.KOKUGO;
  var view = document.getElementById("view");
  var CIRCLED = D.circled;
  var TYPE = {};
  D.types.forEach(function (t) { TYPE[t.code] = t; });

  // ------------------------------------------------------------ 保存

  function key(n) { return "kokugo:v2:lesson:" + n; }

  function blankState() {
    return {
      kanji: { ans: [], graded: false, over: {} },
      goku: { ans: [], graded: false, over: {} },
      q: {}, guide: false, read: false
    };
  }

  function load(n) {
    try {
      var s = JSON.parse(localStorage.getItem(key(n)));
      return s && s.kanji ? s : blankState();
    } catch (e) { return blankState(); }
  }

  function save(n, s) {
    try { localStorage.setItem(key(n), JSON.stringify(s)); } catch (e) { /* 保存できなくても続ける */ }
  }

  // ------------------------------------------------------------ 小物

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function norm(s) { return String(s || "").replace(/[\s　]/g, ""); }

  function lineLabel(s, e) { return s === e ? s + "行目" : s + "〜" + e + "行目"; }

  var toastTimer;
  function toast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }

  function lessonOf(n) {
    for (var i = 0; i < D.lessons.length; i++) if (D.lessons[i].no === n) return D.lessons[i];
    return null;
  }

  function steps(L) {
    var list = [
      { key: "cover", label: "はじめに" },
      { key: "kanji", label: "1 漢字" },
      { key: "goku", label: "2 語句" },
      { key: "guide", label: "3 解き方ガイド" },
      { key: "read", label: "4 長文を読む" }
    ];
    L.passage.questions.forEach(function (q) { list.push({ key: "q" + q.no, label: "問" + q.kanji }); });
    list.push({ key: "result", label: "結果" });
    return list;
  }

  function isDone(st, k) {
    if (k === "kanji" || k === "goku") return st[k].graded;
    if (k === "guide" || k === "read") return st[k];
    if (k[0] === "q") return !!(st.q[k.slice(1)] && st.q[k.slice(1)].graded);
    return false;
  }

  function testItems(T) {
    return T.sections.reduce(function (all, sec) { return all.concat(sec.items); }, []);
  }

  function isRight(it, ans) {
    var a = norm(ans);
    return !!a && it.accept.some(function (x) { return norm(x) === a; });
  }

  function testScore(L, st, kind) {
    var s = st[kind], ok = 0;
    testItems(L[kind]).forEach(function (it, i) { if (s.over[i] || isRight(it, s.ans[i])) ok++; });
    return ok;
  }

  function segHTML(segs) {
    return segs.map(function (g) {
      var t = esc(g.t);
      if (g.u) t = "<u>" + t + "</u>";
      return g.s ? "<small>" + t + "</small>" : t;
    }).join("");
  }

  function pdfButtons(L, small) {
    var c = small ? "btn small" : "btn";
    return '<a class="' + c + '" href="' + esc(L.pdf.student) + '" download>PDF（生徒用）</a>' +
      '<a class="' + c + '" href="' + esc(L.pdf.full) + '" download>PDF（解答つき）</a>';
  }

  // ------------------------------------------------------------ ルーティング

  function route() {
    var m = location.hash.match(/^#\/lesson\/(\d+)\/(\w+)/);
    if (!m) return { page: "home" };
    return { page: "lesson", n: +m[1], step: m[2] };
  }

  var lastHash = null;

  function render() {
    var r = route();
    var same = location.hash === lastHash;
    var pas = view.querySelector(".passage");
    var keep = same ? { x: pas ? pas.scrollLeft : null, y: window.scrollY } : null;
    if (!same) document.getElementById("toast").classList.remove("show");
    lastHash = location.hash;

    if (r.page === "home") {
      view.innerHTML = renderHome();
    } else {
      var L = lessonOf(r.n);
      if (!L) { location.hash = "#/"; return; }
      view.innerHTML = renderLesson(L, r.step);
    }
    if (keep) {
      var p2 = view.querySelector(".passage");
      if (p2 && keep.x !== null) p2.scrollLeft = keep.x;
      window.scrollTo(0, keep.y);
    } else {
      window.scrollTo(0, 0);
    }
  }

  // ------------------------------------------------------------ ホーム

  function renderHome() {
    var h = '<section class="hero"><h1>国語演習　授業プリント＆アプリ</h1>' +
      '<p class="muted">授業プリントと同じ問題を、アプリでもPDFでも学習できます。' +
      '漢字・ことわざ・慣用句のテストと、傍線部の前後10行から根拠をさがす「消去法」の長文演習。</p></section>' +
      '<div class="how">' +
      '<div><b>アプリで学習</b>答えを入力するとその場で採点。長文は縦書きで、選択肢を区切って○×をつけます。</div>' +
      '<div><b>PDFで印刷</b>同じ回の授業プリントをダウンロード。生徒用と、解答つき（先生用）があります。</div>' +
      '<div><b>進み具合を保存</b>このブラウザに自動で保存されるので、続きから再開できます。</div>' +
      '</div><div class="lessons">';
    D.lessons.forEach(function (L) {
      var st = load(L.no), P = L.passage;
      var qDone = P.questions.filter(function (q) { return st.q[q.no] && st.q[q.no].graded; }).length;
      var qOk = P.questions.filter(function (q) { return st.q[q.no] && st.q[q.no].graded && st.q[q.no].pick === q.answer; }).length;
      h += '<article class="lesson-card">' +
        '<h2>第' + L.no + '回</h2>' +
        '<p class="about">長文：' + esc(P.kind) + '「' + esc(P.title) + '」<br>' + esc(P.about) + '</p>' +
        '<div class="badges">' +
        badge(st.kanji.graded, "漢字", testScore(L, st, "kanji"), testItems(L.kanji).length) +
        badge(st.goku.graded, goName(L), testScore(L, st, "goku"), testItems(L.goku).length) +
        badge(qDone, "長文", qOk, P.questions.length) +
        '</div>' +
        '<div class="btn-row"><a class="btn primary" href="#/lesson/' + L.no + '/' + (qDone || st.kanji.graded ? resumeStep(L, st) : "cover") + '">' +
        (qDone || st.kanji.graded ? "続きから学習" : "アプリで学習する") + '</a></div>' +
        '<div class="btn-row">' + pdfButtons(L, true) + '</div>' +
        '</article>';
    });
    return h + '</div>';
  }

  function goName(L) {
    return L.goku.sections.map(function (s) { return s.name; }).join("・");
  }

  function badge(done, label, score, n) {
    return done ? '<span class="badge done">' + esc(label) + ' ' + score + '/' + n + '</span>'
      : '<span class="badge">' + esc(label) + ' ' + n + '問</span>';
  }

  function resumeStep(L, st) {
    var list = steps(L);
    for (var i = 1; i < list.length - 1; i++) if (!isDone(st, list[i].key)) return list[i].key;
    return "result";
  }

  // ------------------------------------------------------------ 授業

  function renderLesson(L, step) {
    var st = load(L.no);
    var list = steps(L);
    var idx = 0;
    list.forEach(function (s, i) { if (s.key === step) idx = i; });
    step = list[idx].key;
    if (step === "guide" && !st.guide) { st.guide = true; save(L.no, st); }
    if (step === "read" && !st.read) { st.read = true; save(L.no, st); }

    var h = '<div class="lesson-head"><h1>第' + L.no + '回　国語演習</h1>' +
      '<span class="muted">' + esc(L.passage.kind) + '「' + esc(L.passage.title) + '」</span></div>' +
      '<nav class="steps" aria-label="授業の流れ">';
    list.forEach(function (s, i) {
      h += '<a href="#/lesson/' + L.no + '/' + s.key + '" class="' + (i === idx ? "on " : "") + (isDone(st, s.key) ? "done" : "") + '">' + s.label + '</a>';
    });
    h += '</nav>';

    if (step === "cover") h += renderCover(L);
    else if (step === "kanji" || step === "goku") h += renderTest(L, st, step);
    else if (step === "guide") h += renderGuide();
    else if (step === "read") h += renderRead(L);
    else if (step[0] === "q") h += renderQuestion(L, st, +step.slice(1));
    else h += renderResult(L, st);

    h += '<div class="pager">' +
      (idx > 0 ? '<a class="btn" href="#/lesson/' + L.no + '/' + list[idx - 1].key + '">← ' + list[idx - 1].label + '</a>' : '<a class="btn" href="#/">← もどる</a>') +
      (idx < list.length - 1 ? '<a class="btn primary" href="#/lesson/' + L.no + '/' + list[idx + 1].key + '">' + list[idx + 1].label + ' →</a>' : '<a class="btn" href="#/">一覧へ</a>') +
      '</div>';
    return h;
  }

  function renderCover(L) {
    var total = 0;
    var h = '<div class="panel"><h2>今日のめあて</h2>' +
      '<p>一　漢字と' + esc(goName(L)) + 'を、書けるところまで確実に覚える。</p>' +
      '<p>二　傍線部の前後10行から根拠をさがし、消去法で選択肢を選べるようになる。</p></div>' +
      '<div class="panel"><h2>授業の流れ</h2><ol>';
    L.plan.forEach(function (p) { total += p.min; h += '<li>' + esc(p.what) + '　<span class="muted">' + p.min + '分</span></li>'; });
    h += '</ol><p class="muted">合計' + total + '分。アプリでは各ステップの答え合わせがその場でできます。</p></div>' +
      '<div class="panel"><h2>プリントで解く場合</h2><p class="muted">同じ問題の授業プリントをダウンロードして印刷できます（A4横・縦書き）。</p>' +
      '<div class="btn-row">' + pdfButtons(L) + '</div></div>';
    return h;
  }

  function renderTest(L, st, kind) {
    var T = L[kind], s = st[kind], i = -1;
    var h = '<h2>' + (kind === "kanji" ? "1　" : "2　") + esc(T.title) + '</h2>';
    T.sections.forEach(function (sec) {
      h += '<h3>■' + esc(sec.name) + '</h3><div class="inst">' + esc(sec.inst) + '</div><div class="qlist">';
      sec.items.forEach(function (it) {
        i++;
        h += renderTestItem(it, i, s, kind);
      });
      h += '</div>';
    });
    h += '<div class="score-line">';
    if (s.graded) {
      h += '<span class="score-big">' + testScore(L, st, kind) + ' / ' + testItems(T).length + '</span>' +
        '<span class="muted">別の書き方で合っているときは「○にする」で直せます。</span>' +
        '<button class="btn" data-act="retest" data-kind="' + kind + '">やり直す</button>';
    } else {
      h += '<button class="btn primary" data-act="grade" data-kind="' + kind + '">答え合わせ</button>';
    }
    return h + '</div>';
  }

  function renderTestItem(it, i, s, kind) {
    var h = "";
    var ok = s.over[i] || isRight(it, s.ans[i]);
    var cls = s.graded ? (ok ? " ok" : " ng") : "";
    h += '<div class="qitem' + cls + '"><span class="no">' + (i + 1) + '</span>' +
      '<div class="text">' + segHTML(it.q) + '</div>' +
      (it.mean ? '<div class="mean">意味：' + esc(it.mean) + '</div>' : '') +
      '<div class="ans"><input type="text" autocomplete="off" aria-label="(' + (i + 1) + ')の答え" data-act="ans" data-kind="' + kind + '" data-i="' + i + '" value="' + esc(s.ans[i] || "") + '"' + (s.graded ? " disabled" : "") + '>';
    if (s.graded) {
      h += ok ? '<span class="mark-ok">○</span>' : '<span class="mark-ng">×</span><span class="correct">' + esc(it.a) + '</span>';
      if (s.over[i] || !ok) {
        h += '<button class="btn small" data-act="over" data-kind="' + kind + '" data-i="' + i + '">' + (s.over[i] ? "×にもどす" : "○にする") + '</button>';
      }
    }
    return h + '</div></div>';
  }

  function renderGuide() {
    var h = '<h2>3　消去法の解き方ガイド</h2><div class="guide-steps">';
    D.steps.forEach(function (s) { h += '<div><b>' + esc(s.title) + '</b>' + esc(s.body) + '</div>'; });
    h += '</div><h3>×の種類（ひっかけのパターン）</h3><table class="types"><thead><tr><th>記号</th><th>×の種類</th><th>見分け方</th></tr></thead><tbody>';
    D.types.forEach(function (t) { h += '<tr><td>' + t.code + '</td><td>' + esc(t.name) + '</td><td>' + esc(t.hint) + '</td></tr>'; });
    return h + '</tbody></table><p class="muted" style="margin-top:10px">正解の選択肢は、本文の言葉をそのまま使わず「言いかえ」ていることが多いです。言葉が同じかどうかではなく、内容が同じかどうかで判断しましょう。</p>';
  }

  // ------------------------------------------------------------ 縦書き本文

  function renderPassage(P, opt) {
    opt = opt || {};
    var win = opt.window, marks = opt.marks || [], show = opt.evidence || [];
    var seenU = {};
    var h = '<div class="passage-box"><div class="passage-title"><b>' + esc(P.kind) + '「' + esc(P.title) + '」</b>' +
      '<span>' + (opt.note || "右から左へ読みます。上の数字は行番号。") + '</span></div>' +
      '<div class="passage" lang="ja">';
    P.lines.forEach(function (line, i) {
      var no = i + 1;
      var cls = "ln";
      if (win && no >= win[0] && no <= win[1]) cls += " win";
      if (marks.indexOf(no) >= 0) cls += " mark";
      h += '<div class="' + cls + '" data-act="line" data-no="' + no + '">' + (no % 5 === 0 ? '<span class="no">' + no + '</span>' : '');
      line.forEach(function (seg) {
        var c = [], label = "";
        seg.tags.forEach(function (t) {
          if (t[0] === "u") {
            c.push("u");
            if (+t.slice(1) === opt.active) c.push("active");
            if (!seenU[t]) { seenU[t] = 1; label = '<span class="ulabel">' + CIRCLED[+t.slice(1)] + '</span>'; }
          } else if (show.indexOf(t) >= 0) {
            c.push("ev", "show");
          }
        });
        h += label + (c.length ? '<span class="' + c.join(" ") + '">' + esc(seg.t) + '</span>' : esc(seg.t));
      });
      h += '</div>';
    });
    h += '</div>';
    if (opt.legend) {
      h += '<div class="legend"><span><i style="background:var(--win)"></i>前後10行の範囲</span>' +
        '<span><i style="background:var(--mark)"></i>あなたが印をつけた行</span>' +
        (show.length ? '<span><i style="background:var(--ev)"></i>正解の根拠</span>' : '') + '</div>';
    }
    return h + '</div>';
  }

  function renderRead(L) {
    return '<h2>4　長文を読む</h2><p class="muted">傍線部①②③に注意しながら、最後まで読みましょう。本文は横にスクロールできます。</p>' +
      renderPassage(L.passage, {});
  }

  // ------------------------------------------------------------ 問題（消去法ワークシート）

  function qState(st, no) {
    if (!st.q[no]) st.q[no] = { line: "", lo: "", hi: "", s1: null, marks: [], parts: {}, types: {}, pick: null, graded: false };
    return st.q[no];
  }

  function partMarks(qs, ci, n) {
    var a = qs.parts[ci] || [];
    while (a.length < n) a.push(0);
    return a;
  }

  function eliminated(qs, ci, n) { return partMarks(qs, ci, n).indexOf(2) >= 0; }

  function renderQuestion(L, st, no) {
    var P = L.passage, Q = null;
    P.questions.forEach(function (q) { if (q.no === no) Q = q; });
    var qs = qState(st, no);
    var showWin = qs.s1 === true || qs.graded;
    var ev = qs.graded ? Q.evidence.map(function (e) { return e.tag; }) : [];
    var dis = qs.graded ? " disabled" : "";
    var circ = CIRCLED[no];

    var h = renderPassage(P, { active: no, window: showWin ? Q.window : null, marks: qs.marks, evidence: ev, legend: true,
      note: "行をタップすると印をつけられます。" });
    h += '<div class="panel ws"><h2>問' + Q.kanji + '　' + esc(Q.kind) + '</h2><p>' + esc(Q.prompt) + '</p><div class="choices-read">';
    Q.choices.forEach(function (c) { h += '<p><b>' + c.kana + '</b>　' + esc(c.parts.join("")) + '</p>'; });
    h += '</div>';

    // ステップ1
    h += '<div class="step"><h3><span class="step-label">ステップ1</span>範囲を決める</h3>' +
      '<div class="inline-form">傍線部' + circ + 'は <input class="num" inputmode="numeric" data-act="qf" data-f="line" data-no="' + no + '" value="' + esc(qs.line) + '"' + dis + '> 行目。' +
      '　範囲は <input class="num" inputmode="numeric" data-act="qf" data-f="lo" data-no="' + no + '" value="' + esc(qs.lo) + '"' + dis + '> 〜 ' +
      '<input class="num" inputmode="numeric" data-act="qf" data-f="hi" data-no="' + no + '" value="' + esc(qs.hi) + '"' + dis + '> 行目' +
      (qs.graded ? '' : ' <button class="btn small" data-act="s1" data-no="' + no + '">確認</button>') + '</div>';
    if (qs.s1 === true || qs.graded) {
      h += '<div class="msg ok">傍線部' + circ + 'は' + lineLabel(Q.u[0], Q.u[1]) + '。前後10行の <b>' + Q.window[0] + '〜' + Q.window[1] + '行目</b> に色をつけました。この中から根拠をさがそう。</div>';
    } else if (qs.s1 === false) {
      h += '<div class="msg ng">' + esc(qs.s1msg || "もう一度確かめよう。") + '</div>';
    }
    h += '</div>';

    // ステップ2
    h += '<div class="step"><h3><span class="step-label">ステップ2</span>根拠に印をつける</h3>' +
      '<p class="muted">本文の中で、根拠だと思う行をタップしよう（もう一度タップで消える）。</p>' +
      '<p>印をつけた行：<span data-marks="' + no + '">' + marksText(qs.marks) + '</span></p></div>';

    // ステップ3
    h += '<div class="step"><h3><span class="step-label">ステップ3</span>選択肢を区切って○×をつける</h3>' +
      '<p class="muted">区切りをタップすると「・→○→×」と変わります。×があれば、その種類（A〜F）も選ぼう。</p>';
    Q.choices.forEach(function (c, ci) {
      var pm = partMarks(qs, ci, c.parts.length);
      h += '<div class="choice-row"><span class="kana">' + c.kana + '</span><div class="parts">';
      c.parts.forEach(function (p, pi) {
        var s = pm[pi];
        var truthBad = qs.graded && !c.ok && pi === c.bad;
        h += '<button class="part' + (s === 1 ? " o" : s === 2 ? " x" : "") + (truthBad ? " truth-bad" : "") + '" data-act="part" data-no="' + no + '" data-ci="' + ci + '" data-pi="' + pi + '"' + dis + ' aria-label="' + esc(p) + '">' +
          '<span class="st">' + (s === 1 ? "○" : s === 2 ? "×" : "・") + '</span>' + esc(p) + '</button>';
      });
      h += '</div>';
      if (pm.indexOf(2) >= 0) {
        h += '<label class="type-sel">×の種類 <select data-act="type" data-no="' + no + '" data-ci="' + ci + '"' + dis + '><option value="">えらぶ</option>';
        D.types.forEach(function (t) { h += '<option value="' + t.code + '"' + (qs.types[ci] === t.code ? " selected" : "") + '>' + t.code + '　' + esc(t.name) + '</option>'; });
        h += '</select></label>';
      }
      h += '</div>';
    });
    h += '</div>';

    // ステップ4
    h += '<div class="step"><h3><span class="step-label">ステップ4</span>×のない選択肢が答え</h3><div class="picks">';
    Q.choices.forEach(function (c, ci) {
      h += '<button class="pick' + (qs.pick === c.kana ? " on" : "") + (eliminated(qs, ci, c.parts.length) ? " elim" : "") + '" data-act="pick" data-no="' + no + '" data-k="' + c.kana + '"' + dis + ' aria-pressed="' + (qs.pick === c.kana) + '">' + c.kana + '</button>';
    });
    h += '</div>';
    if (!qs.graded) {
      h += '<div class="score-line"><button class="btn primary" data-act="qgrade" data-no="' + no + '"' + (qs.pick ? "" : " disabled") + '>答え合わせ</button>' +
        (qs.pick ? '' : '<span class="muted">答えをえらぶと答え合わせできます。</span>') + '</div>';
    } else {
      h += renderExplanation(Q, qs);
    }
    return h + '</div></div>';
  }

  function marksText(marks) {
    if (!marks.length) return "まだありません";
    return marks.slice().sort(function (a, b) { return a - b; }).map(function (n) { return n + "行目"; }).join("、");
  }

  function renderExplanation(Q, qs) {
    var right = qs.pick === Q.answer;
    var h = '<div class="result-box ' + (right ? "ok" : "ng") + '"><div class="big">' + (right ? "○ 正解！" : "× ざんねん") + '　答えは ' + Q.answer + '</div>' +
      '<p>範囲：' + Q.window[0] + '〜' + Q.window[1] + '行目（本文で黄色の部分）</p>' +
      '<p>根拠（本文で青い部分）：<br>' + Q.evidence.map(function (e) { return "・" + lineLabel(e.s, e.e) + "「" + esc(e.text) + "」"; }).join("<br>") + '</p>' +
      '<p><b>ポイント</b>　' + esc(Q.point) + '</p></div><div class="expl">';
    Q.choices.forEach(function (c, ci) {
      var pm = partMarks(qs, ci, c.parts.length);
      var verdict = c.ok ? '<span class="verdict ok">○ 正解の選択肢</span>'
        : '<span class="verdict ng">× ' + c.type + '　' + esc(TYPE[c.type].name) + '</span>';
      var yours = "";
      if (!c.ok) {
        var caught = pm[c.bad] === 2;
        yours = caught ? "×の部分を見つけられた！" : "×の部分（赤わく）を見落としていたよ。";
        if (qs.types[ci]) yours += qs.types[ci] === c.type ? "　種類も正解。" : "　種類は " + qs.types[ci] + " ではなく " + c.type + "。";
      } else if (pm.indexOf(2) >= 0) {
        yours = "正解の選択肢に×をつけていたよ。本文の言いかえに注意。";
      }
      h += '<div class="choice-row' + (c.ok ? " right" : "") + '"><span class="kana">' + c.kana + '</span>' + verdict +
        (yours ? '<div class="yours">' + yours + '</div>' : '') + '<div class="why">' + esc(c.why) + '</div></div>';
    });
    return h + '</div><div class="btn-row"><button class="btn" data-act="qreset" data-no="' + Q.no + '">この問題をやり直す</button></div>';
  }

  // ------------------------------------------------------------ 結果

  function renderResult(L, st) {
    var P = L.passage;
    var qOk = 0, judged = 0, judgedOk = 0, missed = {};
    P.questions.forEach(function (Q) {
      var qs = st.q[Q.no];
      if (!qs || !qs.graded) return;
      if (qs.pick === Q.answer) qOk++;
      Q.choices.forEach(function (c, ci) {
        var pm = partMarks(qs, ci, c.parts.length);
        pm.forEach(function (m, pi) {
          if (!m) return;
          judged++;
          var truth = (c.ok || pi !== c.bad) ? 1 : 2;
          if (m === truth) judgedOk++;
        });
        if (!c.ok && pm[c.bad] !== 2) missed[c.type] = (missed[c.type] || 0) + 1;
      });
    });
    var h = '<h2>今日の結果</h2><div class="scores">' +
      '<div>漢字テスト<b>' + (st.kanji.graded ? testScore(L, st, "kanji") : "―") + '</b>/ ' + testItems(L.kanji).length + '</div>' +
      '<div>' + esc(goName(L)) + '<b>' + (st.goku.graded ? testScore(L, st, "goku") : "―") + '</b>/ ' + testItems(L.goku).length + '</div>' +
      '<div>長文（選択問題）<b>' + qOk + '</b>/ ' + P.questions.length + '</div>' +
      '<div>○×の判断の正確さ<b>' + (judged ? Math.round(judgedOk / judged * 100) + "%" : "―") + '</b>' + (judged ? judgedOk + " / " + judged + " か所" : "区切りに○×をつけよう") + '</div>' +
      '</div>';
    var keys = Object.keys(missed);
    h += '<div class="panel" style="margin-top:14px"><h3>見落としやすい×の種類</h3>';
    if (keys.length) {
      h += '<ul>' + keys.map(function (k) { return '<li><b>' + k + '　' + esc(TYPE[k].name) + '</b>（' + missed[k] + 'か所）<br><span class="muted">' + esc(TYPE[k].hint) + '</span></li>'; }).join("") + '</ul>';
    } else {
      h += '<p class="muted">答え合わせした問題では、見落としはありませんでした。</p>';
    }
    h += '</div><div class="panel"><h3>プリントで復習</h3><div class="btn-row">' + pdfButtons(L) + '</div></div>' +
      '<button class="btn" data-act="reset-lesson" data-n="' + L.no + '">この回を最初からやり直す</button>';
    return h;
  }

  // ------------------------------------------------------------ 操作

  function current() {
    var r = route();
    return r.page === "lesson" ? lessonOf(r.n) : null;
  }

  view.addEventListener("input", function (e) {
    var t = e.target, L = current();
    if (!L || !t.dataset) return;
    var st = load(L.no);
    if (t.dataset.act === "ans") {
      st[t.dataset.kind].ans[+t.dataset.i] = t.value;
      save(L.no, st);
    } else if (t.dataset.act === "qf") {
      qState(st, t.dataset.no)[t.dataset.f] = t.value.replace(/[０-９]/g, function (d) { return String.fromCharCode(d.charCodeAt(0) - 0xFEE0); });
      save(L.no, st);
    }
  });

  view.addEventListener("change", function (e) {
    var t = e.target, L = current();
    if (!L || t.dataset.act !== "type") return;
    var st = load(L.no);
    qState(st, t.dataset.no).types[+t.dataset.ci] = t.value;
    save(L.no, st);
  });

  view.addEventListener("click", function (e) {
    var el = e.target.closest("[data-act]");
    var L = current();
    if (!el || !L) return;
    var act = el.dataset.act, st = load(L.no), d = el.dataset, qs;
    var P = L.passage;

    if (act === "grade") {
      st[d.kind].graded = true;
      save(L.no, st);
      render();
      toast(testScore(L, st, d.kind) + " / " + testItems(L[d.kind]).length + " 点");
    } else if (act === "retest") {
      st[d.kind] = { ans: [], graded: false, over: {} };
      save(L.no, st); render();
    } else if (act === "over") {
      var o = st[d.kind].over;
      if (o[d.i]) delete o[d.i]; else o[d.i] = true;
      save(L.no, st); render();
    } else if (act === "line") {
      var r = route();
      if (r.step[0] !== "q") return;
      qs = qState(st, r.step.slice(1));
      if (qs.graded) return;
      var no = +d.no, i = qs.marks.indexOf(no);
      if (i >= 0) qs.marks.splice(i, 1); else qs.marks.push(no);
      save(L.no, st);
      el.classList.toggle("mark");
      var m = view.querySelector('[data-marks="' + r.step.slice(1) + '"]');
      if (m) m.textContent = marksText(qs.marks);
    } else if (act === "s1") {
      var Q = P.questions.filter(function (q) { return q.no === +d.no; })[0];
      qs = qState(st, d.no);
      var line = parseInt(qs.line, 10), lo = parseInt(qs.lo, 10), hi = parseInt(qs.hi, 10), n = P.lines.length;
      if (!(line >= Q.u[0] && line <= Q.u[1])) {
        qs.s1 = false; qs.s1msg = "傍線部" + CIRCLED[Q.no] + "の行番号をもう一度確かめよう。本文の上の数字は5行ごとです。";
      } else if (!((lo === Math.max(1, line - 10) && hi === Math.min(n, line + 10)) || (lo === Q.window[0] && hi === Q.window[1]))) {
        qs.s1 = false; qs.s1msg = "範囲は「傍線部の行 − 10」から「傍線部の行 + 10」まで。本文の最初（1行目）と最後（" + n + "行目）はこえないよ。";
      } else {
        qs.s1 = true;
      }
      save(L.no, st); render();
    } else if (act === "part") {
      qs = qState(st, d.no);
      var c = P.questions.filter(function (q) { return q.no === +d.no; })[0].choices[+d.ci];
      var pm = partMarks(qs, +d.ci, c.parts.length);
      pm[+d.pi] = (pm[+d.pi] + 1) % 3;
      qs.parts[+d.ci] = pm;
      save(L.no, st); render();
    } else if (act === "pick") {
      qState(st, d.no).pick = d.k;
      save(L.no, st); render();
    } else if (act === "qgrade") {
      qs = qState(st, d.no);
      if (!qs.pick) return;
      qs.graded = true;
      save(L.no, st); render();
      var Q2 = P.questions.filter(function (q) { return q.no === +d.no; })[0];
      toast(qs.pick === Q2.answer ? "正解！ 解説を読んで根拠を確かめよう" : "答えは " + Q2.answer + "。解説で×の部分を確かめよう");
    } else if (act === "qreset") {
      delete st.q[d.no];
      save(L.no, st); render();
    } else if (act === "reset-lesson") {
      if (window.confirm("第" + d.n + "回の答えと結果をすべて消して、最初からやり直しますか？")) {
        save(L.no, blankState());
        location.hash = "#/lesson/" + d.n + "/cover";
      }
    }
  });

  window.addEventListener("hashchange", render);
  render();
})();
