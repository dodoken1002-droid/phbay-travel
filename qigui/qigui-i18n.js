/* ═══ 乞龜幸運遊戲 — 三語系文字字典 ═══
   獨立於主站 i18n.js，僅供 /qigui/ 頁面使用。
   語言：zh-tw（繁中，預設）／en（英文）／zh-cn（簡中）
   切換後存 localStorage('qigui_lang')，data-i18n 屬性的元素會自動套用對應文字。 */

var QGUI_LANG_KEY = 'qigui_lang';

var QGUI_I18N = {
  'zh-tw': {
    'meta.title': '澎湖乞龜幸運遊戲｜秋季旅展限定｜連續三關贏得澎湖好禮｜潮旅國際旅行社',
    'meta.desc': '體驗澎湖乞龜百年民俗遊戲！秋季旅展限定，連續過關三次即可獲得澎湖限定好禮。認識乞龜由來，跟著潮旅玩澎湖。',
    'nav.line': '加公司 WhatsApp',
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
    'game.lockedHint': '今日挑戰已結束，明天再來！或直接 <a href="https://wa.me/message/WHETZSTV2GFQM1" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 WhatsApp 找潮旅</a> 安排澎湖行程',
    'game.soldOut': '今日名額已全數送出，感謝您的參與，請明日再來挑戰！',
    'game.playedOut': '今日挑戰已使用，請明日再來',
    'win.title': '恭喜挑戰成功！',
    'win.desc': '您連續三關全數過關，太幸運了！<br>獲得 <strong>澎湖限定好禮一份</strong>',
    'win.codeLabel': '兌獎編號',
    'win.claimBtn': '加公司 WhatsApp 領取好禮',
    'win.note': '請加入潮旅公司 WhatsApp，<strong>截圖此畫面並傳送兌獎編號</strong>，<br>現場出示畫面即可兌換好禮。每組編號限兌換一次。',
    'win.hintDone': '您已完成挑戰，請加 WhatsApp 領取好禮',
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
    'footer.legal': '潮旅國際旅行社｜交觀乙第1864號｜品保澎字第0188號｜電話 06-9271288｜WhatsApp 諮詢',
    'footer.home': '回潮旅官網',
    'footer.neihai': '內海巡禮預購',
    'footer.quiz': '行程評估',
  },
  'en': {
    'meta.title': 'Penghu Lucky Turtle Toss | Autumn Travel Fair Exclusive | Win a Penghu Gift | Phbay Travel',
    'meta.desc': 'Try Penghu\'s century-old lucky toss game! Autumn Travel Fair exclusive — clear 3 rounds in a row to win an exclusive Penghu gift. Learn about the tradition with Phbay Travel.',
    'nav.line': 'Add our WhatsApp',
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
    'game.lockedHint': 'Today\'s challenge is over — come back tomorrow! Or <a href="https://wa.me/message/WHETZSTV2GFQM1" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">add our WhatsApp</a> to plan your Penghu trip',
    'game.soldOut': 'Today\'s gifts are all claimed — thanks for playing! Please come back tomorrow.',
    'game.playedOut': 'You\'ve used today\'s challenge — please come back tomorrow',
    'win.title': 'Congratulations, Challenge Complete!',
    'win.desc': 'You cleared all 3 rounds in a row — amazing luck!<br>You\'ve won an <strong>exclusive Penghu gift</strong>',
    'win.codeLabel': 'Redemption Code',
    'win.claimBtn': 'Add our WhatsApp to Claim',
    'win.note': 'Please add our official WhatsApp, <strong>screenshot this page and send your redemption code</strong>,<br>then show this screen at our booth to claim your gift. Each code can be redeemed once.',
    'win.hintDone': 'Challenge complete — add our WhatsApp to claim your gift',
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
    'footer.legal': 'Phbay Travel International｜Travel Agency No. 1864｜Bond No. 0188｜Tel 06-9271288｜WhatsApp',
    'footer.home': 'Back to Phbay Travel',
    'footer.neihai': 'Inner Sea Cruise Booking',
    'footer.quiz': 'Trip Assessment',
  },
  'ja': {
    'meta.title': '澎湖乞亀ラッキーゲーム｜秋の旅行博限定｜3回連続クリアで澎湖限定ギフト｜潮旅国際旅行社',
    'meta.desc': '澎湖に百年伝わる民俗遊び「乞亀」を体験！秋の旅行博限定、3回連続クリアで澎湖限定ギフトをプレゼント。乞亀の由来も知って、潮旅と澎湖を楽しもう。',
    'nav.line': 'WhatsAppを追加',
    'hero.kicker': '秋の旅行博限定ミニゲーム',
    'hero.title': '乞亀ラッキーチャレンジ',
    'hero.sub': '澎湖の百年民俗遊びを体験。<strong>3回連続</strong>クリアで<br>澎湖限定ギフトをお持ち帰り！',
    'game.ready': '準備はいい？下のボタンをタップしてスタート！',
    'game.hint': 'チャレンジは1人1日1回。クリアできなければ終了、また明日どうぞ',
    'game.throw': '筊（ジャオ）を投げる',
    'game.throw3': '一気に3回投げる',
    'game.throwing': '筊杯を投げています——',
    'game.throwingAuto': '連続で投げています——',
    'game.flat': '表向き',
    'game.round': '裏向き',
    'game.pass': '🎉 クリア！（{n}／3）— その調子！',
    'game.win': '🎉🎉🎉 3回全クリア！',
    'game.fail': '😊 惜しい！また明日チャレンジしてね！',
    'game.offline': '接続が不安定です。少し後でもう一度お試しください 🙏',
    'game.alreadyDone': '本日のチャレンジは完了しています！',
    'game.lockedHint': '本日のチャレンジは終了。また明日！または <a href="https://wa.me/message/WHETZSTV2GFQM1" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">WhatsAppで潮旅に相談</a>して澎湖旅行を計画しよう',
    'game.soldOut': '本日の景品はすべて終了しました。ご参加ありがとうございます。また明日どうぞ！',
    'game.playedOut': '本日のチャレンジは使用済みです。また明日どうぞ',
    'win.title': 'チャレンジ成功おめでとう！',
    'win.desc': '3回連続で全クリア、すごい強運です！<br><strong>澎湖限定ギフト1つ</strong>をプレゼント',
    'win.codeLabel': '引換番号',
    'win.claimBtn': 'WhatsAppでギフトを受け取る',
    'win.note': '潮旅のWhatsAppを追加し、<strong>この画面をスクリーンショットして引換番号を送信</strong>してください。<br>ブースで画面をご提示いただくとギフトと交換できます。各番号は1回限り有効。',
    'win.hintDone': 'チャレンジ完了。WhatsAppでギフトをお受け取りください',
    'culture.title': '🏮 澎湖の「乞亀」文化とは',
    'culture.body': '毎年元宵節（旧暦1月15日）の時期、澎湖各地の廟にはもち米・麺線・黄金などで作られた「祈福亀」が並びます。百年以上続く、台湾でも澎湖だけの民俗行事です。伝統では筊杯を投げて亀を家へ迎えて福を分かち合い、翌年さらに大きな亀でお返しをします。今回の秋の旅行博では、この楽しい開運文化を気軽に体験していただけます！',
    'culture.g1t': 'クリア',
    'culture.g1d': '「聖筊」：表と裏が1つずつ。順調にクリアの印',
    'culture.g2t': 'もう一度',
    'culture.g2d': '「笑筊」：両方とも表。まだクリアならず',
    'culture.g3t': 'もう一度',
    'culture.g3d': '「陰筊」：両方とも裏。まだクリアならず',
    'culture.cta': 'この百年文化と澎湖の旅をもっと知りたい？',
    'culture.ctaLink': '潮旅に旅程を相談',
    'footer.legal': '潮旅国際旅行社｜交觀乙第1864號｜品保澎字第0188號｜電話 06-9271288｜WhatsApp相談',
    'footer.home': '潮旅公式サイトへ',
    'footer.neihai': '内海クルーズ予約',
    'footer.quiz': '旅程プラン評価',
  },
  'ko': {
    'meta.title': '펑후 치구이 행운 게임｜가을 여행박람회 한정｜3연속 통과로 펑후 선물 획득｜차오뤼 국제여행사',
    'meta.desc': '펑후의 100년 민속놀이 ‘치구이(乞龜)’를 체험해 보세요! 가을 여행박람회 한정, 3회 연속 통과하면 펑후 한정 선물 증정. 치구이의 유래도 알아보고 차오뤼와 펑후를 즐기세요.',
    'nav.line': 'WhatsApp 추가',
    'hero.kicker': '가을 여행박람회 한정 미니게임',
    'hero.title': '치구이 행운 챌린지',
    'hero.sub': '펑후의 100년 민속놀이 체험, <strong>3회 연속</strong> 통과하면<br>펑후 한정 선물을 드려요!',
    'game.ready': '준비됐나요? 아래 버튼을 눌러 시작하세요!',
    'game.hint': '1인 1일 1회 도전, 실패하면 종료 — 내일 다시 도전하세요',
    'game.throw': '자오베이 던지기',
    'game.throw3': '한 번에 3회 던지기',
    'game.throwing': '자오베이를 던지는 중——',
    'game.throwingAuto': '연속으로 던지는 중——',
    'game.flat': '앞면',
    'game.round': '뒷면',
    'game.pass': '🎉 통과! ({n}/3) — 계속 가요!',
    'game.win': '🎉🎉🎉 3회 모두 통과!',
    'game.fail': '😊 아쉬워요 — 내일 다시 도전해 보세요!',
    'game.offline': '연결이 불안정합니다. 잠시 후 다시 시도해 주세요 🙏',
    'game.alreadyDone': '오늘의 도전을 이미 완료했습니다!',
    'game.lockedHint': '오늘의 도전이 끝났어요. 내일 다시! 아니면 <a href="https://wa.me/message/WHETZSTV2GFQM1" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">WhatsApp으로 차오뤼에 문의</a>해 펑후 여행을 계획하세요',
    'game.soldOut': '오늘 준비된 선물이 모두 소진되었습니다. 참여해 주셔서 감사합니다. 내일 다시 도전해 주세요!',
    'game.playedOut': '오늘의 도전을 이미 사용했습니다. 내일 다시 오세요',
    'win.title': '축하합니다, 챌린지 성공!',
    'win.desc': '3회 연속 모두 통과, 대단한 행운이에요!<br><strong>펑후 한정 선물 1개</strong> 증정',
    'win.codeLabel': '교환 번호',
    'win.claimBtn': 'WhatsApp 추가하고 선물 받기',
    'win.note': '차오뤼 WhatsApp을 추가한 뒤 <strong>이 화면을 캡처해 교환 번호를 보내 주세요</strong>.<br>부스에서 화면을 제시하면 선물로 교환해 드립니다. 번호당 1회만 교환 가능.',
    'win.hintDone': '챌린지 완료 — WhatsApp으로 선물을 받아 가세요',
    'culture.title': '🏮 펑후 ‘치구이(乞龜)’ 문화 알아보기',
    'culture.body': '매년 정월대보름 무렵, 펑후 곳곳의 사원에는 찹쌀·국수·황금 등으로 만든 ‘기복 거북’이 놓입니다. 100년 넘게 이어져 온, 대만에서도 펑후에만 있는 민속 행사입니다. 전통적으로는 자오베이를 던져 거북을 집으로 모셔 복을 나누고, 이듬해 더 큰 거북으로 보답합니다. 이번 가을 여행박람회에서 이 즐거운 행운 문화를 가볍게 체험해 보세요!',
    'culture.g1t': '통과',
    'culture.g1d': '‘성자오(聖筊)’: 앞뒤 하나씩 — 순조로운 통과의 표시',
    'culture.g2t': '다시 도전',
    'culture.g2d': '‘소자오(笑筊)’: 둘 다 앞면 — 아직 통과 전',
    'culture.g3t': '다시 도전',
    'culture.g3d': '‘음자오(陰筊)’: 둘 다 뒷면 — 아직 통과 전',
    'culture.cta': '이 100년 문화와 펑후 여행이 더 궁금하다면?',
    'culture.ctaLink': '차오뤼에 일정 문의',
    'footer.legal': '차오뤼 국제여행사｜交觀乙第1864號｜品保澎字第0188號｜전화 06-9271288｜WhatsApp 문의',
    'footer.home': '차오뤼 공식 사이트',
    'footer.neihai': '내해 크루즈 예약',
    'footer.quiz': '여행 일정 평가',
  },
  'zh-cn': {
    'meta.title': '澎湖乞龟幸运游戏｜秋季旅展限定｜连续三关赢得澎湖好礼｜潮旅国际旅行社',
    'meta.desc': '体验澎湖乞龟百年民俗游戏！秋季旅展限定，连续过关三次即可获得澎湖限定好礼。认识乞龟由来，跟着潮旅玩澎湖。',
    'nav.line': '加公司 WhatsApp',
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
    'game.lockedHint': '今日挑战已结束，明天再来！或直接 <a href="https://wa.me/message/WHETZSTV2GFQM1" target="_blank" rel="noopener noreferrer" style="color:#7dd6ff;font-weight:800">加 WhatsApp 找潮旅</a> 安排澎湖行程',
    'game.soldOut': '今日名额已全数送出，感谢您的参与，请明日再来挑战！',
    'game.playedOut': '今日挑战已使用，请明日再来',
    'win.title': '恭喜挑战成功！',
    'win.desc': '您连续三关全数过关，太幸运了！<br>获得 <strong>澎湖限定好礼一份</strong>',
    'win.codeLabel': '兑奖编号',
    'win.claimBtn': '加公司 WhatsApp 领取好礼',
    'win.note': '请加入潮旅公司 WhatsApp，<strong>截图此画面并传送兑奖编号</strong>，<br>现场出示画面即可兑换好礼。每组编号限兑换一次。',
    'win.hintDone': '您已完成挑战，请加 WhatsApp 领取好礼',
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
    'footer.legal': '潮旅国际旅行社｜交观乙第1864号｜品保澎字第0188号｜电话 06-9271288｜WhatsApp 咨询',
    'footer.home': '回潮旅官网',
    'footer.neihai': '内海巡礼预购',
    'footer.quiz': '行程评估',
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
  document.documentElement.lang = lang === 'zh-tw' ? 'zh-Hant' : (lang === 'zh-cn' ? 'zh-Hans' : lang);

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
