/* ═══════════════════════════════════════════════
   潮旅國際旅行社 - JavaScript
   功能：導覽列捲動效果、Tab 切換、Modal、表單、回到頂部
════════════════════════════════════════════════ */

// ─── 等 DOM 載入完成後執行 ───
document.addEventListener('DOMContentLoaded', () => {
  captureAttribution();
  initNavbar();
  initTabs();
  initContactForm();
  initScrollEffects();
  loadTours();
  initQuiz();
  initCarousel();
  initMemberHome();
  // Footer 版權年份自動更新
  const yr = document.getElementById('footer-year');
  if (yr) yr.textContent = new Date().getFullYear();
});

async function initMemberHome() {
  const box = document.getElementById('member-home-status');
  if (!box) return;
  try {
    const response = await fetch('/api/member/me');
    if (!response.ok) return;
    const data = await response.json();
    if (!data.ok) return;
    box.textContent = '';
    const card = document.createElement('div');
    card.style.cssText = 'background:#fff;border-radius:16px;padding:18px 24px;box-shadow:0 8px 24px #0b537219';
    const title = document.createElement('strong');
    title.style.cssText = 'display:block;font-size:1.35rem;color:#1a6b9e';
    title.textContent = `${data.member.name}｜第 ${data.member.trip_count} 次・${data.member.level}`;
    const progress = document.createElement('span');
    progress.textContent = data.member.next_level
      ? `距「${data.member.next_level.name}」還差 ${data.member.next_level.remaining} 次`
      : '你已抵達百澎傳奇';
    card.append(title, progress); box.append(card);
  } catch (_) { /* 未登入或網路瞬斷時保留訪客版 */ }
}

/* P1 轉換歸因：同一次瀏覽保留首次 UTM 與入口，表單送出時一併存後台。 */
const ATTRIBUTION_KEY = 'phbay_attribution_v1';
function captureAttribution() {
  try {
    if (sessionStorage.getItem(ATTRIBUTION_KEY)) return;
    const q = new URLSearchParams(location.search);
    const data = {
      utm_source: q.get('utm_source') || '', utm_medium: q.get('utm_medium') || '',
      utm_campaign: q.get('utm_campaign') || '', utm_content: q.get('utm_content') || '',
      utm_term: q.get('utm_term') || '', landing_page: location.pathname + location.search,
      referrer: document.referrer || ''
    };
    sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(data));
  } catch (_) { /* 瀏覽器禁用 storage 時不影響主要流程 */ }
}
function getAttribution() {
  try { return JSON.parse(sessionStorage.getItem(ATTRIBUTION_KEY) || '{}'); }
  catch (_) { return {}; }
}

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

  // 行程介紹子選單：點套裝/單一 → 捲到行程區並切到對應分類
  navLinks.querySelectorAll('.nav-submenu a[data-cat]').forEach(a => {
    a.addEventListener('click', () => {
      const catBtn = document.querySelector(`.cat-btn[data-cat="${a.dataset.cat}"]`);
      if (catBtn) catBtn.click();   // 切換分類（沿用既有兩層切換邏輯）
    });
  });
}

/* ═══════════════════════════════════════════════
   行程 Tab 切換（兩層）
   上層分類：.cat-btn[data-cat] ↔ .tour-cat[data-cat-panel]
   下層子分頁：.tab-btn[data-tab] ↔ .tab-panel[data-panel]，
   子分頁切換只作用在所屬分類（.tour-cat）內，分類之間互不干擾。
════════════════════════════════════════════════ */
function initTabs() {
  // 上層分類切換
  const catBtns   = document.querySelectorAll('.cat-btn');
  const catPanels = document.querySelectorAll('.tour-cat');
  catBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.cat;
      catBtns.forEach(b => b.classList.remove('active'));
      catPanels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.querySelector(`.tour-cat[data-cat-panel="${target}"]`);
      if (panel) panel.classList.add('active');
    });
  });

  // 下層子分頁切換（限同一分類內）
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      const cat = btn.closest('.tour-cat') || document;
      cat.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      cat.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = cat.querySelector(`.tab-panel[data-panel="${target}"]`);
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

  // Meta Pixel：使用者主動開啟行程詳情才記錄內容瀏覽，不在頁面載入時觸發
  if (typeof fbq === 'function') {
    const modalTitle = modal.querySelector('h2, h3, .tour-title')?.textContent?.trim() || tourId;
    fbq('track', 'ViewContent', {
      content_name: modalTitle,
      content_type: 'product',
      content_category: '行程詳情'
    });
  }
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

/* 澎湖百旅會員：選「我已是潮旅會員」才顯示會員編號欄位 */
function toggleMemberNo(status) {
  const g = document.getElementById('member-no-group');
  if (!g) return;
  const show = status === '已是會員';
  g.style.display = show ? '' : 'none';
  if (!show) {
    const input = document.getElementById('member-no');
    if (input) input.value = '';
  }
}
window.toggleMemberNo = toggleMemberNo;

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
    data.utm = getAttribution();

    if (!data.name || !data.phone || !data.travel_date || !data.travel_date_end || !data.people || !data.transport) {
      showFormError('請填寫所有必填欄位（標示 * 的欄位）');
      return;
    }

    const contractBox = document.getElementById('contract-consent');
    if (contractBox && !contractBox.checked) {
      showFormError('請先閱讀並勾選同意《國內旅遊定型化契約》再送出。');
      return;
    }
    delete data.contract_consent; // 僅前端確認用，不送後端



    // slot_id 轉為數字或移除
    if (data.slot_id) data.slot_id = parseInt(data.slot_id);
    else delete data.slot_id;

    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 傳送中...';

    // 送出前先記一筆 attempt：與 generate_lead 相比即可看出失敗率，
    // 表單一壞當天就會在 GA4 顯示落差（2026-07 曾整月無聲失敗而未被發現）。
    if (typeof gtag === 'function') {
      gtag('event', 'contact_submit_attempt', {
        method:        'contact_form',
        tour_interest: data.tour_interest || '(未選)',
        transport:     data.transport || '',
        people:        data.people || '',
      });
    }

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      let result = {};
      try { result = await res.json(); } catch (_) { /* 非 JSON 回應（如 502） */ }

      if (!res.ok || !result.ok) {
        const e = new Error(result.error || `伺服器錯誤（HTTP ${res.status}）`);
        e.httpStatus = res.status;
        throw e;
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

      // GA4 / Meta Pixel 轉換事件：送出成功後才記錄一筆諮詢成立
      if (typeof gtag === 'function') {
        gtag('event', 'generate_lead', {
          method:        'contact_form',
          tour_interest: data.tour_interest || '(未選)',
          transport:     data.transport || '',
          people:        data.people || '',
          is_waitlist:   !!result.is_waitlist,
        });
      }
      if (typeof fbq === 'function') {
        fbq('track', 'Lead', {
          content_name: '諮詢表單',
          content_category: '行程諮詢'
        });
      }

      // 重新整理該梯次名額顯示
      if (data.slot_id) refreshSlotStatus(data.slot_id);

    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 送出諮詢';

      // 失敗一定要記事件，讓表單故障在 GA4 當天就看得出來
      if (typeof gtag === 'function') {
      gtag('event', 'contact_submit_failed', {
          method:         'contact_form',
          failure_type:  err.httpStatus ? 'server' : 'network',
          http_status:   err.httpStatus || 0,
          error_message: String(err.message || '').slice(0, 100),
          tour_interest: data.tour_interest || '(未選)',
        });
      }

      // 不要只丟一句錯誤讓客人離開——同時給出備援聯絡管道，把名單留住
      showFormFallback(err.message);
    }
  });
}

