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
function initContactForm() {
  const form    = document.getElementById('contact-form');
  const success = document.getElementById('form-success');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // 收集表單資料
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // 基本驗證
    if (!data.name || !data.phone || !data.travel_date || !data.people) {
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

/* ─── 工具函式 ─── */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
