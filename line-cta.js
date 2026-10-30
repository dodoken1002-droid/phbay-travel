/* 官網 → LINE（MantaGO 對話互動引流）：點擊追蹤＋電腦版站內 QR
   官網所有「加 LINE」按鈕都改走 go.mantago.co 引流連結：加好友時 MantaGO 會自動貼標籤
   （來源_官網／興趣_xxx），並回覆對應的對話模組。官方帳號 @phbay2018 與 @ont0739i 為同一帳號。

   手機：照常開連結 → 直接進 LINE App。
   電腦：MantaGO 會先跳自家 QR 頁，掃完的 LIFF 在電腦瀏覽器又要 LINE 登入 QR，等於看到兩次 QR。
         所以電腦版改在官網跳出視窗，只放一個 QR（內容就是同一條 go.mantago.co 連結，
         手機掃描後一樣會貼標），客人不用離開官網。QR 圖檔在 /images/line-qr/<代碼>.svg。

   連結對照（改連結時請同步更新 MantaGO 後台「對話互動引流」與 /images/line-qr/）：
     QnBsyj 官網-通用LINE諮詢   首頁、FAQ、預購、七美龜、行程頁、美食/音樂節攻略
     iCy82S 官網-秋冬頁          /penghu-autumn-winter
     nMG8Tp 官網-潮汐查詢頁      /tides
     4ATZyb 官網-行程診斷        行程診斷結果、/penghu-itinerary-recommendations
     yjC7QY 官網-三天兩夜頁      /penghu-3days-itinerary
     fSNKzY 官網-親子旅遊頁      /penghu-family-travel
     5w7aEZ 官網-澎湖百旅會員頁  （會員頁預留）
     bDsNKJ 官網-詢價表單送出    首頁詢價表單送出後

   每次點擊送 GA4 事件 mantago_line_click：
     link_id     ＝ 引流代碼（對應 MantaGO 後台那一條）
     line_source ＝ 按鈕位置（data-line-source），沒填就用頁面路徑
     page_path   ＝ 目前頁面
     open_mode   ＝ desktop_qr（電腦版跳 QR 視窗）／direct（手機直接開 LINE）
   GA4 會把這次造訪原本帶進來的 utm_* 一起歸因。 */
(function () {
  if (window.__phbayLineCta) return;
  window.__phbayLineCta = true;

  var QR_CODES = ['QnBsyj', 'iCy82S', 'nMG8Tp', '4ATZyb', 'yjC7QY', 'fSNKzY', '5w7aEZ', 'bDsNKJ'];

  // 電腦＝主要指標是滑鼠且不是手機/平板 UA；iPad（桌面版 UA）因為是觸控 pointer:coarse 會走手機流程
  function isDesktop() {
    var ua = navigator.userAgent || '';
    if (/Android|iPhone|iPad|iPod|Mobile|Line\//i.test(ua)) return false;
    try { return window.matchMedia('(hover: hover) and (pointer: fine)').matches; }
    catch (_) { return false; }
  }

  function track(params) {
    try {
      if (typeof gtag === 'function') gtag('event', 'mantago_line_click', params);
      if (typeof fbq === 'function') fbq('trackCustom', 'MantagoLineClick', params);
    } catch (_) { /* 追蹤失敗不影響主要流程 */ }
  }

  var CSS =
    '.phbay-lq{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;' +
      'background:rgba(10,30,45,.55);padding:16px;font-family:"Noto Sans TC",system-ui,sans-serif}' +
    '.phbay-lq[hidden]{display:none}' +
    '.phbay-lq-box{position:relative;background:#fff;color:#17384d;border-radius:18px;max-width:340px;width:100%;' +
      'padding:28px 24px 22px;text-align:center;box-shadow:0 18px 48px rgba(0,0,0,.25)}' +
    '.phbay-lq-box h2{margin:0 0 6px;font-size:1.15rem;font-weight:800;color:#17384d}' +
    '.phbay-lq-box p{margin:0;font-size:.9rem;line-height:1.7;color:#4a6475}' +
    '.phbay-lq-qr{display:block;width:220px;height:220px;margin:16px auto 12px;padding:10px;background:#fff;' +
      'border:1px solid #e3ecf1;border-radius:12px;box-sizing:content-box}' +
    '.phbay-lq-badge{display:inline-flex;align-items:center;gap:6px;background:#06c755;color:#fff;font-weight:700;' +
      'border-radius:999px;padding:4px 12px;font-size:.8rem;margin-bottom:10px}' +
    '.phbay-lq-close{position:absolute;top:8px;right:10px;border:0;background:none;font-size:1.6rem;line-height:1;' +
      'color:#8aa0ad;cursor:pointer;padding:6px}' +
    '.phbay-lq-close:hover,.phbay-lq-close:focus-visible{color:#17384d}' +
    '.phbay-lq-note{margin-top:10px!important;font-size:.78rem!important;color:#8aa0ad!important}';

  var overlay, qrImg, lastFocus;

  function build() {
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    overlay = document.createElement('div');
    overlay.className = 'phbay-lq';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'phbay-lq-title');
    overlay.innerHTML =
      '<div class="phbay-lq-box">' +
        '<button type="button" class="phbay-lq-close" aria-label="關閉">&times;</button>' +
        '<span class="phbay-lq-badge">LINE</span>' +
        '<h2 id="phbay-lq-title">用手機掃描，加入潮澎湖 LINE</h2>' +
        '<p>打開手機相機或 LINE 掃描下方 QR Code，<br>小編會直接在 LINE 回覆您</p>' +
        '<img class="phbay-lq-qr" alt="潮澎湖 LINE 官方帳號 QR Code" width="220" height="220">' +
        '<p class="phbay-lq-note">官方帳號 @phbay2018｜週一至週五 08:30–17:30</p>' +
      '</div>';
    document.body.appendChild(overlay);
    qrImg = overlay.querySelector('.phbay-lq-qr');

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target.closest('.phbay-lq-close')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay && !overlay.hidden) close();
    });
  }

  function open(code) {
    if (!overlay) build();
    lastFocus = document.activeElement;
    qrImg.src = '/images/line-qr/' + code + '.svg';
    overlay.hidden = false;
    overlay.querySelector('.phbay-lq-close').focus();
  }

  function close() {
    overlay.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href*="go.mantago.co/"]') : null;
    if (!a) return;
    var m = a.href.match(/go\.mantago\.co\/([A-Za-z0-9]+)/);
    var code = m ? m[1] : '';
    var desktopQr = isDesktop() && QR_CODES.indexOf(code) !== -1;

    track({
      link_id: code,
      line_source: a.getAttribute('data-line-source') || location.pathname,
      page_path: location.pathname,
      open_mode: desktopQr ? 'desktop_qr' : 'direct'
    });

    if (desktopQr) {
      e.preventDefault();
      open(code);
    }
  });
})();
