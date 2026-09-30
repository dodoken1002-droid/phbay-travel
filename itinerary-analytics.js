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

  const PLANNER_EVENT_FIELDS = Object.freeze({
    planner_start: ['planner_version', 'entry_source', 'template_id', 'day_bucket'],
    planner_template_generated: ['template_id', 'itinerary_type', 'item_count_bucket', 'warning_count_bucket'],
    planner_item_add: ['item_id', 'category', 'area', 'day_index', 'slot', 'source'],
    planner_item_remove: ['item_id', 'category', 'area', 'day_index', 'slot', 'source'],
    planner_item_move: ['item_id', 'category', 'from_day', 'to_day', 'from_slot', 'to_slot'],
    planner_warning_shown: ['warning_type', 'severity', 'day_index'],
    planner_warning_resolved: ['warning_type', 'resolution_type', 'day_index'],
    planner_warning_ignored: ['warning_type', 'severity', 'day_index'],
    planner_restore_template: ['template_id', 'edit_count_bucket'],
    planner_complete: ['day_bucket', 'item_count_bucket', 'warning_count_bucket', 'edit_count_bucket'],
    planner_export: ['export_type', 'day_bucket', 'item_count_bucket'],
    planner_line_click: ['day_bucket', 'completion_bucket', 'warning_count_bucket'],
    planner_quote_click: ['day_bucket', 'completion_bucket', 'warning_count_bucket', 'edit_count_bucket'],
    planner_quote_submitted: ['day_bucket', 'completion_bucket', 'template_id']
  });
  const PLANNER_ENUMS = Object.freeze({
    entry_source: ['quiz_result', 'direct'],
    category: ['attraction', 'island', 'water', 'food', 'culture', 'rest', 'transport', 'shopping'],
    area: ['magong', 'north', 'south', 'huxi', 'xiyu', 'baisha', 'offshore'],
    slot: ['morning', 'noon', 'afternoon', 'evening'],
    from_slot: ['morning', 'noon', 'afternoon', 'evening'],
    to_slot: ['morning', 'noon', 'afternoon', 'evening'],
    source: ['catalog', 'board'],
    severity: ['high', 'medium', 'low'],
    resolution_type: ['add', 'remove', 'move', 'restore', 'settings', 'clear'],
    export_type: ['line_copy', 'print'],
    day_bucket: ['2d', '3d', '4d', '5d_plus'],
    item_count_bucket: ['0_3', '4_6', '7_9', '10_plus'],
    edit_count_bucket: ['0', '1_3', '4_7', '8_plus'],
    warning_count_bucket: ['0', '1', '2_3', '4_plus'],
    completion_bucket: ['started', 'partial', 'complete']
  });

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

  function sanitizePlannerParams(eventName, params) {
    const fields = PLANNER_EVENT_FIELDS[eventName];
    if (!fields) return {};
    return fields.reduce(function (out, key) {
      let value = params && params[key];
      if (value == null || value === '') return out;
      if (PLANNER_ENUMS[key]) {
        value = cleanValue(value);
        if (PLANNER_ENUMS[key].indexOf(value) !== -1) out[key] = value;
        return out;
      }
      if (['day_index', 'from_day', 'to_day'].indexOf(key) !== -1) {
        const day = Number(value);
        if (Number.isInteger(day) && day >= 1 && day <= 5) out[key] = String(day);
        return out;
      }
      value = cleanValue(value);
      if (/^[a-z0-9][a-z0-9_|-]{0,63}$/i.test(value)) out[key] = value;
      return out;
    }, {});
  }

  function trackPlanner(eventName, params) {
    if (!PLANNER_EVENT_FIELDS[eventName]) return {};
    return track(eventName, sanitizePlannerParams(eventName, params));
  }

  const api = { STORAGE_KEY, ALLOWED, BLOCKED, PLANNER_EVENT_FIELDS, PLANNER_ENUMS,
    sanitizeProfile, saveProfile, loadProfile, track, sanitizePlannerParams, trackPlanner };
  root.PhbayAnalytics = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
