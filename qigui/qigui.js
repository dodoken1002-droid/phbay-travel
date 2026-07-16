/* ═══ 澎湖乞龜擲筊小遊戲（夏季旅展限定）═══
   規則：連續擲出 3 個聖筊即中獎。判定與每日禮物庫存（500份／4天，每日125份）
   一律由後端 /api/qigui/throw 權威決定，前端只負責動畫呈現，避免竄改或超發。
   localStorage 僅用於畫面體驗（重新整理仍看得到中獎畫面），非安全依據。 */

var streak = 0;          // 目前連續聖筊數（畫面顯示用，實際判定在後端）
var throwing = false;    // 動畫/請求進行中防連點
var STORE_WIN  = 'qigui_win';         // 中獎紀錄 JSON {code, date}（僅跨日自動失效）

function todayStr() {
  var d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function getWin() {
  try {
    var w = JSON.parse(localStorage.getItem(STORE_WIN) || 'null');
    return (w && w.date === todayStr()) ? w : null;
  } catch (e) { return null; }
}

/* ── 擲筊：呼叫後端做權威判定 ── */
function throwJiao() {
  if (throwing) return;
  var cached = getWin();
  if (cached) { showWin(cached.code); return; }

  throwing = true;
  var btn = document.getElementById('qg-throw');
  btn.disabled = true;
  setResult('筊杯擲出——', '');
  setLabels('', '');

  var bodyA = document.querySelector('#jiao-a .qg-jiao-body');
  var bodyB = document.querySelector('#jiao-b .qg-jiao-body');
  bodyA.classList.remove('spin', 'flat');
  bodyB.classList.remove('spin', 'flat');
  void bodyA.offsetWidth;  // 強制 reflow 重新觸發動畫
  bodyA.classList.add('spin');
  bodyB.classList.add('spin');

  fetch('/api/qigui/throw', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      setTimeout(function () { handleThrowResult(bodyA, bodyB, d); }, 1150);
    })
    .catch(function () {
      setTimeout(function () {
        bodyA.classList.remove('spin');
        bodyB.classList.remove('spin');
        setResult('連線不穩，請稍後再試一次 🙏', 'fail');
        throwing = false;
        btn.disabled = false;
      }, 1150);
    });
}

function handleThrowResult(bodyA, bodyB, d) {
  bodyA.classList.remove('spin');
  bodyB.classList.remove('spin');

  if (!d || !d.ok) {
    setResult('連線不穩，請稍後再試一次 🙏', 'fail');
    throwing = false;
    document.getElementById('qg-throw').disabled = false;
    return;
  }

  // 已在別的分頁/裝置乞得金龜過
  if (d.already_won) {
    setLabels('', '');
    setResult('您已乞得金龜！', 'holy');
    try { localStorage.setItem(STORE_WIN, JSON.stringify({ code: d.code, date: todayStr() })); } catch (e) {}
    showWin(d.code);
    return;
  }

  // 禮物名額已發完 / 今日挑戰已用完
  if (d.locked && !d.outcome) {
    setLabels('', '');
    setResult(d.message || '今日挑戰已結束，請明日再來！', d.sold_out ? 'fail' : '');
    lockToday();
    return;
  }

  // 依伺服器判定的結果決定筊杯視覺（聖筊＝一平一凸，笑筊＝兩平，陰筊＝兩凸）
  var aFlat, bFlat;
  if (d.outcome === 'holy') { aFlat = Math.random() < 0.5; bFlat = !aFlat; }
  else if (d.outcome === 'laugh') { aFlat = true; bFlat = true; }
  else { aFlat = false; bFlat = false; }
  if (aFlat) bodyA.classList.add('flat');
  if (bFlat) bodyB.classList.add('flat');
  setLabels(aFlat ? '平面朝上' : '凸面朝上', bFlat ? '平面朝上' : '凸面朝上');

  if (typeof gtag === 'function') gtag('event', 'qigui_throw', { outcome: d.outcome, streak: d.streak });

  if (d.outcome === 'holy') {
    streak = d.streak;
    lightDots();
    var t = document.getElementById('qg-turtle');
    t.classList.remove('happy'); void t.offsetWidth; t.classList.add('happy');

    if (d.won) {
      win(d.code);
      return;
    }
    setResult('🌓 聖筊！神明應允（' + streak + '／3）— 保持誠心，再擲！', 'holy');
    throwing = false;
    document.getElementById('qg-throw').disabled = false;
  } else {
    var msg = d.outcome === 'laugh'
      ? '🌕 笑筊——神明笑而不答，明日再來乞一次吧！'
      : '🌑 陰筊——神明未允，明日誠心再來！';
    setResult(msg, 'fail');
    streak = 0;
    lockToday(true);
    if (typeof gtag === 'function') gtag('event', 'qigui_fail', { outcome: d.outcome });
  }
}

/* ── 中獎 ── */
function win(code) {
  try { localStorage.setItem(STORE_WIN, JSON.stringify({ code: code, date: todayStr() })); } catch (e) {}
  setResult('🌓🌓🌓 三聖筊！', 'holy');
  if (typeof gtag === 'function') gtag('event', 'qigui_win', { code: code });
  if (typeof fbq === 'function') fbq('track', 'ViewContent', { content_name: '乞龜中獎', content_category: '乞龜擲筊遊戲' });
  setTimeout(function () { showWin(code); }, 700);
}

function showWin(code) {
  document.getElementById('qg-code').textContent = code;
  var winEl = document.getElementById('qg-win');
  winEl.style.display = 'block';
  document.getElementById('qg-throw').disabled = true;
  document.getElementById('qg-hint').textContent = '您已乞得金龜，請加 LINE 領取小禮物';
  throwing = false;
  winEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function trackLineClaim() {
  if (typeof gtag === 'function') gtag('event', 'qigui_line_claim', {});
  if (typeof fbq === 'function') fbq('track', 'Lead', { content_name: '乞龜領獎LINE', content_category: '乞龜擲筊遊戲' });
}

/* ── 當日已鎖定的狀態 ── */
function lockToday() {
  var btn = document.getElementById('qg-throw');
  btn.disabled = true;
  throwing = false;
  document.getElementById('qg-hint').innerHTML =
    '今日挑戰已結束，明天再來！或直接 <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 LINE 找潮旅</a> 安排澎湖行程';
}

/* ── UI 小工具 ── */
function setResult(text, cls) {
  var el = document.getElementById('qg-result');
  el.innerHTML = text;
  el.className = 'qg-result' + (cls ? ' ' + cls : '');
}

function setLabels(a, b) {
  document.getElementById('label-a').textContent = a;
  document.getElementById('label-b').textContent = b;
}

function lightDots() {
  var dots = document.querySelectorAll('.qg-dot');
  for (var i = 0; i < dots.length; i++) {
    dots[i].classList.toggle('lit', i < streak);
  }
}

/* ── 初始化：優先信任本機保存的中獎畫面，其餘一律由第一次擲筊時向後端確認 ── */
(function init() {
  var w = getWin();
  if (w) {
    streak = 3;
    lightDots();
    showWin(w.code);
    setResult('您已乞得金龜！', 'holy');
  }
})();

window.throwJiao = throwJiao;
window.trackLineClaim = trackLineClaim;
