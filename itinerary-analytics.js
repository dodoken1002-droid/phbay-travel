(function (root) {
  'use strict';

  const STORAGE_KEY = 'phbay_itinerary_profile_v1';
  const ALLOWED = [
    'travel_days', 'party_type', 'children_age', 'budget_range',
    'travel_style', 'avoid_preference', 'arrival_method', 'first_visit'
  ];

  function cleanValue(value) {
    if (Array.isArray(value)) value = value.join('|');
    if (typeof value === 'boolean') value = value ? 'yes' : 'no';
    return String(value == null ? '' : value).replace(/[^a-z0-9_|-]/gi, '').slice(0, 100);
  }

  function sanitizeProfile(profile) {
    return ALLOWED.reduce(function (out, key) {
      if (profile && profile[key] != null && profile[key] !== '') out[key] = cleanValue(profile[key]);
      return out;
    }, {});
  }

  function saveProfile(profile) {
    const safe = sanitizeProfile(profile);
    try { root.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(safe)); } catch (_) {}
    return safe;
  }

  function loadProfile() {
    try { return sanitizeProfile(JSON.parse(root.sessionStorage.getItem(STORAGE_KEY) || '{}')); }
    catch (_) { return {}; }
  }

  // 可識別個人或行程日期的欄位一律不送 GA4。訂位代號（NH20261003…、FESTIV20260919-…）
  // 內含出發日期，所以 booking_ref／transaction_id 也在封鎖清單。
  const BLOCKED = /^(name|full_name|phone|tel|mobile|email|line_id|travel_date|departure_date|sailing_date|adults|children|party_size|passenger_count|passengers|booking_ref|transaction_id)$/i;

  function track(eventName, params) {
    const extra = {};
    Object.keys(params || {}).forEach(function (key) {
      if (BLOCKED.test(key)) return;
      // 診斷維度不論從哪裡傳入都用同一個格式（陣列 → a|b），GA4 報表才不會分裂成兩種值
      extra[key] = ALLOWED.indexOf(key) !== -1 ? cleanValue(params[key]) : params[key];
    });
    const payload = Object.assign({}, loadProfile(), extra);
    if (typeof root.gtag === 'function') root.gtag('event', eventName, payload);
    return payload;
  }

  const api = { STORAGE_KEY, ALLOWED, BLOCKED, sanitizeProfile, saveProfile, loadProfile, track };
  root.PhbayAnalytics = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
