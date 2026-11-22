// オフラインで学習できるようにする service worker。
// アプリ本体（HTML・JS・CSS・data.js・アイコン）は最初に保存し、
// 開くたびにネットから新しいものを取りに行く（つながらないときは保存したものを使う）。
// PDF は一度開いたものだけ保存する（全部だと大きすぎるため）。
var CACHE = "kokugo-v1";
var CORE = ["./", "index.html", "app.js", "app.css", "data.js", "manifest.webmanifest",
            "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(CORE); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  var same = url.origin === self.location.origin;
  var font = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!same && !font) return;
  if (same && /\.zip$/.test(url.pathname)) return;   // ZIP は保存しない

  // ネット優先。取れたら保存し、取れなければ保存したものを返す
  e.respondWith(fetch(req).then(function (res) {
    if (res && (res.ok || res.type === "opaque")) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { c.put(req, copy); });
    }
    return res;
  }).catch(function () {
    return caches.match(req, { ignoreSearch: true }).then(function (hit) {
      return hit || (req.mode === "navigate" ? caches.match("index.html") : Response.error());
    });
  }));
});
