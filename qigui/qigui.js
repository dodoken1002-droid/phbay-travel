/* ═══ 澎湖乞龜幸運遊戲（秋季旅展限定）═══
   規則：連續過關 3 次即中獎。判定與每日禮物庫存一律由後端 /api/qigui/throw
   權威決定，前端只負責動畫呈現，避免竄改或超發。
   文字全部走 qigui-i18n.js 的 QG_T()；後端回傳的 message 僅供除錯參考，
   畫面一律改用本機三語字典渲染（見各 QG_T('game.xxx') 呼叫），確保切換
   語言時文字一致，不會因為後端只回中文而破圖。
   localStorage 僅用於畫面體驗（重新整理仍看得到中獎畫面），非安全依據。 */

var streak = 0;          // 目前連續過關數（畫面顯示用，實際判定在後端）
var throwing = false;    // 動畫/請求進行中防連點
var autoMode = false;    // 「一次擲3杯」：連續自動擲筊，直到中獎/鎖定/失敗為止
var lastState = 'idle';  // 目前畫面狀態，供切換語言時重新渲染：idle/pass/win/fail/locked/soldOut/alreadyDone

var STORE_WIN  = 'qigui_win';         // 中獎紀錄 JSON {code, date}（僅跨日自動失效）

function setThrowButtonsDisabled(disabled) {
  var b1 = document.getElementById('qg-throw');
  var b3 = document.getElementById('qg-throw3');
  if (b1) b1.disabled = disabled;
  if (b3) b3.disabled = disabled;
}

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
  setThrowButtonsDisabled(true);
  setResult(QG_T(autoMode ? 'game.throwingAuto' : 'game.throwing'), '');
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
        lastState = 'fail';
        setResult(QG_T('game.offline'), 'fail');
        throwing = false;
        autoMode = false;
        setThrowButtonsDisabled(false);
      }, 1150);
    });
}

/* ── 一次擲3杯：自動連續呼叫 throwJiao，直到中獎／鎖定／失敗為止 ── */
function throwJiaoAuto() {
  if (throwing) return;
  autoMode = true;
  throwJiao();
}

function handleThrowResult(bodyA, bodyB, d) {
  bodyA.classList.remove('spin');
  bodyB.classList.remove('spin');

  if (!d || !d.ok) {
    lastState = 'fail';
    setResult(QG_T('game.offline'), 'fail');
    throwing = false;
    autoMode = false;
    setThrowButtonsDisabled(false);
    return;
  }

  // 已在別的分頁/裝置完成今日挑戰過
  if (d.already_won) {
    setLabels('', '');
    lastState = 'alreadyDone';
    setResult(QG_T('game.alreadyDone'), 'holy');
    try { localStorage.setItem(STORE_WIN, JSON.stringify({ code: d.code, date: todayStr() })); } catch (e) {}
    autoMode = false;
    showWin(d.code);
    return;
  }

  // 禮物名額已發完 / 今日挑戰已用完
  if (d.locked && !d.outcome) {
    setLabels('', '');
    lastState = d.sold_out ? 'soldOut' : 'playedOut';
    setResult(QG_T(d.sold_out ? 'game.soldOut' : 'game.playedOut'), d.sold_out ? 'fail' : '');
    autoMode = false;
    lockToday();
    return;
  }

  // 依伺服器判定的結果決定筊杯視覺（過關＝一正一反，其餘＝兩面同向）
  var aFlat, bFlat;
  if (d.outcome === 'holy') { aFlat = Math.random() < 0.5; bFlat = !aFlat; }
  else if (d.outcome === 'laugh') { aFlat = true; bFlat = true; }
  else { aFlat = false; bFlat = false; }
  if (aFlat) bodyA.classList.add('flat');
  if (bFlat) bodyB.classList.add('flat');
  setLabels(QG_T(aFlat ? 'game.flat' : 'game.round'), QG_T(bFlat ? 'game.flat' : 'game.round'));

  if (typeof gtag === 'function') gtag('event', 'qigui_throw', { outcome: d.outcome, streak: d.streak, auto: autoMode });

  if (d.outcome === 'holy') {
    streak = d.streak;
    lightDots();
    var t = document.getElementById('qg-turtle');
    t.classList.remove('happy'); void t.offsetWidth; t.classList.add('happy');

    if (d.won) {
      autoMode = false;
      win(d.code);
      return;
    }
    lastState = 'pass';
    setResult(QG_T('game.pass', { n: streak }), 'holy');
    throwing = false;
    if (autoMode) {
      setTimeout(function () { throwJiao(); }, 600);
    } else {
      setThrowButtonsDisabled(false);
    }
  } else {
    lastState = 'fail';
    setResult(QG_T('game.fail'), 'fail');
    streak = 0;
    autoMode = false;
    lockToday(true);
    if (typeof gtag === 'function') gtag('event', 'qigui_fail', { outcome: d.outcome });
  }
}