/* 送出失敗時顯示備援聯絡管道（常駐，不自動消失）。
   2026-07 諮詢表單無聲失敗一個多月，客人只看到一句錯誤就離開，名單直接流失。 */
function showFormFallback(reason) {
  const form = document.getElementById('contact-form');
  if (!form) return;
  document.querySelector('.form-fallback')?.remove();
  document.querySelector('.form-error-msg')?.remove();

  const t = (window.__lang && FORM_FALLBACK_TXT[window.__lang]) || FORM_FALLBACK_TXT['zh-tw'];
  const box = document.createElement('div');
  box.className = 'form-fallback';
  box.innerHTML = `
    <p class="form-fallback-title"><i class="fas fa-triangle-exclamation"></i> ${t.title}</p>
    <p class="form-fallback-desc">${t.desc}</p>
    <div class="form-fallback-btns">
      <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer"
         onclick="trackFallbackClick('line')"><i class="fab fa-line"></i> LINE</a>
      <a href="https://wa.me/886912151788" target="_blank" rel="noopener noreferrer"
         onclick="trackFallbackClick('whatsapp')"><i class="fab fa-whatsapp"></i> WhatsApp</a>
      <a href="tel:06-9271288" onclick="trackFallbackClick('phone')"><i class="fas fa-phone"></i> 06-9271288</a>
      <a href="mailto:dodoken1002@phbay.net" onclick="trackFallbackClick('email')"><i class="fas fa-envelope"></i> Email</a>
    </div>
    <p class="form-fallback-reason">${t.reason}${reason ? '：' + reason : ''}</p>`;
  form.prepend(box);
  box.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function trackFallbackClick(channel) {
  if (typeof gtag === 'function') {
    gtag('event', 'contact_fallback_click', { channel: channel });
  }
}
window.trackFallbackClick = trackFallbackClick;

const FORM_FALLBACK_TXT = {
  'zh-tw': { title:'表單送出失敗，但別讓行程等待', desc:'系統暫時無法接收，請直接用以下任一方式聯繫我們，一樣會由專人為你安排。', reason:'錯誤訊息' },
  'en':    { title:'Submission failed — let\'s not keep your trip waiting', desc:'Our form is temporarily unavailable. Please reach us through any channel below and our team will help you directly.', reason:'Error' },
  'ja':    { title:'送信に失敗しました。ご旅行の相談はこちらから', desc:'フォームが一時的にご利用いただけません。以下のいずれかの方法でご連絡ください。担当者が直接ご対応いたします。', reason:'エラー' },
  'ko':    { title:'전송에 실패했습니다 — 여행 상담은 이쪽으로', desc:'양식이 일시적으로 작동하지 않습니다. 아래 방법 중 하나로 연락 주시면 담당자가 직접 도와드립니다.', reason:'오류' },
  'zh-cn': { title:'表单送出失败，但别让行程等待', desc:'系统暂时无法接收，请直接用以下任一方式联系我们，一样会由专人为你安排。', reason:'错误信息' },
};

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

/* 諮詢表單的梯次選單開關。
   2026-08-27 暫時關閉：tour_slots.booked 是後台人工維護的已售數，
   但諮詢表單每送出一筆就 booked+1（不論幾人），且預購訂單完全不會扣減它，
   兩邊對不起來會造成超賣。待名額改為單一來源後再開回 true。
   關閉後行程卡上的名額顯示不受影響，客人仍可從卡片的「預購訂位」下單。 */
const ENABLE_SLOT_SELECTION = false;

async function loadSlotOptions(selectEl) {
  const group  = document.getElementById('slot-group');
  const select = document.getElementById('slot-select');
  const hint   = document.getElementById('slot-status');
  if (!group || !select) return;

  if (!ENABLE_SLOT_SELECTION) {
    group.style.display = 'none';
    select.innerHTML = '';       // 確保不會送出 slot_id
    select.value = '';
    if (hint) hint.textContent = '';
    return;
  }

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
// 已載入行程（供語言切換時重新渲染）
let _toursGrouped = null;

// 取得行程欄位的當前語言版本（無翻譯則回退中文）
function getLoc(tour, field) {
  const l = window.__lang || 'zh-tw';
  if (l === 'zh-tw') return tour[field];
  const t = tour.i18n && tour.i18n[l];
  return (t && t[field] != null && t[field] !== '') ? t[field] : tour[field];
}
// 取得行程 modal_data 的當前語言版本
function getLocModal(tour) {
  const l = window.__lang || 'zh-tw';
  if (l === 'zh-tw') return tour.modal_data || {};
  const t = tour.i18n && tour.i18n[l] && tour.i18n[l].modal_data;
  return (t && Object.keys(t).length) ? t : (tour.modal_data || {});
}
// 取得行程 prices 的當前語言版本
function getLocPrices(tour) {
  const l = window.__lang || 'zh-tw';
  if (l !== 'zh-tw') {
    const t = tour.i18n && tour.i18n[l] && tour.i18n[l].prices;
    if (Array.isArray(t) && t.length) return t;
  }
  return tour.prices || [];
}

async function loadTours() {
  try {
    const [toursRes, slotsRes] = await Promise.all([
      fetch('/api/tours'),
      fetch('/api/slots')
    ]);
    if (!toursRes.ok) throw new Error('API error');
    const json    = await toursRes.json();
    _toursGrouped = json.tours || {};

    if (slotsRes.ok) {
      const sJson = await slotsRes.json();
      (sJson.slots || []).forEach(s => {
        if (!_allSlots[s.tour_id]) _allSlots[s.tour_id] = [];
        _allSlots[s.tour_id].push(s);
      });
    }

    renderAllTours();

    // 用唯一行程清單填入諮詢表單下拉（不再寫死 ID）
    const seen = new Set();
    const uniqueTours = [];
    Object.values(_toursGrouped).flat().forEach(t => {
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

// 所有行程子分頁鍵（套裝 4 + 單一 4）。新增分頁時一併更新此清單與 HTML、app.py、i18n.js
const TAB_KEYS = ['featured', '2d1n', '3d2n', '4d3n',
                 'north-sea', 'east-sea', 'south-sea', 'main-island'];

// 依當前語言渲染所有行程卡片與彈窗（語言切換時重用）
function renderAllTours() {
  if (!_toursGrouped) return;
  document.querySelectorAll('.tours-loading').forEach(el => el.remove());
  const mc = document.getElementById('modal-container');
  if (mc) mc.innerHTML = '';
  TAB_KEYS.forEach(tab => {
    const grid = document.getElementById(`grid-${tab}`);
    if (!grid) return;
    grid.innerHTML = '';
    const list = _toursGrouped[tab] || [];
    list.forEach(tour => {
      grid.appendChild(renderTourCard(tour));
      renderTourModal(tour);
    });
    // 空分頁：連同頁籤一起隱藏（不再顯示「敬請期待」佔位），讓版面更精練
    const hasTours = list.length > 0;
    const tabBtn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
    if (tabBtn) tabBtn.style.display = hasTours ? '' : 'none';
    const empty = document.querySelector(`.tours-empty[data-empty="${tab}"]`);
    if (empty) empty.style.display = 'none';
  });
  refreshTourCategories();
}

/* 隱藏空分頁後：確保每個分類的作用中頁籤是可見的；整個分類都空則收起分類鈕 */
function refreshTourCategories() {
  document.querySelectorAll('.tour-cat').forEach(cat => {
    const visibleTabs = [...cat.querySelectorAll('.tab-btn')].filter(b => b.style.display !== 'none');
    // 分類內作用中的頁籤若被隱藏，改選第一個可見頁籤
    if (visibleTabs.length) {
      const activeBtn = cat.querySelector('.tab-btn.active');
      if (!activeBtn || activeBtn.style.display === 'none') {
        cat.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        cat.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        visibleTabs[0].classList.add('active');
        const panel = cat.querySelector(`.tab-panel[data-panel="${visibleTabs[0].dataset.tab}"]`);
        if (panel) panel.classList.add('active');
      }
    }
    // 若整個分類都沒有可上架的行程，隱藏此分類的上層分類鈕
    const catKey = cat.dataset.catPanel;
    const catBtn = document.querySelector(`.cat-btn[data-cat="${catKey}"]`);
    if (catBtn) catBtn.style.display = visibleTabs.length ? '' : 'none';
  });
  // 作用中的上層分類若被隱藏，改選第一個可見分類
  const visibleCats = [...document.querySelectorAll('.cat-btn')].filter(b => b.style.display !== 'none');
  const activeCat = document.querySelector('.cat-btn.active');
  if (visibleCats.length && (!activeCat || activeCat.style.display === 'none')) {
    visibleCats[0].click();
  }
  // 只剩一個分類時，隱藏整排分類切換鈕（沒有切換的必要）
  const catBar = document.querySelector('.tour-cat-buttons');
  if (catBar) catBar.style.display = visibleCats.length > 1 ? '' : 'none';
}

// 語言切換時由 i18n.js 呼叫 → 重新渲染動態行程
window.onLangChange = function () { renderAllTours(); };

// 行程卡片／彈窗的固定 UI 字串（依語言）
const TOUR_UI = {
  'zh-tw':{detail:'查看詳情',priceHdr:'出發地 × 價格',suitable:'適合',duration:'天數',notice:'注意事項',includes:'費用包含',notes:'備註',highlights:'行程亮點',dates:'出發日期',
           poster:'行程海報',posterHint:'點擊可看大圖',contact:'行程提供單位與聯絡方式',cAgency:'主辦旅行社',cPartner:'合作夥伴',cPhone:'電話',cLine:'LINE',cEmail:'Email',cWeb:'網站',cLicense:'證號',cNote:'也可直接洽潮旅國際旅行社協助報名',memberBadge:'經潮旅報名完成後可累積澎湖旅次'},
  'en':{detail:'View Details',priceHdr:'Departure × Price',suitable:'For',duration:'Duration',notice:'Note',includes:'Includes',notes:'Notes',highlights:'Highlights',dates:'Departure Dates',
        poster:'Itinerary Poster',posterHint:'Click to enlarge',contact:'Operator & Contact',cAgency:'Operating Agency',cPartner:'Partners',cPhone:'Phone',cLine:'LINE',cEmail:'Email',cWeb:'Website',cLicense:'License',cNote:'You may also book through Phbay Travel',memberBadge:'Completed bookings through Phbay count toward Penghu journeys'},
  'ja':{detail:'詳細を見る',priceHdr:'出発地 × 料金',suitable:'対象',duration:'日数',notice:'ご注意',includes:'料金に含む',notes:'備考',highlights:'ハイライト',dates:'出発日',
        poster:'ツアーポスター',posterHint:'クリックで拡大',contact:'主催会社とお問い合わせ',cAgency:'主催旅行会社',cPartner:'協力',cPhone:'電話',cLine:'LINE',cEmail:'メール',cWeb:'ウェブ',cLicense:'許可番号',cNote:'潮旅国際旅行社経由でのお申し込みも可能です',memberBadge:'潮旅経由で予約・完了すると旅回数に加算'},
  'ko':{detail:'상세 보기',priceHdr:'출발지 × 요금',suitable:'대상',duration:'일수',notice:'유의사항',includes:'포함 사항',notes:'비고',highlights:'하이라이트',dates:'출발일',
        poster:'여행 포스터',posterHint:'클릭하면 확대',contact:'주최사 및 연락처',cAgency:'주최 여행사',cPartner:'협력사',cPhone:'전화',cLine:'LINE',cEmail:'이메일',cWeb:'웹사이트',cLicense:'등록번호',cNote:'Phbay 여행사를 통해서도 예약하실 수 있습니다',memberBadge:'차오뤼를 통해 예약·완료하면 펑후 여행 횟수 적립'},
  'zh-cn':{detail:'查看详情',priceHdr:'出发地 × 价格',suitable:'适合',duration:'天数',notice:'注意事项',includes:'费用包含',notes:'备注',highlights:'行程亮点',dates:'出发日期',
           poster:'行程海报',posterHint:'点击可看大图',contact:'行程提供单位与联络方式',cAgency:'主办旅行社',cPartner:'合作伙伴',cPhone:'电话',cLine:'LINE',cEmail:'Email',cWeb:'网站',cLicense:'证号',cNote:'也可直接洽潮旅国际旅行社协助报名',memberBadge:'经潮旅报名完成后可累积澎湖旅次'}
};
function tourUI(k){ return (TOUR_UI[window.__lang || 'zh-tw'] || TOUR_UI['zh-tw'])[k]; }

/* 行程標題 → 預購表單對照表；之後有新預購行程在此加一行即可 */
const PREORDER_LINKS = [
  { pattern: /小城故事|內海巡禮|内海巡礼|Inner-Sea Cruise/i, url: '/neihai-preorder.html', icon: 'fa-ship' },
  { pattern: /追風|音樂燈光節|音楽祭|Music Festival/i,        url: '/preorder/festival',    icon: 'fa-music' },
];
function preorderLinkFor(title) {
  return PREORDER_LINKS.find(m => m.pattern.test(title || '')) || null;
}

function renderTourCard(tour) {
  const card = document.createElement('div');
  const isHero = tour.is_hero;
  card.className = 'tour-card' + (isHero ? ' tour-card--hero' : '');

  const L = {
    title: getLoc(tour, 'title'),
    description: getLoc(tour, 'description'),
    suitable_for: getLoc(tour, 'suitable_for'),
    duration: getLoc(tour, 'duration'),
    price_display: getLoc(tour, 'price_display'),
    prices: getLocPrices(tour),
  };

  const badgeHtml = tour.badge_text
    ? `<div class="tour-badge ${tour.badge_class || ''}">${tour.badge_text}</div>` : '';

  const imgHtml = tour.image_url
    ? `<img src="${tour.image_url}" alt="${L.title}" loading="lazy" />`
    : `<img src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80" alt="${L.title}" loading="lazy" />`;

  // 多出發地價格列（DB 格式：{label, value}）
  const pricesHtml = Array.isArray(L.prices) && L.prices.length
    ? `<div class="tour-prices">${L.prices.map(p =>
        `<div class="price-row"><span class="price-from">${p.label ?? p.from ?? ''}</span><span class="price-val">${p.value ?? p.price ?? ''}</span></div>`
      ).join('')}</div>` : '';

  const priceMetaHtml = (!L.prices || !L.prices.length) && L.price_display
    ? `<span class="meta-item price"><i class="fas fa-tag"></i> ${L.price_display}</span>` : '';

  const btnClass = isHero ? 'btn btn-card btn-card--hero' : 'btn btn-card';
  const cardPreorder = preorderLinkFor(L.title);
  const neihaiCardCta = cardPreorder
    ? `<a href="${cardPreorder.url}" class="${btnClass}" style="margin-top:10px;text-decoration:none;text-align:center">
        <i class="fas ${cardPreorder.icon}"></i> 預購訂位
      </a>`
    : '';

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
      <h3 class="tour-title">${L.title}</h3>
      <p class="tour-desc">${L.description || ''}</p>
      <p style="font-size:.78rem;color:#9a6b16;font-weight:700"><i class="fas fa-passport"></i> ${tourUI('memberBadge')}</p>
      ${slotHtml}
      ${pricesHtml}
      <div class="tour-meta">
        ${L.suitable_for ? `<span class="meta-item"><i class="fas fa-users"></i> ${L.suitable_for}</span>` : ''}
        ${L.duration ? `<span class="meta-item"><i class="fas fa-calendar"></i> ${L.duration}</span>` : ''}
        ${priceMetaHtml}
      </div>
      <button class="${btnClass}" onclick="openModal('db-${tour.id}')">
        ${tourUI('detail')} <i class="fas fa-arrow-right"></i>
      </button>
      ${neihaiCardCta}
    </div>`;
  return card;
}

function renderTourModal(tour) {
  const md     = getLocModal(tour);
  const title  = getLoc(tour, 'title');
  const dur    = getLoc(tour, 'duration');
  const pdisp  = getLoc(tour, 'price_display');
  const prices = getLocPrices(tour);
  const container = document.getElementById('modal-container');

  const modalEl = document.createElement('div');
  modalEl.className = 'modal' + (tour.is_hero ? ' modal--turtle' : '');
  modalEl.id = `modal-db-${tour.id}`;

  // Prices table or tag
  let priceSection = '';
  if (Array.isArray(prices) && prices.length) {
    priceSection = `<h4><i class="fas fa-tag"></i> ${tourUI('priceHdr')}</h4>
      <table class="price-table">
        ${prices.map(p => `<tr><td>${p.label ?? p.from ?? ''}</td><td class="price-highlight">${p.value ?? p.price ?? ''}</td></tr>`).join('')}
      </table>`;
  } else if (pdisp) {
    priceSection = `<h4><i class="fas fa-tag"></i> ${tourUI('priceHdr')}</h4><p>${pdisp}</p>`;
  }

  // Dates
  const datesHtml = md.dates && md.dates.length
    ? `<h4><i class="fas fa-calendar-alt"></i> ${tourUI('dates')}</h4>
       <div class="date-chips">${md.dates.map(d => `<span class="date-chip">${d}</span>`).join('')}</div>` : '';

  // Highlights
  const hlHtml = md.highlights && md.highlights.length
    ? `<h4><i class="fas fa-star"></i> ${tourUI('highlights')}</h4>
       <ul>${md.highlights.map(h => `<li>${h}</li>`).join('')}</ul>` : '';

  // Day by day
  let daysHtml = '';
  if (md.days && md.days.length) {
    daysHtml = `<h4><i class="fas fa-map-signs"></i> ${tourUI('highlights')}</h4><div class="day-blocks">
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
  const includesHtml = md.includes ? `<h4><i class="fas fa-check-circle"></i> ${tourUI('includes')}</h4><p>${md.includes}</p>` : '';
  const notesHtml    = md.notes   ? `<h4><i class="fas fa-exclamation-circle"></i> ${tourUI('notes')}</h4><p>${md.notes}</p>` : '';

  // 完整行程海報（modal_data.posters：圖片路徑陣列；點擊開新分頁看原圖）
  const posters = Array.isArray(md.posters) ? md.posters : [];
  const posterHtml = posters.length
    ? `<h4><i class="fas fa-image"></i> ${tourUI('poster')}
         <span class="poster-hint">${tourUI('posterHint')}</span></h4>
       <div class="tour-posters">
         ${posters.map((p, i) => `
           <a href="${p}" target="_blank" rel="noopener noreferrer" class="poster-thumb">
             <img src="${p}" alt="${title}｜${tourUI('poster')} ${i + 1}" loading="lazy" decoding="async" />
           </a>`).join('')}
       </div>` : '';

  // 行程提供單位與聯絡方式（modal_data.contact）
  const c = md.contact || {};
  const cRows = [
    c.agency  ? `<tr><td>${tourUI('cAgency')}</td><td>${c.agency}</td></tr>` : '',
    c.partner ? `<tr><td>${tourUI('cPartner')}</td><td>${c.partner}</td></tr>` : '',
    c.phone   ? `<tr><td>${tourUI('cPhone')}</td><td><a href="tel:${String(c.phone).split(/[／/、（(]/)[0].replace(/[^\d+]/g, '')}">${c.phone}</a></td></tr>` : '',
    c.line    ? `<tr><td>${tourUI('cLine')}</td><td>${c.line}</td></tr>` : '',
    c.email   ? `<tr><td>${tourUI('cEmail')}</td><td><a href="mailto:${c.email}">${c.email}</a></td></tr>` : '',
    c.website ? `<tr><td>${tourUI('cWeb')}</td><td><a href="${/^https?:/.test(c.website) ? c.website : 'https://' + c.website}" target="_blank" rel="noopener noreferrer">${c.website}</a></td></tr>` : '',
    c.license ? `<tr><td>${tourUI('cLicense')}</td><td>${c.license}</td></tr>` : '',
  ].filter(Boolean).join('');
  const contactHtml = cRows
    ? `<h4><i class="fas fa-address-card"></i> ${tourUI('contact')}</h4>
       <table class="contact-table">${cRows}</table>
       <p class="contact-note"><i class="fas fa-circle-info"></i> ${tourUI('cNote')}</p>` : '';

  const headerClass = tour.is_hero ? 'modal-header modal-header--turtle' : 'modal-header';
  const headerInner = tour.is_hero
    ? `<div class="modal-header-content">
        <span class="modal-year">2026</span>
        <h2>${title}</h2>
        <span class="modal-tag">${dur || ''}</span>
       </div>`
    : `<h2>${title}</h2>
       <span class="modal-tag">${dur || ''}${pdisp ? '｜' + pdisp : ''}</span>`;
  const modalPreorder = preorderLinkFor(title);
  const neihaiModalCta = modalPreorder
    ? `<a href="${modalPreorder.url}" class="btn btn-primary">
        <i class="fas ${modalPreorder.icon}"></i> 前往預購訂位
      </a>`
    : `<a href="#contact" class="btn btn-primary" onclick="closeModal()">
        <i class="fas fa-comment-dots"></i> ${tourUI('detail')}
      </a>`;

  modalEl.innerHTML = `
    <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
    <div class="${headerClass}">${headerInner}</div>
    <div class="modal-body">
      ${datesHtml}
      ${priceSection}
      ${hlHtml}
      ${daysHtml}
      ${includesHtml}
      ${posterHtml}
      ${contactHtml}
      ${notesHtml}
      <div style="background:#fff7df;border-left:4px solid #c99535;padding:12px 14px;margin:16px 0"><i class="fas fa-passport"></i> <strong>${tourUI('memberBadge')}</strong></div>
      ${neihaiModalCta}
    </div>`;

  container.appendChild(modalEl);
}

/* ═══════════════════════════════════════════════
   行程心理測驗
════════════════════════════════════════════════ */
const QUIZ_QUESTIONS = [
  {
    icon: '📅',
    q: '你預計幾月來澎湖？',
    options: [
      { icon:'🌸', text:'3–5 月（春）',  sub:'大潮季、秘境現身',      scores:{ tides:3, neihai:1 } },
      { icon:'☀️', text:'6–8 月（夏）',  sub:'跳島旺季、暑假出遊',    scores:{ island:3, family:2, neihai:1 } },
      { icon:'🎆', text:'9–10 月（秋）', sub:'追風音樂燈光節登場',    scores:{ festival:4, neihai:1 } },
      { icon:'🧭', text:'冬季 / 還沒決定', sub:'看推薦再決定',          scores:{ neihai:2, tides:1, family:1 } },
    ]
  },
  {
    icon: '🧳',
    q: '這趟你和誰一起來？',
    options: [
      { icon:'👨‍👩‍👧‍👦', text:'親子 / 全家出遊', sub:'帶著孩子一起探索',   scores:{ family:4, neihai:1 } },
      { icon:'💑', text:'情侶 兩人',        sub:'浪漫慢步調',        scores:{ neihai:2, tides:2, festival:1 } },
      { icon:'🎉', text:'一群朋友',          sub:'人多更熱鬧',        scores:{ festival:3, island:3 } },
      { icon:'🏢', text:'公司員旅 / 揪團',   sub:'一起放鬆團體行',    scores:{ festival:2, island:2, family:1 } },
    ]
  },
  {
    icon: '🌊',
    q: '最想要的澎湖體驗是？',
    options: [
      { icon:'🤿', text:'海上活動', sub:'浮潛、SUP、跳島',     scores:{ island:4 } },
      { icon:'📸', text:'拍照打卡', sub:'秘境美景收進相機',    scores:{ tides:3, neihai:2 } },
      { icon:'🍢', text:'在地美食', sub:'古厝老街、海味小吃',  scores:{ neihai:3, tides:1 } },
      { icon:'🍃', text:'慢旅行',   sub:'放空、看海、聽故事',  scores:{ neihai:3, tides:2 } },
      { icon:'🎶', text:'音樂節',   sub:'夜間活動、熱鬧氣氛',  scores:{ festival:4 } },
    ]
  },
  {
    icon: '💰',
    q: '每人預算大概是？',
    options: [
      { icon:'💵', text:'NT$ 5,000 以下',    sub:'輕鬆玩就好',       scores:{ neihai:2, tides:2 } },
      { icon:'💳', text:'NT$ 5,000–10,000',  sub:'合理預算體驗豐富', scores:{ family:2, island:2, festival:1 } },
      { icon:'🌟', text:'NT$ 10,000 以上',   sub:'值得的體驗不計較', scores:{ festival:2, island:2, family:1 } },
      { icon:'🤔', text:'還沒抓預算',         sub:'看推薦再決定',     scores:{ neihai:1, tides:1, family:1, island:1, festival:1 } },
    ]
  },
  {
    icon: '⏳',
    q: '這次打算玩幾天？',
    options: [
      { icon:'⚡', text:'半天 / 一日',  sub:'順遊、時間有限',    scores:{ neihai:3, tides:2 } },
      { icon:'🌙', text:'2 天 1 夜',   sub:'週末快閃',          scores:{ neihai:2, tides:2, island:1 } },
      { icon:'☀️', text:'3 天 2 夜',   sub:'剛剛好不趕又充實',  scores:{ festival:3, family:2, neihai:1 } },
      { icon:'🏝️', text:'4 天 3 夜以上', sub:'深度慢遊玩個夠',   scores:{ island:3, family:1 } },
    ]
  },
];

const QUIZ_RESULTS = {
  neihai: {
    type: '內海慢遊收藏家 🚤',
    desc: '你喜歡小而美、有人帶路的在地體驗。小城故事・內海巡禮很適合想輕鬆看海、聽故事、拍美照，也想避開大型人潮的旅人。',
    tour: { name:'小城故事・內海巡禮', duration:'約90分鐘', price:'試航價 NT$1,000 起', img:'/images/neihai-cruise-hero-2026.jpg', interest:'neihai', url:'/neihai-preorder.html', cta:'查看內海巡禮預購' },
  },
  festival: {
    type: '追風音樂節玩家 🎵',
    desc: '你適合把白天的海島散步和晚上的音樂燈光節排在同一趟旅程裡。追風音樂節三天兩夜剛剛好，交通、住宿與活動節奏都交給潮旅協助安排。',
    tour: { name:'追風音樂節三天兩夜', duration:'3天2夜', price:'專人報價', img:'/images/festival-poster.png', interest:'festival', url:'/preorder/festival', cta:'查看音樂節行程預購' },
  },
  family: {
    type: '親子海島守護者 👨‍👩‍👧',
    desc: '家人的笑容是旅途中最美的風景！安全、溫馨又有趣的親子澎湖 3 天 2 夜，讓孩子與海洋親密接觸，留下一家人最珍貴的回憶。',
    tour: { name:'親子澎湖 3 天 2 夜', duration:'3天2夜', price:'NT$ 9,500 起', img:'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=400&q=80', interest:'family3d', cta:'立即諮詢這個行程' },
  },
  island: {
    type: '跳島冒險家 🏝️',
    desc: '你熱愛海洋與探索，望安七美跳島最適合你！雙心石滬、綠蠵龜故鄉、大菓葉玄武岩，一次收集澎湖最經典的離島秘境。',
    tour: { name:'望安七美跳島', duration:'3–4天', price:'NT$ 6,999 起', img:'https://images.unsplash.com/photo-1583212292454-1fe6229603b7?w=400&q=80', interest:'turtle4d', cta:'立即諮詢這個行程' },
  },
  tides: {
    type: '潮汐秘境獵人 🌅',
    desc: '你懂得看時機玩澎湖！退潮才現身的摩西分海、S 彎沙灘與潮間帶秘境，跟著潮汐表安排，拍到別人拍不到的絕景。',
    tour: { name:'潮汐秘境玩法', duration:'彈性安排', price:'依行程報價', img:'/images/neihai-cruise-hero-2026.jpg', interest:'other', url:'/tides', cta:'查看潮汐查詢系統' },
  },
};

let quizAnswers = [];
let quizAnswerTexts = [];   // 保留題目與選項文字，供 AI 個人化建議使用

function initQuiz() {
  quizAnswers = [];
  quizAnswerTexts = [];
  const sharedResult = new URLSearchParams(window.location.search).get('quiz');
  if (sharedResult && QUIZ_RESULTS[sharedResult]) {
    renderQuizResult(sharedResult, true);
    return;
  }
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
  quizAnswerTexts.push({ q: QUIZ_QUESTIONS[qIdx].q, a: QUIZ_QUESTIONS[qIdx].options[optIdx].text });
  const next = qIdx + 1;
  if (next < QUIZ_QUESTIONS.length) {
    renderQuizQuestion(next);
  } else {
    renderQuizResult();
  }
};

function renderQuizResult(forcedKey, fromShare = false) {
  const totals = { neihai:0, festival:0, family:0, island:0, tides:0 };
  quizAnswers.forEach(s => Object.entries(s).forEach(([k,v]) => { if (k in totals) totals[k] = (totals[k]||0) + v; }));
  const best = (forcedKey && QUIZ_RESULTS[forcedKey]) ? forcedKey
    : Object.entries(totals).sort((a,b) => b[1]-a[1])[0][0];
  const r = QUIZ_RESULTS[best];
  const wrap = document.getElementById('quiz-wrap');
  const shareUrl = `${window.location.origin}${window.location.pathname}?quiz=${encodeURIComponent(best)}#quiz`;
  const primaryHref = r.tour.url || '#contact';
  const primaryAction = r.tour.url
    ? ` onclick="trackQuizCta('${best}','preorder')"`
    : ` onclick="prefillTour('${r.tour.interest}');trackQuizCta('${best}','contact')"`;
  if (typeof gtag === 'function') {
    gtag('event', 'quiz_result', { result_type: r.type, content_name: r.tour.name });
  }
  if (typeof fbq === 'function') {
    fbq('track', 'ViewContent', { content_name: `行程診斷：${r.type}`, content_category: '澎湖行程診斷' });
  }
  wrap.innerHTML = `
    <div class="quiz-card quiz-result">
      <div class="quiz-progress">
        <div class="quiz-progress-bar"><div class="quiz-progress-fill" style="width:100%"></div></div>
        <span class="quiz-step-label">✨ 結果揭曉！</span>
      </div>
      <span class="quiz-result-badge">你的旅遊類型</span>
      <div class="quiz-result-type">${r.type}</div>
      <p class="quiz-result-desc">${r.desc}</p>
      <div id="quiz-ai-note" style="display:none;background:#f0f7ff;border-left:3px solid var(--blue-main);border-radius:8px;padding:12px 16px;margin:0 0 14px;text-align:left;font-size:.94rem;line-height:1.8;color:var(--text-dark)"></div>
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
      <p class="quiz-share-note">把結果傳給 LINE 專人幫你排，或留資料領取專屬的澎湖行程建議表，我們依你的玩法安排日期、交通與行程。</p>
      <div class="quiz-result-actions">
        <a href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer" class="btn btn-primary" onclick="prefillTour('${r.tour.interest}');trackQuizCta('${best}','line')">
          <i class="fab fa-line"></i> 把結果傳給 LINE 專人幫我排
        </a>
        <button class="btn btn-outline" onclick="openQuizLead('${best}')">
          <i class="fas fa-file-lines"></i> 領取澎湖行程建議表
        </button>
      </div>
      <div id="quiz-lead-box" style="display:none"></div>
      <div class="quiz-result-actions" style="margin-top:10px">
        <a href="${primaryHref}" class="quiz-retry"${primaryAction}>
          <i class="fas fa-route"></i> ${r.tour.cta || (r.tour.url ? '查看推薦預購' : '立即諮詢這個行程')}
        </a>
        <button class="quiz-retry" onclick="shareQuizResult('${best}')">
          <i class="fas fa-share-nodes"></i> 分享結果
        </button>
        <button class="quiz-retry" onclick="downloadQuizCard('${best}')">
          <i class="fas fa-image"></i> 儲存結果圖卡
        </button>
        <button class="quiz-retry" onclick="resetQuizShareUrl()">
          <i class="fas fa-redo"></i> 重新測驗
        </button>
      </div>
      <div class="quiz-copy-toast" id="quiz-copy-toast">已複製分享連結！</div>
    </div>`;
  if (fromShare && location.hash !== '#quiz') location.hash = 'quiz';
  if (!fromShare && quizAnswerTexts.length) loadQuizAiNote(best);
}

// AI 個人化建議（失敗就靜默略過，不影響原結果）
function loadQuizAiNote(resultKey) {
  fetch('/api/quiz-ai', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result: resultKey, answers: quizAnswerTexts }),
  }).then(r => r.json()).then(d => {
    if (!d.ok || !d.text) return;
    const box = document.getElementById('quiz-ai-note');
    if (!box) return;
    box.innerHTML = `<strong style="color:var(--blue-main)">✦ 給你的小建議</strong><br>${d.text.replace(/</g,'&lt;')}`;
    box.style.display = 'block';
    if (typeof gtag === 'function') gtag('event', 'quiz_ai_note_shown', { result_type: resultKey });
  }).catch(() => {});
}

async function shareQuizResult(key) {
  const r = QUIZ_RESULTS[key];
  if (!r) return;
  const shareUrl = `${window.location.origin}${window.location.pathname}?quiz=${encodeURIComponent(key)}#quiz`;
  const shareData = {
    title: `${r.type}｜潮旅澎湖行程診斷`,
    text: `我測出來是「${r.type}」，推薦 ${r.tour.name}。你也測看看適合哪種澎湖玩法！`,
    url: shareUrl
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(`${shareData.text} ${shareUrl}`);
      const toast = document.getElementById('quiz-copy-toast');
      if (toast) {
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2200);
      }
    } else {
      window.prompt('複製這段分享給朋友：', `${shareData.text} ${shareUrl}`);
    }
    if (typeof gtag === 'function') gtag('event', 'share', { method: 'quiz_result', content_type: '澎湖行程診斷', item_id: key });
  } catch (_) {}
}
window.shareQuizResult = shareQuizResult;

function resetQuizShareUrl() {
  const clean = `${window.location.origin}${window.location.pathname}#quiz`;
  history.replaceState(null, '', clean);
  initQuiz();
}
window.resetQuizShareUrl = resetQuizShareUrl;

function prefillTour(interest) {
  const sel = document.getElementById('tour-interest');
  if (sel && interest) sel.value = interest;
}
window.prefillTour = prefillTour;

/* 診斷結果 CTA 點擊追蹤：知道哪種結果最會導 LINE / 預購 */
function trackQuizCta(key, channel) {
  const r = QUIZ_RESULTS[key];
  if (!r) return;
  if (typeof gtag === 'function') {
    gtag('event', 'quiz_cta_click', { result_type: r.type, channel });
  }
  if (channel === 'line' && typeof fbq === 'function') {
    fbq('track', 'Lead', { content_name: `行程診斷LINE：${r.type}`, content_category: '澎湖行程診斷' });
  }
}
window.trackQuizCta = trackQuizCta;

/* 領取澎湖行程建議表：展開輕量名單表單（姓名＋電話/LINE＋月份/人數） */
function openQuizLead(key) {
  const r = QUIZ_RESULTS[key];
  if (!r) return;
  const box = document.getElementById('quiz-lead-box');
  if (!box) return;
  if (box.style.display === 'block') { box.style.display = 'none'; return; }
  box.style.display = 'block';
  box.innerHTML = `
    <div style="background:#f6fbff;border:1px solid #cde7f7;border-radius:16px;padding:18px;margin-top:14px;text-align:left">
      <div style="font-weight:800;color:#0d4f83;margin-bottom:6px"><i class="fas fa-gift"></i> 領取「${r.tour.name}」專屬行程建議表</div>
      <p style="font-size:.86rem;color:#5a7a94;margin-bottom:12px">留下聯絡方式，潮旅在地顧問會依你的診斷結果，把建議行程、費用與可出發日期整理好傳給你。</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <input id="qlead-name" placeholder="稱呼 *" style="padding:10px;border:1px solid #cde0ee;border-radius:10px;width:100%" />
        <input id="qlead-phone" placeholder="電話 / LINE ID *" style="padding:10px;border:1px solid #cde0ee;border-radius:10px;width:100%" />
        <input id="qlead-month" placeholder="預計月份（選填）" style="padding:10px;border:1px solid #cde0ee;border-radius:10px;width:100%" />
        <input id="qlead-people" placeholder="人數（選填）" style="padding:10px;border:1px solid #cde0ee;border-radius:10px;width:100%" />
      </div>
      <button class="btn btn-primary" style="margin-top:12px;width:100%;justify-content:center" onclick="submitQuizLead('${key}')">
        <i class="fas fa-paper-plane"></i> 送出，領取行程建議表
      </button>
      <div id="qlead-msg" style="font-size:.86rem;margin-top:8px"></div>
    </div>`;
}
window.openQuizLead = openQuizLead;

async function submitQuizLead(key) {
  const r = QUIZ_RESULTS[key];
  const g = id => (document.getElementById(id) || {}).value || '';
  const name = g('qlead-name').trim(), phone = g('qlead-phone').trim();
  const msg = document.getElementById('qlead-msg');
  if (!name || !phone) { msg.style.color = '#c53030'; msg.textContent = '請填寫稱呼與聯絡方式。'; return; }
  const btn = document.querySelector('#quiz-lead-box .btn-primary');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 送出中...'; }
  try {
    const res = await fetch('/api/quiz-lead', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, phone, month: g('qlead-month').trim(), people: g('qlead-people').trim(),
        result_type: r ? r.type : key, result_name: r ? r.tour.name : '',
      }),
    });
    const d = await res.json();
    if (!res.ok || !d.ok) throw new Error(d.error || '送出失敗');
    if (typeof gtag === 'function') gtag('event', 'generate_lead', { method: 'quiz_guide', result_type: r ? r.type : key });
    if (typeof fbq === 'function') fbq('track', 'Lead', { content_name: `行程診斷建議表：${r ? r.type : key}`, content_category: '澎湖行程診斷' });
    document.getElementById('quiz-lead-box').innerHTML =
      '<div style="background:#e8fff4;border:1px solid #9ae6b4;border-radius:16px;padding:20px;margin-top:14px;text-align:center;color:#0a6b45;font-weight:700">' +
      '<i class="fas fa-circle-check"></i> 已收到！潮旅顧問會盡快把專屬行程建議表傳給你，也歡迎先加官方 LINE @phbay2018 加速聯繫。</div>';
  } catch (err) {
    msg.style.color = '#c53030'; msg.textContent = err.message || '送出失敗，請稍後再試或改用 LINE 聯繫。';
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-paper-plane"></i> 送出，領取行程建議表'; }
  }
}
window.submitQuizLead = submitQuizLead;

