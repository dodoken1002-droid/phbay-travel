const toggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('#main-menu');
toggle?.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') === 'true';
  toggle.setAttribute('aria-expanded', String(!open));
  menu.classList.toggle('open', !open);
});
menu?.addEventListener('click', event => {
  if (event.target.closest('a')) {
    menu.classList.remove('open');
    toggle?.setAttribute('aria-expanded', 'false');
  }
});

// 諮詢點擊：LINE / 電話各送 GA4 contact_click；LINE 另記 Meta Lead（與首頁諮詢一致）
document.querySelectorAll('a[href*="line.me"], a[href*="go.mantago.co"], a[href^="tel:"]').forEach(link => {
  link.addEventListener('click', () => {
    const channel = link.href.startsWith('tel:') ? 'phone' : 'line';
    if (typeof gtag === 'function') gtag('event', 'contact_click', { channel, page: 'autumn_winter' });
    if (channel === 'line' && typeof fbq === 'function') {
      fbq('track', 'Lead', { content_name: '秋冬專頁LINE諮詢', content_category: '秋冬旅行' });
    }
  });
});

// 秋冬入口卡片點擊：GA4 cta_click（label＝data-track），用來比較移動／避風／美食哪個入口最常被點
document.querySelectorAll('[data-track]').forEach(link => {
  link.addEventListener('click', () => {
    if (typeof gtag === 'function') gtag('event', 'cta_click', { label: link.dataset.track, page: 'autumn_winter' });
  });
});
