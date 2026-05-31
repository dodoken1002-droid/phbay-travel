/* ═══════════════════════════════════════════════
   潮旅國際旅行社 - JavaScript
   功能：導覽列捲動效果、Tab 切換、Modal、表單、回到頂部
════════════════════════════════════════════════ */

// ─── 等 DOM 載入完成後執行 ───
document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTabs();
  initContactForm();
  initScrollEffects();
  loadTours();
  initQuiz();
  initCarousel();
  // Footer 版權年份自動更新
  const yr = document.getElementById('footer-year');
  if (yr) yr.textContent = new Date().getFullYear();
});

/* ═══════════════════════════════════════════════
   導覽列：捲動陰影 + 手機漢堡選單
════════════════════════════════════════════════ */
function initNavbar() {
  const navbar   = document.getElementById('navbar');
  const toggle   = document.getElementById('nav-toggle');
  const navLinks = document.getElementById('nav-links');
  const links    = navLinks.querySelectorAll('a');

  // 捲動時加深陰影
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 30);
  }, { passive: true });

  // 漢堡選單開關
  toggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    // 更新 aria 狀態
    const isOpen = navLinks.classList.contains('open');
    toggle.setAttribute('aria-expanded', isOpen);
  });

  // 點擊連結後收起選單
  links.forEach(link => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('open');
    });
  });

  // 點擊選單外側收起
  document.addEventListener('click', (e) => {
    if (!navbar.contains(e.target)) {
      navLinks.classList.remove('open');
    }
  });
}

/* ═══════════════════════════════════════════════
   行程 Tab 切換
   如需新增 Tab，只要在 HTML 對應加上
   tab-btn[data-tab="xxx"] 與 tab-panel[data-panel="xxx"]
════════════════════════════════════════════════ */
function initTabs() {
  const tabBtns   = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;

      // 移除全部 active
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      // 加上目標 active
      btn.classList.add('active');
      const panel = document.querySelector(`.tab-panel[data-panel="${target}"]`);
      if (panel) panel.classList.add('active');
    });
  });
}

/* ═══════════════════════════════════════════════
   行程詳情 Modal
   用法：openModal('tour1') / closeModal()
   若要修改每個 Modal 內容，直接修改 HTML 中
   id="modal-tour1" 等對應區塊
════════════════════════════════════════════════ */
function openModal(tourId) {
  const overlay = document.getElementById('modal-overlay');
  const modal   = document.getElementById(`modal-${tourId}`);
  if (!modal) return;

  overlay.classList.add('active');
  modal.classList.add('active');
  document.body.style.overflow = 'hidden'; // 防止背景捲動
}

function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  const modals  = document.querySelectorAll('.modal');

  overlay.classList.remove('active');
  modals.forEach(m => m.classList.remove('active'));
  document.body.style.overflow = '';
}

// ESC 鍵關閉 Modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// 讓函式可以被 HTML onclick 呼叫（全域）
window.openModal  = openModal;
window.closeModal = closeModal;

/* ═══════════════════════════════════════════════
   聯絡表單處理
   目前為前端模擬送出（顯示成功訊息）
   若要串接後端，將 handleFormSubmit 改為
   fetch('/api/contact', { method:'POST', body: formData })
════════════════════════════════════════════════ */
const FLIGHT_CITIES = ['台北松山機場', '台中清泉崗機場', '嘉義水上機場', '台南仁德機場', '高雄小港機場'];
const BOAT_CITIES   = ['嘉義布袋港', '高雄鼓山一號碼頭'];

function toggleDeparture(transport) {
  const sel = document.getElementById('departure');
  if (!sel) return;
  sel.innerHTML = '<option value="">請選擇出發地</option>';
  const cities = transport === '飛機' ? FLIGHT_CITIES : BOAT_CITIES;
  cities.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    sel.appendChild(opt);
  });
}
window.toggleDeparture = toggleDeparture;