/* 診斷結果圖卡：Canvas 產生 1080×1350 分享圖（Logo＋官網＋LINE＋CTA） */
async function downloadQuizCard(key) {
  const r = QUIZ_RESULTS[key];
  if (!r) return;
  const W = 1080, H = 1350;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');

  // 背景漸層（海洋藍）
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#0b5e9e'); bg.addColorStop(1, '#14b8c9');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  // 行程圖（上半部，等比裁滿），失敗就略過
  try {
    const img = await new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im); im.onerror = rej;
      im.src = r.tour.img;
    });
    const areaH = 620, scale = Math.max(W / img.width, areaH / img.height);
    const dw = img.width * scale, dh = img.height * scale;
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, W, areaH); ctx.clip();
    ctx.drawImage(img, (W - dw) / 2, (areaH - dh) / 2, dw, dh);
    ctx.restore();
    const fade = ctx.createLinearGradient(0, areaH - 160, 0, areaH);
    fade.addColorStop(0, 'rgba(11,94,158,0)'); fade.addColorStop(1, 'rgba(11,94,158,1)');
    ctx.fillStyle = fade; ctx.fillRect(0, areaH - 160, W, 160);
  } catch (_) {}

  const centerText = (txt, y, font, color) => {
    ctx.font = font; ctx.fillStyle = color; ctx.textAlign = 'center';
    ctx.fillText(txt, W / 2, y);
  };
  const wrapText = (txt, y, font, color, maxW, lineH) => {
    ctx.font = font; ctx.fillStyle = color; ctx.textAlign = 'center';
    let line = '';
    for (const ch of txt) {
      if (ctx.measureText(line + ch).width > maxW) { ctx.fillText(line, W / 2, y); y += lineH; line = ch; }
      else line += ch;
    }
    if (line) ctx.fillText(line, W / 2, y);
    return y + lineH;
  };

  centerText('潮旅澎湖行程診斷', 700, '600 34px "Noto Sans TC", sans-serif', 'rgba(255,255,255,.85)');
  centerText('我的旅遊類型', 756, '400 28px "Noto Sans TC", sans-serif', 'rgba(255,255,255,.7)');
  centerText(r.type, 830, '900 62px "Noto Sans TC", sans-serif', '#ffe066');
  let y = wrapText(r.desc, 910, '400 30px "Noto Sans TC", sans-serif', 'rgba(255,255,255,.92)', 880, 46);

  // 推薦行程框
  const boxY = Math.max(y + 10, 1080);
  ctx.fillStyle = 'rgba(255,255,255,.14)';
  const bw = 900, bx = (W - bw) / 2;
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(bx, boxY, bw, 110, 20); else ctx.rect(bx, boxY, bw, 110);
  ctx.fill();
  centerText('✦ 推薦行程', boxY + 42, '700 26px "Noto Sans TC", sans-serif', '#ffe066');
  centerText(r.tour.name, boxY + 86, '800 34px "Noto Sans TC", sans-serif', '#ffffff');

  // 底部品牌列
  ctx.fillStyle = 'rgba(6,42,71,.92)'; ctx.fillRect(0, H - 120, W, 120);
  centerText('潮旅國際旅行社｜phbay.info｜LINE @phbay2018', H - 72, '700 30px "Noto Sans TC", sans-serif', '#ffffff');
  centerText('測你的澎湖玩法 → www.phbay.info', H - 30, '400 26px "Noto Sans TC", sans-serif', 'rgba(255,255,255,.75)');

  if (typeof gtag === 'function') gtag('event', 'share', { method: 'quiz_card_image', content_type: '澎湖行程診斷', item_id: key });
  const blob = await new Promise(res => cv.toBlob(res, 'image/png'));
  const file = new File([blob], `潮旅行程診斷_${key}.png`, { type: 'image/png' });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file], title: `${r.type}｜潮旅澎湖行程診斷` }); return; } catch (_) {}
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = file.name;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}
window.downloadQuizCard = downloadQuizCard;

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
