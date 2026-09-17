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

  function track(eventName, params) {
    const payload = Object.assign({}, loadProfile(), params || {});
    if (typeof root.gtag === 'function') root.gtag('event', eventName, payload);
    return payload;
  }

  const api = { STORAGE_KEY, ALLOWED, sanitizeProfile, saveProfile, loadProfile, track };
  root.PhbayAnalytics = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
