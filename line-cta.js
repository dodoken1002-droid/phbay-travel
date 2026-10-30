/* 官網 → LINE（MantaGO 對話互動引流）點擊追蹤
   官網所有「加 LINE」按鈕都改走 go.mantago.co 引流連結：加好友時 MantaGO 會自動貼標籤
   （來源_官網／興趣_xxx），並回覆對應的對話模組。官方帳號 @phbay2018 與 @ont0739i 為同一帳號。

   連結對照（改連結時請同步更新 MantaGO 後台「對話互動引流」）：
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
   GA4 會把這次造訪原本帶進來的 utm_* 一起歸因，可在「探索」用 link_id × 工作階段來源 交叉看。 */
(function () {
  if (window.__phbayLineCta) return;
  window.__phbayLineCta = true;

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href*="go.mantago.co/"]') : null;
    if (!a) return;
    var m = a.href.match(/go\.mantago\.co\/([A-Za-z0-9]+)/);
    var params = {
      link_id: m ? m[1] : '',
      line_source: a.getAttribute('data-line-source') || location.pathname,
      page_path: location.pathname
    };
    try {
      if (typeof gtag === 'function') gtag('event', 'mantago_line_click', params);
      if (typeof fbq === 'function') fbq('trackCustom', 'MantagoLineClick', params);
    } catch (_) { /* 追蹤失敗不影響連結開啟 */ }
  }, true);
})();