function initContactForm() {
  const form    = document.getElementById('contact-form');
  const success = document.getElementById('form-success');
  if (!form) return;

  // 日期區間：回程不能早於出發日
  const startInput = document.getElementById('travel-date-start');
  const endInput   = document.getElementById('travel-date-end');
  if (startInput && endInput) {
    startInput.addEventListener('change', () => {
      endInput.min = startInput.value;
      if (endInput.value && endInput.value < startInput.value) endInput.value = '';
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (!data.name || !data.phone || !data.travel_date || !data.travel_date_end || !data.people || !data.transport) {
      showFormError('請填寫所有必填欄位（標示 * 的欄位）');
      return;
    }

    // slot_id 轉為數字或移除
    if (data.slot_id) data.slot_id = parseInt(data.slot_id);
    else delete data.slot_id;

    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 傳送中...';

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      const result = await res.json();

      if (!res.ok || !result.ok) {
        throw new Error(result.error || '伺服器錯誤');
      }

      // 更新成功訊息（正團 vs 候補）
      const msgEl = document.getElementById('form-success-msg');
      if (msgEl) {
        msgEl.textContent = result.is_waitlist
          ? '✅ 候補登記成功！名額釋出時我們將優先通知您。'
          : '✅ 諮詢已送出！我們將於一個工作日內與您聯繫。';
      }

      form.style.display = 'none';
      success.style.display = 'block';
      success.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // GA4 轉換事件：記錄一筆諮詢成立
      if (typeof gtag === 'function') {
        gtag('event', 'generate_lead', {
          tour_interest: data.tour_interest || '(未選)',
          transport:     data.transport || '',
          people:        data.people || '',
          is_waitlist:   !!result.is_waitlist,
        });
      }

      // 重新整理該梯次名額顯示
      if (data.slot_id) refreshSlotStatus(data.slot_id);

    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 送出諮詢';
      showFormError(err.message || '送出失敗，請直接 LINE 或電話聯繫我們。');
    }
  });
}

// ─── 梯次名額：依行程載入 ────────────────────────────────
let _slotsCache = {};   // { tourId: [slot, ...] }

// 依資料庫行程動態填入「有興趣的行程」下拉
function populateTourInterest(tours) {
  const sel = document.getElementById('tour-interest');
  if (!sel) return;
  const otherOpt = document.getElementById('tour-interest-other');
  // 移除舊的動態 option（保留 placeholder 與「其他」）
  [...sel.querySelectorAll('option[data-dyn="1"]')].forEach(o => o.remove());
  tours.forEach(t => {
    const o = document.createElement('option');
    o.value = t.title;                 // 儲存行程名稱，後台直接顯示
    o.dataset.tourId = t.id;           // 供梯次連動使用
    o.dataset.dyn = '1';
    o.textContent = t.title;
    sel.insertBefore(o, otherOpt);     // 插在「其他」之前
  });
}

async function loadSlotOptions(selectEl) {
  const group  = document.getElementById('slot-group');
  const select = document.getElementById('slot-select');
  const hint   = document.getElementById('slot-status');
  if (!group || !select) return;

  // 讀取目前選取 option 上的 data-tour-id（由動態填入時帶入）
  const opt    = selectEl && selectEl.selectedOptions ? selectEl.selectedOptions[0] : null;
  const tourId = opt ? opt.dataset.tourId : null;

  if (!tourId) { group.style.display = 'none'; return; }

  group.style.display = 'block';
  select.innerHTML = '<option value="">載入中...</option>';
  if (hint) hint.textContent = '';

  try {
    const res  = await fetch(`/api/slots?tour_id=${tourId}`);
    const json = await res.json();
    const slots = (json.slots || []).filter(s => s.is_active);
    _slotsCache[tourId] = slots;

    if (!slots.length) {
      select.innerHTML = '<option value="">（此行程尚無開放梯次）</option>';
      return;
    }

    select.innerHTML = '<option value="">請選擇出發梯次（可不填）</option>';
    slots.forEach(s => {
      const label = slotStatusLabel(s);
      const opt   = document.createElement('option');
      opt.value   = s.id;
      opt.textContent = `${s.date_label}　${label}`;
      if (s.status === 'full_wl_full') opt.disabled = true;
      select.appendChild(opt);
    });
  } catch (e) {
    select.innerHTML = '<option value="">無法載入梯次，請在備註填寫日期</option>';
  }
}
window.loadSlotOptions = loadSlotOptions;

