/* ═══════════════════════════════════════════════
   潮旅國際旅行社 — 多語言 i18n
   預設語言：繁體中文（HTML 內原文）
   支援：English / 日本語 / 한국어 / 简体中文
════════════════════════════════════════════════ */

const LANG_NAMES = { 'zh-tw':'中文', 'en':'EN', 'ja':'日本語', 'ko':'한국어', 'zh-cn':'简体' };
const LANG_HTML  = { 'zh-tw':'zh-TW', 'en':'en', 'ja':'ja', 'ko':'ko', 'zh-cn':'zh-CN' };

const DICT = {
  /* ─────────── English ─────────── */
  en: {
    'nav.home':'Home', 'nav.tours':'Tours', 'nav.quiz':'Trip Quiz', 'nav.about':'About', 'nav.faq':'FAQ', 'nav.blog':'Blog', 'nav.contact':'Contact',
    'nav.preorder':'Pre-order', 'nav.neihai':'Inner Sea Cruise', 'nav.festival':'Music Festival', 'nav.travel':'Travel Info', 'nav.tides':'Tide Forecast', 'nav.articles':'Travel Articles', 'nav.reviews':'Reviews', 'nav.contactInfo':'Contact Info',
    'slide.cta':'Ask About Tours',
    'partner.title':'Official Partner · 2026 Penghu Chasing-the-Wind Music & Light Festival','partner.subtitle':'Phbay Travel is on the official partner list alongside ezTravel, Lion Travel, Cola Tour, SET Tour, Starsunny, kkday and EverFun.',
    'hero.title':'Phbay Travel', 'hero.subtitle':'Discover a different side of Penghu',
    'hero.tagline':'Local & In-Depth × Family-Friendly × Sustainable Ocean',
    'hero.btnTours':'View Recommended Tours', 'hero.btnContact':'Enquire Now',
    'feat.1.title':'Local In-Depth Travel', 'feat.1.desc':'Locals show you Penghu — hidden spots and stories you won’t find elsewhere.',
    'feat.2.title':'Family-Friendly Design', 'feat.2.desc':'Every detail thoughtfully arranged so the whole family can relax and enjoy.',
    'feat.3.title':'Sustainable Ocean', 'feat.3.desc':'We protect Penghu’s marine ecology, preserving its beauty for the next generation.',
    'tours.title':'Featured Tours', 'tours.subtitle':'A Penghu journey tailored just for you',
    'cat.package':'Package Tours', 'cat.single':'Single Tours',
    'tab.featured':'Official Partner Tours', 'tab.2d1n':'2 Days 1 Night', 'tab.3d2n':'3 Days 2 Nights', 'tab.4d3n':'4 Days 3 Nights',
    'tab.north-sea':'North Sea', 'tab.east-sea':'East Sea', 'tab.south-sea':'South Sea', 'tab.main-island':'Main Island',
    'tours.empty':'More tours coming soon. Stay tuned!',
    'about.badge':'Years of Penghu Experience', 'about.title':'About Us',
    'about.p1':'Phbay Travel is a travel agency built around in-depth local Penghu tourism. We believe travel is not just about photos, but a beautiful time to let your mind breathe.',
    'about.p2':'We focus on family travel, ocean experiences and sustainable tourism. Every itinerary is personally planned by local guides, taking you to the Penghu that ordinary tourists never see.',
    'about.p3':'From snorkeling, SUP and tidal-flat ecology to green sea turtle conservation on Wang’an, we help you discover this blue treasure island in the most memorable way.',
    'about.stat1':'Travelers Served', 'about.stat2':'Curated Tours', 'about.stat3':'Satisfaction',
    'quiz.title':'Find Your Perfect Penghu Trip', 'quiz.subtitle':'4 questions · 30 seconds · find the trip that suits you best',
    'contact.title':'Contact Us', 'contact.subtitle':'Any questions or want to know more about our tours? Reach us anytime below.',
    'contact.methods':'Get in Touch', 'contact.lineLabel':'Official LINE', 'contact.phoneLabel':'Phone', 'contact.emailLabel':'Email',
    'contact.hours':'Hours: Mon–Fri 08:30–17:30<br>(Closed weekends & national holidays)',
    'form.heading':'Online Enquiry Form',
    'form.name':'Name', 'form.namePh':'Enter your name',
    'form.phone':'Phone', 'form.phonePh':'e.g. 0912-345-678',
    'form.dateStart':'Departure Date', 'form.dateEnd':'Return Date',
    'form.people':'Number of Travelers', 'form.peoplePh':'Select number',
    'form.budget':'Budget per Person', 'form.budgetPh':'Select budget range',
    'form.transport':'Transport', 'form.byPlane':'By Plane', 'form.byBoat':'By Ferry',
    'form.departure':'Departure City', 'form.departurePh':'Select transport first',
    'form.tourInterest':'Tour of Interest', 'form.tourHint':'(choose to pick a departure date)', 'form.tourPh':'Select a tour (optional)',
    'form.slot':'Select Departure Date', 'form.notes':'Notes / Special Requests', 'form.notesPh':'e.g. stroller, vegetarian, birthday arrangements...',
    'form.submit':'Send Enquiry',
    'form.successDefault':'Your enquiry has been sent! We will contact you within one business day.',
    'form.successLine2':'You can also add us on LINE: <strong>@phbay2018</strong> for a faster reply.',
    'banner.consult':'Enquire Now',
    'footer.quickLinks':'Quick Links', 'footer.contactInfo':'Contact Info',
    'footer.owner':'Owner: Tang Wei-Ju', 'footer.hours':'Mon–Fri 08:30–17:30'
  },

  /* ─────────── 日本語 ─────────── */
  ja: {
    'nav.home':'ホーム', 'nav.tours':'ツアー', 'nav.quiz':'旅行診断', 'nav.about':'会社紹介', 'nav.faq':'よくある質問', 'nav.blog':'ブログ', 'nav.contact':'お問い合わせ',
    'nav.preorder':'事前予約', 'nav.neihai':'内海クルーズ', 'nav.festival':'音楽祭', 'nav.travel':'旅の情報', 'nav.tides':'潮汐予報', 'nav.articles':'旅行記事', 'nav.reviews':'お客様の声', 'nav.contactInfo':'連絡先',
    'slide.cta':'ツアーを相談する',
    'partner.title':'2026 澎湖追風音楽燈光祭 公式提携旅行社','partner.subtitle':'Phbay Travel は易遊網・雄獅・可楽・東南・星晴・佳期・kkday・長汎とともに公式提携リストに掲載されています。',
    'hero.title':'Phbay Travel', 'hero.subtitle':'いつもと違う澎湖（ポンフー）の旅へ',
    'hero.tagline':'地元の深い体験 × ファミリー向け × 持続可能な海',
    'hero.btnTours':'おすすめツアーを見る', 'hero.btnContact':'今すぐ相談',
    'feat.1.title':'地元密着の深い旅', 'feat.1.desc':'地元の人が案内する澎湖。ガイドブックにない秘境と物語をご案内します。',
    'feat.2.title':'ファミリーに優しい設計', 'feat.2.desc':'細部まで丁寧に手配し、ご家族みんなが安心して楽しめます。',
    'feat.3.title':'持続可能な海の理念', 'feat.3.desc':'澎湖の海の生態を守り、その美しさを次の世代へ残します。',
    'tours.title':'おすすめツアー', 'tours.subtitle':'あなただけの澎湖の旅をオーダーメイド',
    'cat.package':'パッケージツアー', 'cat.single':'単品ツアー',
    'tab.featured':'公式提携 特別ツアー', 'tab.2d1n':'1泊2日', 'tab.3d2n':'2泊3日', 'tab.4d3n':'3泊4日',
    'tab.north-sea':'北海エリア', 'tab.east-sea':'東海エリア', 'tab.south-sea':'南海エリア', 'tab.main-island':'本島エリア',
    'tours.empty':'ツアーは順次公開予定です。お楽しみに。',
    'about.badge':'年の澎湖旅行経験', 'about.title':'会社紹介',
    'about.p1':'Phbay Travel は澎湖の地元密着型の深い旅を中心とした旅行会社です。旅は写真を撮るだけでなく、心を解き放つ大切な時間だと考えています。',
    'about.p2':'私たちはファミリー旅行・海の体験・持続可能な観光に注力。すべての行程を地元ガイドが自ら企画し、一般の観光客が見られない澎湖へご案内します。',
    'about.p3':'シュノーケリング、SUP、干潟の生態から望安のアオウミガメ保護まで、この青い宝島を最も深く体験していただきます。',
    'about.stat1':'ご利用のお客様', 'about.stat2':'厳選ツアー', 'about.stat3':'満足度',
    'quiz.title':'あなたにぴったりの澎湖ツアーを見つけよう', 'quiz.subtitle':'4つの質問・30秒・最適なプランをご提案',
    'contact.title':'お問い合わせ', 'contact.subtitle':'ご質問やツアーの詳細など、下記よりお気軽にご連絡ください。',
    'contact.methods':'連絡方法', 'contact.lineLabel':'公式LINE', 'contact.phoneLabel':'電話', 'contact.emailLabel':'メール',
    'contact.hours':'営業時間：月〜金 08:30〜17:30<br>（土日・祝日休業）',
    'form.heading':'オンライン問い合わせフォーム',
    'form.name':'お名前', 'form.namePh':'お名前を入力',
    'form.phone':'電話番号', 'form.phonePh':'例：0912-345-678',
    'form.dateStart':'出発予定日', 'form.dateEnd':'帰着予定日',
    'form.people':'参加人数', 'form.peoplePh':'人数を選択',
    'form.budget':'お一人あたり予算', 'form.budgetPh':'予算帯を選択',
    'form.transport':'往復交通手段', 'form.byPlane':'飛行機', 'form.byBoat':'フェリー',
    'form.departure':'出発地', 'form.departurePh':'先に交通手段を選択',
    'form.tourInterest':'興味のあるツアー', 'form.tourHint':'（選ぶと出発日を指定できます）', 'form.tourPh':'ツアーを選択（任意）',
    'form.slot':'出発日を選択', 'form.notes':'備考・特別なご要望', 'form.notesPh':'例：ベビーカー、ベジタリアン、誕生日の手配など...',
    'form.submit':'問い合わせを送信',
    'form.successDefault':'お問い合わせを送信しました！1営業日以内にご連絡いたします。',
    'form.successLine2':'LINE <strong>@phbay2018</strong> を追加いただくとより早くご返信できます。',
    'banner.consult':'今すぐ相談',
    'footer.quickLinks':'クイックリンク', 'footer.contactInfo':'連絡先',
    'footer.owner':'代表者：唐瑋汝', 'footer.hours':'月〜金 08:30〜17:30'
  },

  /* ─────────── 한국어 ─────────── */
  ko: {
    'nav.home':'홈', 'nav.tours':'투어', 'nav.quiz':'여행 진단', 'nav.about':'회사 소개', 'nav.faq':'자주 묻는 질문', 'nav.blog':'블로그', 'nav.contact':'문의하기',
    'nav.preorder':'사전 예약', 'nav.neihai':'내해 크루즈', 'nav.festival':'음악 축제', 'nav.travel':'여행 정보', 'nav.tides':'조석 예보', 'nav.articles':'여행 아티클', 'nav.reviews':'여행 후기', 'nav.contactInfo':'연락처',
    'slide.cta':'투어 문의하기',
    'partner.title':'2026 펑후 추풍 음악조명축제 공식 제휴 여행사','partner.subtitle':'Phbay Travel은 ezTravel·라이언트래블·콜라투어·SET투어 등과 함께 공식 제휴 명단에 등재되어 있습니다.',
    'hero.title':'Phbay Travel', 'hero.subtitle':'색다른 펑후 여행을 만나보세요',
    'hero.tagline':'현지 심층 체험 × 가족 친화 × 지속가능한 바다',
    'hero.btnTours':'추천 투어 보기', 'hero.btnContact':'지금 문의',
    'feat.1.title':'현지 심층 여행', 'feat.1.desc':'현지인이 안내하는 펑후. 가이드북에 없는 숨은 명소와 이야기를 만나보세요.',
    'feat.2.title':'가족 친화 설계', 'feat.2.desc':'모든 디테일을 세심하게 준비해 온 가족이 안심하고 즐길 수 있습니다.',
    'feat.3.title':'지속가능한 바다', 'feat.3.desc':'펑후의 해양 생태를 보호하여 그 아름다움을 다음 세대에 남깁니다.',
    'tours.title':'추천 투어', 'tours.subtitle':'당신만을 위한 펑후 여행을 맞춤 설계',
    'cat.package':'패키지 투어', 'cat.single':'단품 투어',
    'tab.featured':'공식 제휴 특별 투어', 'tab.2d1n':'1박 2일', 'tab.3d2n':'2박 3일', 'tab.4d3n':'3박 4일',
    'tab.north-sea':'북해 해역', 'tab.east-sea':'동해 해역', 'tab.south-sea':'남해 해역', 'tab.main-island':'본섬 해역',
    'tours.empty':'투어가 순차적으로 공개될 예정입니다. 기대해 주세요.',
    'about.badge':'년 펑후 여행 경력', 'about.title':'회사 소개',
    'about.p1':'Phbay Travel은 펑후 현지 심층 여행을 핵심으로 하는 여행사입니다. 여행은 단순한 인증샷이 아니라 마음을 쉬게 하는 소중한 시간이라고 믿습니다.',
    'about.p2':'저희는 가족 여행, 해양 체험, 지속가능한 관광에 집중합니다. 모든 일정을 현지 가이드가 직접 기획해 일반 관광객이 보지 못하는 펑후로 안내합니다.',
    'about.p3':'스노클링, SUP, 갯벌 생태부터 왕안의 푸른바다거북 보호까지, 이 푸른 보물섬을 가장 깊이 있게 경험하도록 도와드립니다.',
    'about.stat1':'이용 고객', 'about.stat2':'엄선 투어', 'about.stat3':'만족도',
    'quiz.title':'나에게 딱 맞는 펑후 투어 찾기', 'quiz.subtitle':'4가지 질문 · 30초 · 가장 적합한 여행 플랜 추천',
    'contact.title':'문의하기', 'contact.subtitle':'궁금한 점이나 투어 정보가 필요하시면 아래로 언제든 연락주세요.',
    'contact.methods':'연락 방법', 'contact.lineLabel':'공식 LINE', 'contact.phoneLabel':'전화', 'contact.emailLabel':'이메일',
    'contact.hours':'운영시간: 월~금 08:30~17:30<br>(주말 및 공휴일 휴무)',
    'form.heading':'온라인 문의 양식',
    'form.name':'이름', 'form.namePh':'이름을 입력하세요',
    'form.phone':'연락처', 'form.phonePh':'예: 0912-345-678',
    'form.dateStart':'출발 예정일', 'form.dateEnd':'귀국 예정일',
    'form.people':'여행 인원', 'form.peoplePh':'인원 선택',
    'form.budget':'1인당 예산', 'form.budgetPh':'예산 범위 선택',
    'form.transport':'왕복 교통수단', 'form.byPlane':'비행기', 'form.byBoat':'페리',
    'form.departure':'출발지', 'form.departurePh':'교통수단을 먼저 선택',
    'form.tourInterest':'관심 투어', 'form.tourHint':'(선택하면 출발일 지정 가능)', 'form.tourPh':'투어 선택 (선택사항)',
    'form.slot':'출발일 선택', 'form.notes':'비고 / 특별 요청', 'form.notesPh':'예: 유모차, 채식, 생일 준비 등...',
    'form.submit':'문의 보내기',
    'form.successDefault':'문의가 전송되었습니다! 1영업일 이내에 연락드리겠습니다.',
    'form.successLine2':'LINE <strong>@phbay2018</strong>을 추가하시면 더 빠르게 답변드립니다.',
    'banner.consult':'지금 문의',
    'footer.quickLinks':'바로가기', 'footer.contactInfo':'연락처',
    'footer.owner':'대표: 唐瑋汝', 'footer.hours':'월~금 08:30~17:30'
  },

  /* ─────────── 简体中文 ─────────── */
  'zh-cn': {
    'nav.home':'首页', 'nav.tours':'行程介绍', 'nav.quiz':'行程测验', 'nav.about':'关于我们', 'nav.faq':'常见问题', 'nav.blog':'博客', 'nav.contact':'联系我们',
    'nav.preorder':'预购行程', 'nav.neihai':'内海行程', 'nav.festival':'追风音乐节', 'nav.travel':'旅游大小事', 'nav.tides':'潮汐查询系统', 'nav.articles':'旅游文章分享', 'nav.reviews':'旅客评价', 'nav.contactInfo':'联系资讯',
    'slide.cta':'咨询搭配行程',
    'partner.title':'2026 澎湖追风音乐灯光节 官方合作旅行社','partner.subtitle':'潮旅国际与易游网、雄狮、可乐、东南、星晴、佳期、kkday、长汎并列官方授权名单',
    'hero.title':'潮旅国际旅行社', 'hero.subtitle':'带你玩出不一样的澎湖旅行',
    'hero.tagline':'在地深度 × 亲子友善 × 永续海洋',
    'hero.btnTours':'查看推荐行程', 'hero.btnContact':'立即咨询',
    'feat.1.title':'在地深度旅游', 'feat.1.desc':'澎湖人带你玩澎湖，走访不为人知的秘境与故事。',
    'feat.2.title':'亲子友善设计', 'feat.2.desc':'细心安排每个细节，让全家大小都能安心享受。',
    'feat.3.title':'永续海洋理念', 'feat.3.desc':'爱护澎湖海洋生态，把美丽留给下一代。',
    'tours.title':'精选行程', 'tours.subtitle':'量身打造每一趟澎湖旅程',
    'cat.package':'套装行程', 'cat.single':'单一行程',
    'tab.featured':'官方合作特色行程', 'tab.2d1n':'两天一夜', 'tab.3d2n':'三天两夜', 'tab.4d3n':'四天三夜',
    'tab.north-sea':'北海海域', 'tab.east-sea':'东海海域', 'tab.south-sea':'南海海域', 'tab.main-island':'本岛海域',
    'tours.empty':'行程陆续上架中，敬请期待。',
    'about.badge':'年澎湖旅游经验', 'about.title':'关于我们',
    'about.p1':'潮旅国际旅行社是一家以澎湖在地深度旅游为核心的旅行社，我们相信旅行不只是打卡，而是一段让心灵留白的美好时光。',
    'about.p2':'我们专注于亲子旅行、海洋体验与永续旅游，每一条行程都由在地向导亲自规划，走进一般游客看不到的澎湖风情。',
    'about.p3':'从浮潜、SUP、潮间带生态到望安绿蠵龟保育，我们带你用最深刻的方式，认识这片蓝色宝岛。',
    'about.stat1':'服务旅客', 'about.stat2':'精选行程', 'about.stat3':'满意度',
    'quiz.title':'找到你的专属澎湖行程', 'quiz.subtitle':'4 个问题・30 秒・帮你找出最适合的旅游方案',
    'contact.title':'联系我们', 'contact.subtitle':'有任何问题或想了解更多行程，欢迎透过以下方式联系。',
    'contact.methods':'联系方式', 'contact.lineLabel':'LINE 官方咨询', 'contact.phoneLabel':'电话咨询', 'contact.emailLabel':'Email 信箱',
    'contact.hours':'服务时间：周一至周五 08:30–17:30<br>（周六、日及国定假日休假）',
    'form.heading':'在线咨询表单',
    'form.name':'姓名', 'form.namePh':'请输入您的姓名',
    'form.phone':'联系电话', 'form.phonePh':'例：0912-345-678',
    'form.dateStart':'预计出发日', 'form.dateEnd':'预计回程日',
    'form.people':'旅游人数', 'form.peoplePh':'请选择人数',
    'form.budget':'每人预算', 'form.budgetPh':'请选择预算范围',
    'form.transport':'往返交通方式', 'form.byPlane':'搭飞机', 'form.byBoat':'搭船',
    'form.departure':'出发地', 'form.departurePh':'请先选择交通方式',
    'form.tourInterest':'感兴趣的行程', 'form.tourHint':'（选择后可指定出发梯次）', 'form.tourPh':'请选择行程（可不填）',
    'form.slot':'选择出发梯次', 'form.notes':'备注 / 特殊需求', 'form.notesPh':'例：有婴儿车、素食需求、庆生安排等...',
    'form.submit':'送出咨询',
    'form.successDefault':'咨询已送出！我们将于一个工作日内与您联系。',
    'form.successLine2':'也可直接加 LINE：<strong>@phbay2018</strong> 获得更快速的回复。',
    'banner.consult':'立即咨询',
    'footer.quickLinks':'快速链接', 'footer.contactInfo':'联系信息',
    'footer.owner':'负责人：唐玮汝', 'footer.hours':'周一至周五 08:30–17:30'
  }
};

