/* ═══ 乞龜幸運遊戲 — 三語系文字字典 ═══
   獨立於主站 i18n.js，僅供 /qigui/ 頁面使用。
   語言：zh-tw（繁中，預設）／en（英文）／zh-cn（簡中）
   切換後存 localStorage('qigui_lang')，data-i18n 屬性的元素會自動套用對應文字。 */

var QGUI_LANG_KEY = 'qigui_lang';

var QGUI_I18N = {
  'zh-tw': {
    'meta.title': '澎湖乞龜幸運遊戲｜秋季旅展限定｜連續三關贏得澎湖好禮｜潮旅國際旅行社',
    'meta.desc': '體驗澎湖乞龜百年民俗遊戲！秋季旅展限定，連續過關三次即可獲得澎湖限定好禮。認識乞龜由來，跟著潮旅玩澎湖。',
    'nav.line': '加官方 LINE',
    'hero.kicker': '秋季旅展限定小遊戲',
    'hero.title': '乞龜幸運挑戰',
    'hero.sub': '體驗澎湖百年民俗遊戲，連續過關 <strong>三次</strong>，<br>澎湖限定好禮帶回家！',
    'game.ready': '準備好了嗎？點擊下方按鈕開始挑戰！',
    'game.hint': '每人每日一次挑戰機會，未過關即結束，明天再來',
    'game.throw': '擲筊挑戰',
    'game.throw3': '一次擲3杯',
    'game.throwing': '筊杯擲出——',
    'game.throwingAuto': '筊杯連續擲出——',
    'game.flat': '正面朝上',
    'game.round': '反面朝上',
    'game.pass': '🎉 過關！（{n}／3）— 再接再厲！',
    'game.win': '🎉🎉🎉 三關全過！',
    'game.fail': '😊 差一點點——明天再來挑戰一次吧！',
    'game.offline': '連線不穩，請稍後再試一次 🙏',
    'game.alreadyDone': '您已完成今日挑戰！',
    'game.lockedHint': '今日挑戰已結束，明天再來！或直接 <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 LINE 找潮旅</a> 安排澎湖行程',
    'game.soldOut': '今日名額已全數送出，感謝您的參與，請明日再來挑戰！',
    'game.playedOut': '今日挑戰已使用，請明日再來',
    'win.title': '恭喜挑戰成功！',
    'win.desc': '您連續三關全數過關，太幸運了！<br>獲得 <strong>澎湖限定好禮一份</strong>',
    'win.codeLabel': '兌獎編號',
    'win.claimBtn': '加官方 LINE 領取好禮',
    'win.note': '請加入潮旅官方 LINE（@phbay2018），<strong>截圖此畫面並傳送兌獎編號</strong>，<br>現場出示畫面即可兌換好禮。每組編號限兌換一次。',
    'win.hintDone': '您已完成挑戰，請加 LINE 領取好禮',
    'culture.title': '🏮 認識澎湖「乞龜」文化',
    'culture.body': '每年元宵節期間，澎湖各地廟宇會擺出以糯米、麵線、黃金等製成的「祈福龜」，是澎湖流傳超過百年、全台獨有的民俗活動。傳統上，鄉親會擲筊請示是否能將龜請回家分享好運，隔年再答謝奉還更大的龜。這次秋季旅展，我們把這份趣味與好運文化搬到現場，讓大家輕鬆體驗！',
    'culture.g1t': '過關',
    'culture.g1d': '傳統稱「聖筊」：一正一反，象徵順利過關',
    'culture.g2t': '再接再厲',
    'culture.g2d': '傳統稱「笑筊」：兩面朝上，尚未過關',
    'culture.g3t': '再試一次',
    'culture.g3d': '傳統稱「陰筊」：兩面朝下，尚未過關',
    'culture.cta': '想更深入認識這項百年文化與澎湖旅遊？',
    'culture.ctaLink': '找潮旅安排行程',
    'footer.legal': '潮旅國際旅行社｜交觀乙第1864號｜澎品保0188號｜電話 06-9271288｜LINE @phbay2018',
    'footer.home': '回潮旅官網',
    'footer.neihai': '內海巡禮預購',
    'footer.quiz': '30 秒行程診斷',
  },
  'en': {
    'meta.title': 'Penghu Lucky Turtle Toss | Autumn Travel Fair Exclusive | Win a Penghu Gift | Phbay Travel',
    'meta.desc': 'Try Penghu\'s century-old lucky toss game! Autumn Travel Fair exclusive — clear 3 rounds in a row to win an exclusive Penghu gift. Learn about the tradition with Phbay Travel.',
    'nav.line': 'Add our LINE',
    'hero.kicker': 'Autumn Travel Fair Exclusive',
    'hero.title': 'Lucky Turtle Toss',
    'hero.sub': 'Try Penghu\'s century-old lucky toss game — clear <strong>3 rounds</strong> in a row<br>to win an exclusive Penghu gift!',
    'game.ready': 'Ready? Tap the button below to start!',
    'game.hint': 'One challenge per person per day — if you don\'t clear it, come back tomorrow!',
    'game.throw': 'Toss',
    'game.throw3': 'Toss 3 at Once',
    'game.throwing': 'Tossing——',
    'game.throwingAuto': 'Tossing in a row——',
    'game.flat': 'Face up',
    'game.round': 'Face down',
    'game.pass': '🎉 Cleared! ({n}/3) — Keep going!',
    'game.win': '🎉🎉🎉 All 3 Rounds Cleared!',
    'game.fail': '😊 So close — come back and try again tomorrow!',
    'game.offline': 'Connection issue, please try again shortly 🙏',
    'game.alreadyDone': 'You\'ve already completed today\'s challenge!',
    'game.lockedHint': 'Today\'s challenge is over — come back tomorrow! Or <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">add our LINE</a> to plan your Penghu trip',
    'game.soldOut': 'Today\'s gifts are all claimed — thanks for playing! Please come back tomorrow.',
    'game.playedOut': 'You\'ve used today\'s challenge — please come back tomorrow',
    'win.title': 'Congratulations, Challenge Complete!',
    'win.desc': 'You cleared all 3 rounds in a row — amazing luck!<br>You\'ve won an <strong>exclusive Penghu gift</strong>',
    'win.codeLabel': 'Redemption Code',
    'win.claimBtn': 'Add our LINE to Claim',
    'win.note': 'Please add our official LINE (@phbay2018), <strong>screenshot this page and send your redemption code</strong>,<br>then show this screen at our booth to claim your gift. Each code can be redeemed once.',
    'win.hintDone': 'Challenge complete — add our LINE to claim your gift',
    'culture.title': '🏮 About Penghu\'s "Turtle Blessing" Tradition',
    'culture.body': 'During Penghu\'s Lantern Festival each year, local temples display "lucky turtles" made of glutinous rice, noodles, or even gold — a century-old tradition found nowhere else in Taiwan. Traditionally, locals toss a pair of wooden blocks to see if they may take a turtle home for good fortune, returning an even bigger one the following year. For this Autumn Travel Fair, we\'ve brought this fun local custom to you as an interactive game!',
    'culture.g1t': 'Cleared',
    'culture.g1d': 'Traditionally called a "Sacred Toss": one up, one down — a clear pass',
    'culture.g2t': 'Try Again',
    'culture.g2d': 'Traditionally called a "Laughing Toss": both up — not yet',
    'culture.g3t': 'Try Again',
    'culture.g3d': 'Traditionally called a "Yin Toss": both down — not yet',
    'culture.cta': 'Want to learn more about this century-old tradition and Penghu travel?',
    'culture.ctaLink': 'Plan a trip with Phbay',
    'footer.legal': 'Phbay Travel International｜Travel Agency No. 1864｜Bond No. 0188｜Tel 06-9271288｜LINE @phbay2018',
    'footer.home': 'Back to Phbay Travel',
    'footer.neihai': 'Inner Sea Cruise Booking',
    'footer.quiz': '30-Second Trip Quiz',
  },
  'zh-cn': {
    'meta.title': '澎湖乞龟幸运游戏｜秋季旅展限定｜连续三关赢得澎湖好礼｜潮旅国际旅行社',
    'meta.desc': '体验澎湖乞龟百年民俗游戏！秋季旅展限定，连续过关三次即可获得澎湖限定好礼。认识乞龟由来，跟着潮旅玩澎湖。',
    'nav.line': '加官方 LINE',
    'hero.kicker': '秋季旅展限定小游戏',
    'hero.title': '乞龟幸运挑战',
    'hero.sub': '体验澎湖百年民俗游戏，连续过关 <strong>三次</strong>，<br>澎湖限定好礼带回家！',
    'game.ready': '准备好了吗？点击下方按钮开始挑战！',
    'game.hint': '每人每日一次挑战机会，未过关即结束，明天再来',
    'game.throw': '掷筊挑战',
    'game.throw3': '一次掷3杯',
    'game.throwing': '筊杯掷出——',
    'game.throwingAuto': '筊杯连续掷出——',
    'game.flat': '正面朝上',
    'game.round': '反面朝上',
    'game.pass': '🎉 过关！（{n}／3）— 再接再厉！',
    'game.win': '🎉🎉🎉 三关全过！',
    'game.fail': '😊 差一点点——明天再来挑战一次吧！',
    'game.offline': '连线不稳，请稍后再试一次 🙏',
    'game.alreadyDone': '您已完成今日挑战！',
    'game.lockedHint': '今日挑战已结束，明天再来！或直接 <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 LINE 找潮旅</a> 安排澎湖行程',
    'game.soldOut': '今日名额已全数送出，感谢您的参与，请明日再来挑战！',
    'game.playedOut': '今日挑战已使用，请明日再来',
    'win.title': '恭喜挑战成功！',
    'win.desc': '您连续三关全数过关，太幸运了！<br>获得 <strong>澎湖限定好礼一份</strong>',
    'win.codeLabel': '兑奖编号',
    'win.claimBtn': '加官方 LINE 领取好礼',
    'win.note': '请加入潮旅官方 LINE（@phbay2018），<strong>截图此画面并传送兑奖编号</strong>，<br>现场出示画面即可兑换好礼。每组编号限兑换一次。',
    'win.hintDone': '您已完成挑战，请加 LINE 领取好礼',
    'culture.title': '🏮 认识澎湖「乞龟」文化',
    'culture.body': '每年元宵节期间，澎湖各地庙宇会摆出以糯米、面线、黄金等制成的「祈福龟」，是澎湖流传超过百年、全台独有的民俗活动。传统上，乡亲会掷筊请示是否能将龟请回家分享好运，隔年再答谢奉还更大的龟。这次秋季旅展，我们把这份趣味与好运文化搬到现场，让大家轻松体验！',
    'culture.g1t': '过关',
    'culture.g1d': '传统称「圣筊」：一正一反，象征顺利过关',
    'culture.g2t': '再接再厉',
    'culture.g2d': '传统称「笑筊」：两面朝上，尚未过关',
    'culture.g3t': '再试一次',
    'culture.g3d': '传统称「阴筊」：两面朝下，尚未过关',
    'culture.cta': '想更深入认识这项百年文化与澎湖旅游？',
    'culture.ctaLink': '找潮旅安排行程',
    'footer.legal': '潮旅国际旅行社｜交观乙第1864号｜澎品保0188号｜电话 06-9271288｜LINE @phbay2018',
    'footer.home': '回潮旅官网',
    'footer.neihai': '内海巡礼预购',
    'footer.quiz': '30秒行程诊断',
  },
};