function slotStatusLabel(s) {
  if (s.status === 'full_wl_full') return '⛔ 已額滿';
  if (s.status === 'waitlist')     return `🔴 候補 ${s.wl_remaining} 位`;
  if (s.status === 'low')          return `🟡 剩 ${s.remaining} 位`;
  return `🟢 剩 ${s.remaining} 位`;
}

// 表單送出後重新抓單一梯次狀態並更新 select option 文字
async function refreshSlotStatus(slotId) {
  try {
    const res   = await fetch('/api/slots');
    const json  = await res.json();
    const slot  = (json.slots || []).find(s => s.id === slotId);
    if (!slot) return;
    const opt = document.querySelector(`#slot-select option[value="${slotId}"]`);
    if (opt) opt.textContent = `${slot.date_label}　${slotStatusLabel(slot)}`;
  } catch (_) {}
}

function showFormError(msg) {
  // 移除舊的錯誤訊息
  const old = document.querySelector('.form-error-msg');
  if (old) old.remove();

  const err = document.createElement('p');
  err.className = 'form-error-msg';
  err.style.cssText = 'color:#e53e3e;font-size:0.88rem;padding:8px 12px;background:#fff5f5;border-radius:8px;border-left:4px solid #e53e3e;';
  err.textContent = msg;

  const form = document.getElementById('contact-form');
  form.prepend(err);

  // 3 秒後自動消失
  setTimeout(() => err.remove(), 3500);
}

