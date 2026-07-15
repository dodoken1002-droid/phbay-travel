/* ═══ 澎湖元宵乞龜擲筊小遊戲 ═══
   規則：連續擲出 3 個聖筊即中獎（每筊各 50% 平/凸，聖筊機率 50%，通關約 12.5%）
   限制：每人每日一次挑戰（localStorage 軟性限制），中獎憑證保存於本機重複顯示 */

var streak = 0;          // 目前連續聖筊數
var throwing = false;    // 動畫中防連點
var STORE_PLAY = 'qigui_last_play';   // 當日已挑戰（值＝日期字串）
var STORE_WIN  = 'qigui_win';         // 中獎紀錄 JSON {code, date}

function todayStr() {
  var d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function getWin() {
  try { return JSON.parse(localStorage.getItem(STORE_WIN) || 'null'); } catch (e) { return null; }
}

function playedToday() {
  try { return localStorage.getItem(STORE_PLAY) === todayStr(); } catch (e) { return false; }
}

function markPlayed() {
  try { localStorage.setItem(STORE_PLAY, todayStr()); } catch (e) {}
}

/* ── 擲筊 ── */
function throwJiao() {
  if (throwing) return;
  if (getWin()) { showWin(getWin().code); return; }
  if (playedToday()) { lockToday(); return; }

  throwing = true;
  var btn = document.getElementById('qg-throw');
  btn.disabled = true;
  setResult('筊杯擲出——', '');
  setLabels('', '');

  var bodyA = document.querySelector('#jiao-a .qg-jiao-body');
  var bodyB = document.querySelector('#jiao-b .qg-jiao-body');
  bodyA.classList.remove('spin', 'flat');
  bodyB.classList.remove('spin', 'flat');
  // 強制 reflow 重新觸發動畫
  void bodyA.offsetWidth;
  bodyA.classList.add('spin');
  bodyB.classList.add('spin');

  // 各筊 50% 平面朝上
  var aFlat = Math.random() < 0.5;
  var bFlat = Math.random() < 0.5;

  setTimeout(function () {
    bodyA.classList.remove('spin');
    bodyB.classList.remove('spin');
    if (aFlat) bodyA.classList.add('flat');
    if (bFlat) bodyB.classList.add('flat');
    setLabels(aFlat ? '平面朝上' : '凸面朝上', bFlat ? '平面朝上' : '凸面朝上');
    settle(aFlat, bFlat);
  }, 1150);
}

function settle(aFlat, bFlat) {
  var btn = document.getElementById('qg-throw');
  var outcome = (aFlat !== bFlat) ? 'holy' : (aFlat ? 'laugh' : 'yin');

  if (typeof gtag === 'function') gtag('event', 'qigui_throw', { outcome: outcome, streak: streak });

  if (outcome === 'holy') {
    streak++;
    lightDots();
    var t = document.getElementById('qg-turtle');
    t.classList.remove('happy'); void t.offsetWidth; t.classList.add('happy');
    if (streak >= 3) {
      win();
      return;
    }
    setResult('🌓 聖筊！神明應允（' + streak + '／3）— 保持誠心，再擲！', 'holy');
    throwing = false;
    btn.disabled = false;
  } else {
    var msg = outcome === 'laugh'
      ? '🌕 笑筊——神明笑而不答，明日再來乞一次吧！'
      : '🌑 陰筊——神明未允，明日誠心再來！';
    setResult(msg, 'fail');
    markPlayed();
    streak = 0;
    lockToday(true);
    if (typeof gtag === 'function') gtag('event', 'qigui_fail', { outcome: outcome });
  }
}

/* ── 中獎 ── */
function win() {
  markPlayed();
  var code = makeCode();
  try { localStorage.setItem(STORE_WIN, JSON.stringify({ code: code, date: todayStr() })); } catch (e) {}
  setResult('🌓🌓🌓 三聖筊！', 'holy');
  if (typeof gtag === 'function') gtag('event', 'qigui_win', { code: code });
  if (typeof fbq === 'function') fbq('track', 'ViewContent', { content_name: '乞龜中獎', content_category: '乞龜擲筊遊戲' });
  setTimeout(function () { showWin(code); }, 700);
}

function makeCode() {
  var d = new Date();
  var ymd = String(d.getFullYear()).slice(2) + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0');
  var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  var rand = '';
  for (var i = 0; i < 4; i++) rand += chars.charAt(Math.floor(Math.random() * chars.length));
  return '龜' + ymd + '-' + rand;
}

function showWin(code) {
  document.getElementById('qg-code').textContent = code;
  var winEl = document.getElementById('qg-win');
  winEl.style.display = 'block';
  document.getElementById('qg-throw').disabled = true;
  document.getElementById('qg-hint').textContent = '您已乞得金龜，請加 LINE 領取小禮物';
  winEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function trackLineClaim() {
  if (typeof gtag === 'function') gtag('event', 'qigui_line_claim', {});
  if (typeof fbq === 'function') fbq('track', 'Lead', { content_name: '乞龜領獎LINE', content_category: '乞龜擲筊遊戲' });
}

/* ── 當日已挑戰的鎖定狀態 ── */
function lockToday(justFailed) {
  var btn = document.getElementById('qg-throw');
  btn.disabled = true;
  throwing = false;
  document.getElementById('qg-hint').innerHTML =
    '今日挑戰已結束，明天再來！或直接 <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 LINE 找潮旅</a> 安排澎湖行程';
  if (!justFailed) {
    setResult('今日已擲過筊——請明日再來，或先看看乞龜的故事 👇', '');
  }
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

/* ── 初始化 ── */
(function init() {
  var w = getWin();
  if (w) {
    streak = 3;
    lightDots();
    showWin(w.code);
    setResult('您已乞得金龜！', 'holy');
    return;
  }
  if (playedToday()) lockToday();
})();

window.throwJiao = throwJiao;
window.trackLineClaim = trackLineClaim;