function qguiGetLang() {
  try {
    var saved = localStorage.getItem(QGUI_LANG_KEY);
    if (saved && QGUI_I18N[saved]) return saved;
  } catch (e) {}
  return 'zh-tw';
}

function qguiSetLang(lang) {
  if (!QGUI_I18N[lang]) return;
  try { localStorage.setItem(QGUI_LANG_KEY, lang); } catch (e) {}
  window.__qguiLang = lang;
  qguiApplyLang();
}

/* 取翻譯字串；vars 可傳 {n: 2} 這類插值，取代文字中的 {n} */
function QG_T(key, vars) {
  var lang = window.__qguiLang || qguiGetLang();
  var dict = QGUI_I18N[lang] || QGUI_I18N['zh-tw'];
  var str = dict[key] || QGUI_I18N['zh-tw'][key] || key;
  if (vars) {
    for (var k in vars) {
      str = str.split('{' + k + '}').join(vars[k]);
    }
  }
  return str;
}

/* 套用目前語言到所有帶 data-i18n / data-i18n-html 的元素，並更新 <title>／meta description／lang 屬性 */
function qguiApplyLang() {
  var lang = window.__qguiLang || qguiGetLang();
  document.documentElement.lang = lang === 'zh-tw' ? 'zh-Hant' : (lang === 'zh-cn' ? 'zh-Hans' : 'en');

  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    el.textContent = QG_T(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
    el.innerHTML = QG_T(el.getAttribute('data-i18n-html'));
  });

  var titleEl = document.querySelector('title');
  if (titleEl) titleEl.textContent = QG_T('meta.title');
  var descEl = document.querySelector('meta[name="description"]');
  if (descEl) descEl.setAttribute('content', QG_T('meta.desc'));

  document.querySelectorAll('.qgui-lang-btn').forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // 重新套用遊戲當下的動態訊息（若已擲過筊，避免切語言時卡在舊語言文字）
  if (typeof qguiRefreshDynamicText === 'function') qguiRefreshDynamicText();
}

window.__qguiLang = qguiGetLang();
// 這支 script 放在 </body> 前，此時 data-i18n 元素早已存在於 DOM，
// 直接同步套用即可，不等 DOMContentLoaded，避免畫面先閃預設語言再切換。
qguiApplyLang();
window.qguiSetLang = qguiSetLang;
