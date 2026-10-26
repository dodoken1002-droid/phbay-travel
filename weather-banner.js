/* 上方資訊列的馬公天氣（資料：/api/weather → 中央氣象署 F-D0047-045）。
   取不到資料就什麼都不做，資訊列維持原樣；同一分頁 10 分鐘內換頁不重抓。
   樣式由本檔注入，沒載入 style.css 的頁面（秋冬專頁）也能用。 */
(function () {
  var CACHE_KEY = 'phbay_weather_v1';
  var CACHE_MS = 10 * 60 * 1000;
  // 氣象署官方「澎湖縣馬公市」鄉鎮預報頁（看完整未來 3 天與 1 週）
  var LINK = 'https://www.cwa.gov.tw/V8/C/W/Town/Town.html?TID=1001601';

  var CSS = [
    '.banner-weather{color:inherit;text-decoration:none;white-space:nowrap;font-weight:700}',
    '.banner-weather:hover{text-decoration:underline}',
    '.banner-weather .bw-sep{opacity:.55;margin:0 4px}',
    '.banner-weather .bw-alert{background:#F2B441;color:#4A3200;border-radius:999px;padding:1px 9px}',
    '.banner-weather .bw-alert-short{display:none}',
    /* 一般頁：天氣固定在最前面，後面的公司資訊放不下就淡出，不換行 */
    '.top-banner.has-weather .banner-static{flex-wrap:nowrap;justify-content:flex-start;white-space:nowrap;overflow:hidden;' +
      '-webkit-mask-image:linear-gradient(90deg,#000 94%,transparent);mask-image:linear-gradient(90deg,#000 94%,transparent)}',
    '@media (max-width:768px){',
    /* 手機只放得下一行：只留天氣，公司資訊在頁尾都有 */
    '.top-banner.has-weather .banner-static{justify-content:center;-webkit-mask-image:none;mask-image:none}',
    '.top-banner.has-weather .banner-static>:not(.banner-weather):not(.banner-sailing){display:none}',
    '.top-note.has-weather .tn-phone{display:none}',  /* 秋冬專頁：手機留天氣＋字號兩行 */
    '.banner-weather .bw-pop,.banner-weather .bw-pop-sep{display:none}',
    /* 強風時手機優先講風：隱藏天氣概況，提醒改短版 */
    '.banner-weather.is-windy .bw-main,.banner-weather.is-windy .bw-wind-sep{display:none}',
    '.banner-weather .bw-alert-long{display:none}.banner-weather .bw-alert-short{display:inline}',
    '}'
  ].join('');

  function icon(code) {
    var n = parseInt(code, 10);
    if (n === 1) return '☀️';
    if (n >= 2 && n <= 3) return '🌤️';
    if (n >= 4 && n <= 7) return '☁️';
    if (n >= 15 && n <= 22) return '⛈️';
    if (n >= 8) return '🌧️';
    return '⛅';
  }

  function span(cls, text) {
    var e = document.createElement('span');
    e.className = cls;
    e.textContent = text;
    return e;
  }

  function has(v) { return v !== null && v !== undefined && v !== ''; }

  function build(w, extraClass) {
    var a = document.createElement('a');
    a.className = 'banner-weather' + (w.strong_wind ? ' is-windy' : '') + (extraClass || '');
    a.href = LINK;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.title = '中央氣象署預報' + (w.forecast_time ? '（' + w.forecast_time.slice(5, 16).replace('T', ' ') + '）' : '');

    var main = icon(w.weather_code) + ' 馬公' + (has(w.temp_c) ? ' ' + w.temp_c + '°C' : '') + (w.weather ? ' ' + w.weather : '');
    var parts = [['bw-main', main]];
    if (w.wind_direction && has(w.beaufort)) {
      parts.push(['bw-wind', w.wind_direction + ' ' + w.beaufort + ' 級' + (w.beaufort_or_more ? '以上' : '')]);
    }
    if (has(w.pop_percent)) parts.push(['bw-pop', '降雨 ' + w.pop_percent + '%']);

    parts.forEach(function (p, i) {
      if (i > 0) a.appendChild(span('bw-sep ' + p[0] + '-sep', '｜'));  // 分隔線以後面那段命名，隱藏時一起藏
      a.appendChild(span(p[0], p[1]));
    });
    if (w.strong_wind) {
      a.appendChild(span('bw-sep bw-alert-sep', '｜'));
      var alert = span('bw-alert', '');
      alert.appendChild(span('bw-alert-long', '風浪較大，離島船班請先確認'));
      alert.appendChild(span('bw-alert-short', '⚠️ 離島船班請先確認'));
      a.appendChild(alert);
    }
    return a;
  }

  function render(w) {
    var banner = document.querySelector('.top-banner .banner-static');
    var note = document.querySelector('.top-note');
    var host = banner || note;
    if (!host || host.querySelector('.banner-weather')) return;
    if (!document.getElementById('banner-weather-css')) {
      var st = document.createElement('style');
      st.id = 'banner-weather-css';
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    var link = build(w, banner ? '' : ' tn-item');
    // 船班公告若已先顯示，天氣排在它後面
    var sailing = host.querySelector('.banner-sailing');
    var ref = sailing ? sailing.nextSibling : host.firstChild;
    host.insertBefore(span((banner ? 'banner-sep' : 'tn-sep') + ' banner-weather-sep', '｜'), ref);
    host.insertBefore(link, host.querySelector('.banner-weather-sep'));
    (banner ? banner.closest('.top-banner') : note).classList.add('has-weather');
  }

  /* 船班公告（/api/sailing-notice，後台「內海預購」分頁手動設定）：
     正常時不顯示；減班＝黃、停駛＝紅，點了到 FAQ 的風浪船班說明。
     強風提醒與船班公告同時存在時，只留船班公告（資訊更明確）。 */
  var SAILING_CSS = [
    '.banner-sailing{display:inline-block;white-space:nowrap;font-weight:700;text-decoration:none;border-radius:999px;padding:1px 10px;margin-right:6px}',
    '.banner-sailing.is-caution{background:#F2B441;color:#4A3200}',
    '.banner-sailing.is-suspended{background:#C53030;color:#fff}',
    '.banner-sailing:hover{text-decoration:underline}',
    '.has-sailing .banner-weather .bw-alert,.has-sailing .banner-weather .bw-alert-sep{display:none}',
    /* 手機只有一行：船班公告優先，天氣整段讓位 */
    '@media (max-width:768px){.has-sailing .banner-weather,.has-sailing .banner-weather-sep{display:none!important}}'
  ].join('');

  function renderSailing(n) {
    if (!n || !n.ok || (n.level !== 'caution' && n.level !== 'suspended') || !n.message) return;
    var banner = document.querySelector('.top-banner .banner-static');
    var host = banner || document.querySelector('.top-note');
    if (!host || host.querySelector('.banner-sailing')) return;
    if (!document.getElementById('banner-sailing-css')) {
      var st = document.createElement('style');
      st.id = 'banner-sailing-css';
      st.textContent = SAILING_CSS;
      document.head.appendChild(st);
    }
    var a = document.createElement('a');
    a.className = 'banner-sailing is-' + n.level + (banner ? '' : ' tn-item');
    a.href = '/faq#autumn-sailing';
    a.textContent = (n.level === 'suspended' ? '⛔ ' : '⚠️ ') + n.message;
    host.insertBefore(a, host.firstChild);
    (banner ? banner.closest('.top-banner') : host).classList.add('has-sailing');
    if (banner) banner.closest('.top-banner').classList.add('has-weather');  // 套用手機單行版面
    try { if (window.gtag) window.gtag('event', 'sailing_notice_view', { level: n.level }); } catch (e) {}
  }

  function loadSailing() {
    fetch('/api/sailing-notice', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(renderSailing)
      .catch(function () { /* 抓不到就不顯示 */ });
  }

  function load() {
    loadSailing();
    try {
      var c = JSON.parse(sessionStorage.getItem(CACHE_KEY) || 'null');
      if (c && Date.now() - c.at < CACHE_MS) { render(c.data); return; }
    } catch (e) { /* 無痕模式等情況讀不到就直接重抓 */ }
    fetch('/api/weather', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.ok) return;
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), data: d })); } catch (e) {}
        render(d);
      })
      .catch(function () { /* 抓不到就不顯示天氣 */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