/* ── 中獎 ── */
function win(code) {
  try { localStorage.setItem(STORE_WIN, JSON.stringify({ code: code, date: todayStr() })); } catch (e) {}
  lastState = 'win';
  setResult(QG_T('game.win'), 'holy');
  if (typeof gtag === 'function') gtag('event', 'qigui_win', { code: code });
  if (typeof fbq === 'function') fbq('track', 'ViewContent', { content_name: 'Qigui Win', content_category: 'Qigui Lucky Game' });
  setTimeout(function () { showWin(code); }, 700);
}

function showWin(code) {
  document.getElementById('qg-code').textContent = code;
  var winEl = document.getElementById('qg-win');
  winEl.style.display = 'block';
  setThrowButtonsDisabled(true);
  var hintEl = document.getElementById('qg-hint');
  if (hintEl) hintEl.textContent = QG_T('win.hintDone');
  throwing = false;
  winEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function trackLineClaim() {
  if (typeof gtag === 'function') gtag('event', 'qigui_line_claim', {});
  if (typeof fbq === 'function') fbq('track', 'Lead', { content_name: 'Qigui LINE Claim', content_category: 'Qigui Lucky Game' });
}

/* ── 當日已鎖定的狀態 ── */
function lockToday() {
  setThrowButtonsDisabled(true);
  throwing = false;
  var hintEl = document.getElementById('qg-hint');
  if (hintEl) hintEl.innerHTML = QG_T('game.lockedHint');
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

/* ── 切換語言時，重新渲染「目前狀態」對應的動態文字（不是靠 data-i18n 的靜態文字都要這裡處理）── */
function qguiRefreshDynamicText() {
  if (document.getElementById('qg-win') && document.getElementById('qg-win').style.display === 'block') {
    var hintEl = document.getElementById('qg-hint');
    if (hintEl) hintEl.textContent = QG_T('win.hintDone');
  } else if (document.getElementById('qg-throw') && document.getElementById('qg-throw').disabled &&
             lastState !== 'idle' && lastState !== 'pass') {
    var hintEl2 = document.getElementById('qg-hint');
    if (hintEl2 && (lastState === 'soldOut' || lastState === 'playedOut' || lastState === 'fail')) {
      hintEl2.innerHTML = QG_T('game.lockedHint');
    }
  }
  switch (lastState) {
    case 'pass':      setResult(QG_T('game.pass', { n: streak }), 'holy'); break;
    case 'win':        setResult(QG_T('game.win'), 'holy'); break;
    case 'fail':       setResult(QG_T('game.fail'), 'fail'); break;
    case 'soldOut':    setResult(QG_T('game.soldOut'), 'fail'); break;
    case 'playedOut':  setResult(QG_T('game.playedOut'), ''); break;
    case 'alreadyDone':setResult(QG_T('game.alreadyDone'), 'holy'); break;
    default:            if (!throwing) setResult(QG_T('game.ready'), '');
  }
}

/* ── 初始化：優先信任本機保存的中獎畫面，其餘一律由第一次擲筊時向後端確認 ── */
(function init() {
  var w = getWin();
  if (w) {
    streak = 3;
    lightDots();
    showWin(w.code);
    lastState = 'alreadyDone';
    setResult(QG_T('game.alreadyDone'), 'holy');
  }
})();

window.throwJiao = throwJiao;
window.throwJiaoAuto = throwJiaoAuto;
window.trackLineClaim = trackLineClaim;
window.qguiRefreshDynamicText = qguiRefreshDynamicText;