/* ═══════════════════════════════════════════════
   捲動效果：回到頂部按鈕顯示 / 隱藏
════════════════════════════════════════════════ */
function initScrollEffects() {
  const backToTop = document.getElementById('back-to-top');

  window.addEventListener('scroll', () => {
    backToTop.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.scrollToTop = scrollToTop;

/* ═══════════════════════════════════════════════
   動態行程載入
════════════════════════════════════════════════ */
// 全站梯次快取 { tourId: [slot,...] }
let _allSlots = {};

async function loadTours() {
  try {
    // 同時抓行程與梯次名額
    const [toursRes, slotsRes] = await Promise.all([
      fetch('/api/tours'),
      fetch('/api/slots')
    ]);
    if (!toursRes.ok) throw new Error('API error');
    const json    = await toursRes.json();
    const grouped = json.tours || {};

    if (slotsRes.ok) {
      const sJson = await slotsRes.json();
      (sJson.slots || []).forEach(s => {
        if (!_allSlots[s.tour_id]) _allSlots[s.tour_id] = [];
        _allSlots[s.tour_id].push(s);
      });
    }

    document.querySelectorAll('.tours-loading').forEach(el => el.remove());

    ['featured', '2d1n', '3d2n', '4d3n'].forEach(tab => {
      const grid = document.getElementById(`grid-${tab}`);
      if (!grid) return;
      const tours = grouped[tab] || [];
      tours.forEach(tour => {
        grid.appendChild(renderTourCard(tour));
        renderTourModal(tour);
      });
    });

    // 用唯一行程清單填入諮詢表單下拉（不再寫死 ID）
    const seen = new Set();
    const uniqueTours = [];
    Object.values(grouped).flat().forEach(t => {
      if (!seen.has(t.id)) { seen.add(t.id); uniqueTours.push(t); }
    });
    uniqueTours.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    populateTourInterest(uniqueTours);
  } catch (err) {
    console.error('loadTours 失敗:', err);
    document.querySelectorAll('.tours-loading').forEach(el => {
      el.innerHTML = '<i class="fas fa-exclamation-circle"></i> 行程載入失敗，請稍後再試。';
    });
  }
}

function renderTourCard(tour) {
  const card = document.createElement('div');
  const isHero = tour.is_hero;
  card.className = 'tour-card' + (isHero ? ' tour-card--hero' : '');

  const badgeHtml = tour.badge_text
    ? `<div class="tour-badge ${tour.badge_class || ''}">${tour.badge_text}</div>` : '';

  const imgHtml = tour.image_url
    ? `<img src="${tour.image_url}" alt="${tour.title}" loading="lazy" />`
    : `<img src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80" alt="${tour.title}" loading="lazy" />`;

  // 多出發地價格列（DB 格式：{label, value}）
  const pricesHtml = Array.isArray(tour.prices) && tour.prices.length
    ? `<div class="tour-prices">${tour.prices.map(p =>
        `<div class="price-row"><span class="price-from">${p.label ?? p.from ?? ''}</span><span class="price-val">${p.value ?? p.price ?? ''}</span></div>`
      ).join('')}</div>` : '';

  const priceMetaHtml = (!tour.prices || !tour.prices.length) && tour.price_display
    ? `<span class="meta-item price"><i class="fas fa-tag"></i> ${tour.price_display}</span>` : '';

  const btnClass = isHero ? 'btn btn-card btn-card--hero' : 'btn btn-card';

  // 梯次名額摘要（顯示全部梯次）
  const slots = _allSlots[tour.id] || [];
  let slotHtml = '';
  if (slots.length) {
    const chipsHtml = slots.map(s => {
      if (s.status === 'full_wl_full')
        return `<span class="slot-chip chip-full">⛔ ${s.date_label}</span>`;
      if (s.status === 'waitlist')
        return `<span class="slot-chip chip-waitlist">🔴 ${s.date_label} 候補${s.wl_remaining}位</span>`;
      if (s.status === 'low')
        return `<span class="slot-chip chip-low">🟡 ${s.date_label} 剩${s.remaining}位</span>`;
      return `<span class="slot-chip chip-ok">🟢 ${s.date_label} 剩${s.remaining}位</span>`;
    }).join('');
    slotHtml = `<div class="slot-summary">${chipsHtml}</div>`;
  }

  card.innerHTML = `
    ${badgeHtml}
    <div class="tour-image">
      ${imgHtml}
      <div class="tour-overlay">
        <span class="tour-days"><i class="fas fa-clock"></i> ${tour.duration || ''}</span>
      </div>
    </div>
    <div class="tour-body">
      ${isHero ? '<div class="tour-year-badge">2026</div>' : ''}
      <h3 class="tour-title">${tour.title}</h3>
      <p class="tour-desc">${tour.description || ''}</p>
      ${slotHtml}
      ${pricesHtml}
      <div class="tour-meta">
        ${tour.suitable_for ? `<span class="meta-item"><i class="fas fa-users"></i> ${tour.suitable_for}</span>` : ''}
        ${tour.duration ? `<span class="meta-item"><i class="fas fa-calendar"></i> ${tour.duration}</span>` : ''}
        ${priceMetaHtml}
      </div>
      <button class="${btnClass}" onclick="openModal('db-${tour.id}')">
        查看詳情 <i class="fas fa-arrow-right"></i>
      </button>
    </div>`;
  return card;
}

function renderTourModal(tour) {
  const md = tour.modal_data || {};
  const container = document.getElementById('modal-container');

  const modalEl = document.createElement('div');
  modalEl.className = 'modal' + (tour.is_hero ? ' modal--turtle' : '');
  modalEl.id = `modal-db-${tour.id}`;

  // Prices table or tag
  let priceSection = '';
  if (Array.isArray(tour.prices) && tour.prices.length) {
    priceSection = `<h4><i class="fas fa-tag"></i> 出發地 × 價格</h4>
      <table class="price-table">
        ${tour.prices.map(p => `<tr><td>${p.label ?? p.from ?? ''}</td><td class="price-highlight">${p.value ?? p.price ?? ''}</td></tr>`).join('')}
      </table>`;
  } else if (tour.price_display) {
    priceSection = `<h4><i class="fas fa-tag"></i> 價格</h4><p>${tour.price_display}</p>`;
  }

  // Dates
  const datesHtml = md.dates && md.dates.length
    ? `<h4><i class="fas fa-calendar-alt"></i> 出發日期</h4>
       <div class="date-chips">${md.dates.map(d => `<span class="date-chip">${d}</span>`).join('')}</div>` : '';

  // Highlights
  const hlHtml = md.highlights && md.highlights.length
    ? `<h4><i class="fas fa-star"></i> 行程亮點</h4>
       <ul>${md.highlights.map(h => `<li>${h}</li>`).join('')}</ul>` : '';

  // Day by day
  let daysHtml = '';
  if (md.days && md.days.length) {
    daysHtml = `<h4><i class="fas fa-map-signs"></i> 行程規劃</h4><div class="day-blocks">
      ${md.days.map(d => `
        <div class="day-block">
          <div class="day-label">${d.label}</div>
          <div class="day-content">
            <strong>${d.title}</strong>
            <ul>${(d.items || []).map(i => `<li>${i}</li>`).join('')}</ul>
          </div>
        </div>`).join('')}
    </div>`;
  }

  // Includes / notes
  const includesHtml = md.includes ? `<h4><i class="fas fa-check-circle"></i> 費用包含</h4><p>${md.includes}</p>` : '';
  const notesHtml    = md.notes   ? `<h4><i class="fas fa-exclamation-circle"></i> 注意事項</h4><p>${md.notes}</p>` : '';

  const headerClass = tour.is_hero ? 'modal-header modal-header--turtle' : 'modal-header';
  const headerInner = tour.is_hero
    ? `<div class="modal-header-content">
        <span class="modal-year">2026</span>
        <h2>${tour.title}</h2>
        <span class="modal-tag">${tour.duration || ''} × 望安深度 × 海島體驗 × 永續旅遊</span>
       </div>`
    : `<h2>${tour.title}</h2>
       <span class="modal-tag">${tour.duration || ''}${tour.price_display ? '｜' + tour.price_display : ''}</span>`;

  modalEl.innerHTML = `
    <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
    <div class="${headerClass}">${headerInner}</div>
    <div class="modal-body">
      ${datesHtml}
      ${priceSection}
      ${hlHtml}
      ${daysHtml}
      ${includesHtml}
      ${notesHtml}
      <a href="#contact" class="btn btn-primary" onclick="closeModal()">
        <i class="fas fa-comment-dots"></i> 我要諮詢這個行程
      </a>
    </div>`;

  container.appendChild(modalEl);
}

/* ═══════════════════════════════════════════════
   行程心理測驗
════════════════════════════════════════════════ */
const QUIZ_QUESTIONS = [
  {
    icon: '🧳',
    q: '這次旅遊，你和誰一起來澎湖？',
    options: [
      { icon:'💑', text:'情侶 / 好朋友', sub:'兩人同行說走就走',   scores:{ turtle:2, classic:2, sup:1 } },
      { icon:'👨‍👩‍👧‍👦', text:'親子 / 全家出遊', sub:'帶著孩子一起探索',  scores:{ family:4 } },
      { icon:'🎒', text:'一個人',         sub:'自由自在的獨旅',   scores:{ eco:3, sup:2 } },
      { icon:'🎉', text:'一群朋友 / 揪團', sub:'人多更熱鬧',      scores:{ classic:3, turtle:1, sup:2 } },
    ]
  },
  {
    icon: '🌊',
    q: '最想在澎湖體驗哪一件事？',
    options: [
      { icon:'🤿', text:'浮潛、SUP 水上活動',   sub:'直接跳進海裡玩',        scores:{ sup:4, turtle:1 } },
      { icon:'🐢', text:'海龜保育 × 生態探索', sub:'深入自然、有意義的旅行', scores:{ turtle:4, eco:3 } },
      { icon:'🏡', text:'古厝文化 × 在地美食', sub:'慢遊、感受澎湖生活',     scores:{ classic:3, turtle:2 } },
      { icon:'🌅', text:'拍美照、看夕陽',       sub:'輕鬆放空最重要',         scores:{ classic:2, family:2 } },
    ]
  },
  {
    icon: '📅',
    q: '這次打算在澎湖待幾天？',
    options: [
      { icon:'⚡', text:'2 天 1 夜',  sub:'週末快閃，說走就走',  scores:{ sup:4 } },
      { icon:'☀️', text:'3 天 2 夜',  sub:'剛剛好，不趕又充實', scores:{ classic:3, family:3 } },
      { icon:'🌊', text:'4 天 3 夜',  sub:'深度慢遊，玩個夠',   scores:{ turtle:4, eco:3 } },
      { icon:'🤔', text:'還沒決定',   sub:'看推薦再決定',        scores:{ classic:1, turtle:1, family:1 } },
    ]
  },
  {
    icon: '💰',
    q: '每人預算大概是？',
    options: [
      { icon:'💵', text:'NT$ 7,000 以下',   sub:'輕鬆玩就好',         scores:{ sup:4 } },
      { icon:'💳', text:'NT$ 7,000–10,000', sub:'合理預算，體驗豐富',  scores:{ classic:3, family:3, sup:1 } },
      { icon:'🌟', text:'NT$ 10,000–15,000',sub:'值得的體驗不計較',    scores:{ turtle:4, classic:1 } },
      { icon:'👑', text:'不設限',            sub:'最棒的體驗最重要',    scores:{ eco:4, turtle:2 } },
    ]
  },
];

const QUIZ_RESULTS = {
  sup: {
    type: '海洋冒險家 🤿',
    desc: '你熱愛刺激、說走就走，短假期也要玩得盡興！站上 SUP 衝浪板、浮潛看珊瑚礁，用最直接的方式感受澎湖海洋的魅力。',
    tour: { name:'SUP × 浮潛 × 海洋體驗', duration:'2天1夜', price:'NT$ 5,800 起', img:'https://images.unsplash.com/photo-1506953823976-52e1fdc0149a?w=400&q=80', interest:'sup2d' },
  },
  classic: {
    type: '澎湖經典探索者 🌅',
    desc: '你喜歡豐富多元的旅遊體驗，奎壁山摩西分海、跨海大橋、七美雙心石滬……澎湖的經典美景一次都不想錯過！',
    tour: { name:'澎湖經典三日遊', duration:'3天2夜', price:'NT$ 8,800 起', img:'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80', interest:'classic3d' },
  },
  family: {
    type: '親子海島守護者 👨‍👩‍👧',
    desc: '家人的笑容是旅途中最美的風景！安全、溫馨又有趣的行程，讓孩子與海洋親密接觸，留下一家人最珍貴的回憶。',
    tour: { name:'親子海島體驗行程', duration:'3天2夜', price:'NT$ 9,500 起', img:'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=400&q=80', interest:'family3d' },
  },
  turtle: {
    type: '海龜慢旅實踐者 🐢',
    desc: '你重視旅遊的深度與意義，不只是走馬看花。跟著海龜走進望安的山與海，體驗永續旅遊的美好，這趟旅行將改變你對澎湖的想像！',
    tour: { name:'🐢 2026 跟著海龜漫旅', duration:'4天3夜', price:'NT$ 6,999 起', img:'https://images.unsplash.com/photo-1583212292454-1fe6229603b7?w=400&q=80', interest:'turtle4d' },
  },
  eco: {
    type: '永續生態旅行者 🌿',
    desc: '你是真正熱愛大自然、有深度的旅人。望安綠蠵龜保護區、花宅古厝聚落……離開澎湖時，你帶走的不只是美照，更是滿滿的感動與故事。',
    tour: { name:'望安永續生態旅行', duration:'4天3夜', price:'NT$ 12,800 起', img:'https://images.unsplash.com/photo-1500375592092-40eb2168fd21?w=400&q=80', interest:'eco4d' },
  },
};

let quizAnswers = [];

function initQuiz() {
  quizAnswers = [];
  renderQuizQuestion(0);
}
window.initQuiz = initQuiz;

function renderQuizQuestion(idx) {
  const wrap = document.getElementById('quiz-wrap');
  if (!wrap) return;
  const q = QUIZ_QUESTIONS[idx];
  const total = QUIZ_QUESTIONS.length;
  const pct = Math.round((idx / total) * 100);
  wrap.innerHTML = `
    <div class="quiz-progress">
      <div class="quiz-progress-bar"><div class="quiz-progress-fill" style="width:${pct}%"></div></div>
      <span class="quiz-step-label">第 ${idx + 1} / ${total} 題</span>
    </div>
    <div class="quiz-card">
      <span class="quiz-q-icon">${q.icon}</span>
      <div class="quiz-question">${q.q}</div>
      <div class="quiz-options">
        ${q.options.map((o, i) => `
          <div class="quiz-option" onclick="quizAnswer(${idx},${i})">
            <span class="opt-icon">${o.icon}</span>
            <span class="opt-text">${o.text}</span>
            <span class="opt-sub">${o.sub}</span>
          </div>`).join('')}
      </div>
    </div>`;
}

window.quizAnswer = function(qIdx, optIdx) {
  quizAnswers.push(QUIZ_QUESTIONS[qIdx].options[optIdx].scores);
  const next = qIdx + 1;
  if (next < QUIZ_QUESTIONS.length) {
    renderQuizQuestion(next);
  } else {
    renderQuizResult();
  }
};

function renderQuizResult() {
  const totals = { sup:0, classic:0, family:0, turtle:0, eco:0 };
  quizAnswers.forEach(s => Object.entries(s).forEach(([k,v]) => { totals[k] = (totals[k]||0) + v; }));
  const best = Object.entries(totals).sort((a,b) => b[1]-a[1])[0][0];
  const r = QUIZ_RESULTS[best];
  const wrap = document.getElementById('quiz-wrap');
  wrap.innerHTML = `
    <div class="quiz-card quiz-result">
      <div class="quiz-progress">
        <div class="quiz-progress-bar"><div class="quiz-progress-fill" style="width:100%"></div></div>
        <span class="quiz-step-label">✨ 結果揭曉！</span>
      </div>
      <span class="quiz-result-badge">你的旅遊類型</span>
      <div class="quiz-result-type">${r.type}</div>
      <p class="quiz-result-desc">${r.desc}</p>
      <div class="quiz-result-tour">
        <img src="${r.tour.img}" alt="${r.tour.name}" />
        <div class="quiz-result-tour-info">
          <div class="tour-recommend-label">✦ 推薦行程</div>
          <div class="tour-recommend-name">${r.tour.name}</div>
          <div class="tour-recommend-meta">
            <i class="fas fa-calendar"></i> ${r.tour.duration} &nbsp;｜&nbsp;
            <i class="fas fa-tag"></i> ${r.tour.price}
          </div>
        </div>
      </div>
      <div class="quiz-result-actions">
        <a href="#contact" class="btn btn-primary" onclick="prefillTour('${r.tour.interest}')">
          <i class="fas fa-comment-dots"></i> 立即諮詢這個行程
        </a>
        <button class="quiz-retry" onclick="initQuiz()">
          <i class="fas fa-redo"></i> 重新測驗
        </button>
      </div>
    </div>`;
}

function prefillTour(interest) {
  const sel = document.getElementById('tour-interest');
  if (sel && interest) sel.value = interest;
}
window.prefillTour = prefillTour;

/* ═══════════════════════════════════════════════
   首頁輪播
════════════════════════════════════════════════ */
let _carouselIdx   = 0;
let _carouselTotal = 0;
let _carouselTimer = null;

function initCarousel() {
  const track  = document.getElementById('carousel-track');
  const dotsEl = document.getElementById('carousel-dots');
  if (!track) return;

  _carouselTotal = track.children.length;

  // 建立圓點
  dotsEl.innerHTML = '';
  for (let i = 0; i < _carouselTotal; i++) {
    const d = document.createElement('button');
    d.className = 'carousel-dot' + (i === 0 ? ' active' : '');
    d.setAttribute('aria-label', `第 ${i+1} 張`);
    d.onclick = () => carouselGoTo(i);
    dotsEl.appendChild(d);
  }

  carouselGoTo(0);
  _carouselStartAuto();

  // 暫停自動播放（hover）
  const carousel = document.getElementById('main-carousel');
  carousel.addEventListener('mouseenter', _carouselStopAuto);
  carousel.addEventListener('mouseleave', _carouselStartAuto);

  // 觸控滑動支援
  let touchX = 0;
  carousel.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
  carousel.addEventListener('touchend',   e => {
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) carouselMove(dx < 0 ? 1 : -1);
  }, { passive: true });
}

function carouselGoTo(idx) {
  _carouselIdx = (idx + _carouselTotal) % _carouselTotal;
  document.getElementById('carousel-track').style.transform = `translateX(-${_carouselIdx * 100}%)`;
  document.querySelectorAll('.carousel-dot').forEach((d, i) => {
    d.classList.toggle('active', i === _carouselIdx);
  });
}

function carouselMove(dir) {
  carouselGoTo(_carouselIdx + dir);
  _carouselStopAuto();
  _carouselStartAuto();
}
window.carouselMove = carouselMove;

function _carouselStartAuto() {
  _carouselStopAuto();
  _carouselTimer = setInterval(() => carouselGoTo(_carouselIdx + 1), 5000);
}
function _carouselStopAuto() {
  if (_carouselTimer) { clearInterval(_carouselTimer); _carouselTimer = null; }
}

/* ─── 工具函式 ─── */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