/* ── 初始化：記錄原始內容 ── */
function _i18nCapture() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el._i18nOrig = el.innerHTML;
    const f = el.firstElementChild;
    el._i18nIcon = (f && f.tagName === 'I') ? f.outerHTML + ' ' : '';
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => { el._i18nOrigHtml = el.innerHTML; });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el._i18nOrigPh = el.getAttribute('placeholder') || ''; });
}

/* ── 套用語言 ── */
function setLang(lang) {
  const dict = DICT[lang] || {};
  const isDefault = (lang === 'zh-tw');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const t = dict[el.getAttribute('data-i18n')];
    el.innerHTML = (isDefault || !t) ? el._i18nOrig : (el._i18nIcon + t);
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const t = dict[el.getAttribute('data-i18n-html')];
    el.innerHTML = (isDefault || !t) ? el._i18nOrigHtml : t;
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const t = dict[el.getAttribute('data-i18n-ph')];
    el.setAttribute('placeholder', (isDefault || !t) ? el._i18nOrigPh : t);
  });

  document.documentElement.lang = LANG_HTML[lang] || 'zh-TW';
  window.__lang = lang;
  try { localStorage.setItem('phbay_lang', lang); } catch (e) {}
  const cur = document.getElementById('lang-current');
  if (cur) cur.textContent = LANG_NAMES[lang] || '中文';
  // 通知動態內容（行程卡片等）依語言重新渲染
  if (typeof window.onLangChange === 'function') window.onLangChange(lang);
}
window.setLang = setLang;
window.__lang = 'zh-tw';

/* ── 切換選單與啟動 ── */
document.addEventListener('DOMContentLoaded', () => {
  _i18nCapture();

  const btn  = document.getElementById('lang-btn');
  const menu = document.getElementById('lang-menu');
  if (btn && menu) {
    btn.addEventListener('click', e => { e.stopPropagation(); menu.classList.toggle('open'); });
    menu.querySelectorAll('button[data-lang]').forEach(b => {
      b.addEventListener('click', () => { setLang(b.getAttribute('data-lang')); menu.classList.remove('open'); });
    });
    document.addEventListener('click', () => menu.classList.remove('open'));
  }

  // 還原上次選擇的語言
  let saved = 'zh-tw';
  try { saved = localStorage.getItem('phbay_lang') || 'zh-tw'; } catch (e) {}
  if (saved !== 'zh-tw') setLang(saved);
  else { const cur = document.getElementById('lang-current'); if (cur) cur.textContent = '中文'; }
});
