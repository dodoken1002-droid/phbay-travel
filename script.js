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
const FLIGHT_CITIES = ['台北松山', '台中', '高雄', '嘉義'];
const BOAT_CITIES   = ['嘉義布袋', '台中梧棲', '高雄'];

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

    // 收集表單資料
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // 基本驗證
    if (!data.name || !data.phone || !data.travel_date || !data.travel_date_end || !data.people || !data.transport) {
      showFormError('請填寫所有必填欄位（標示 * 的欄位）');
      return;
    }

    // 按鈕轉為 loading 狀態
    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 傳送中...';

    try {
      // 呼叫後端 API（Flask /api/contact）
      // 在本機開發時會打 http://localhost:5000/api/contact
      // 部署到 Railway 後自動使用同一網域，不需修改
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      const result = await res.json();

      if (!res.ok || !result.ok) {
        throw new Error(result.error || '伺服器錯誤');
      }

      form.style.display = 'none';
      success.style.display = 'block';
      success.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 送出諮詢';
      showFormError(err.message || '送出失敗，請直接 LINE 或電話聯繫我們。');
    }
  });
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
async function loadTours() {
  try {
    const res = await fetch('/api/tours');
    if (!res.ok) throw new Error('API error');
    const grouped = await res.json(); // { featured: [...], "2d1n": [...], ... }

    // 清除所有 loading 指示器
    document.querySelectorAll('.tours-loading').forEach(el => el.remove());

    // 清空並填充每個 tab 的 grid
    ['featured', '2d1n', '3d2n', '4d3n'].forEach(tab => {
      const grid = document.getElementById(`grid-${tab}`);
      if (!grid) return;
      const tours = grouped[tab] || [];
      tours.forEach(tour => {
        grid.appendChild(renderTourCard(tour));
        renderTourModal(tour);
      });
    });
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

  // 多出發地價格列
  const pricesHtml = Array.isArray(tour.prices) && tour.prices.length
    ? `<div class="tour-prices">${tour.prices.map(p =>
        `<div class="price-row"><span class="price-from">${p.from}</span><span class="price-val">${p.price}</span></div>`
      ).join('')}</div>` : '';

  const priceMetaHtml = (!tour.prices || !tour.prices.length) && tour.price_display
    ? `<span class="meta-item price"><i class="fas fa-tag"></i> ${tour.price_display}</span>` : '';

  const btnClass = isHero ? 'btn btn-card btn-card--hero' : 'btn btn-card';

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
        ${tour.prices.map(p => `<tr><td>${p.from}</td><td class="price-highlight">${p.price}</td></tr>`).join('')}
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
      ${priceSection}
      ${datesHtml}
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

/* ─── 工具函式 ─── */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
