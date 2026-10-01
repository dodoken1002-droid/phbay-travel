'use strict';

const assert = require('assert');
const fs = require('fs');
const planner = require('./itinerary-planner.js');
const page = require('./itinerary-planner-page.js');
const prefill = require('./itinerary-prefill.js');
const analytics = require('./itinerary-analytics.js');

function storage(initial) {
  const values = Object.assign({}, initial || {});
  return {
    getItem(key) { return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null; },
    setItem(key, value) { values[key] = String(value); },
    removeItem(key) { delete values[key]; },
    values
  };
}

const raw = {
  travel_date: '2026-10-10', adults: 2, children: 1, name: '測試旅客', phone: '0912345678',
  travel_days: '4d3n', party_type: 'family', children_age: ['age_4_6'],
  travel_style: ['culture', 'relax'], avoid_preference: ['rushed'],
  arrival_method: 'flight_planning', first_visit: 'yes'
};
const state = page.buildState(raw, 1000);
const serialized = JSON.stringify(state);
assert.strictEqual(state.plan.days.length, 4);
assert(!serialized.includes('2026-10-10'));
assert(!serialized.includes('0912345678'));
assert(!serialized.includes('測試旅客'));
assert(!('adults' in state.answers) && !('children' in state.answers));

const store = storage();
const saved = page.saveState(store, state, 2000);
assert.strictEqual(saved.storage_failed, undefined);
assert.strictEqual(page.loadState(store, 2001).plan.days.length, 4);
assert.strictEqual(page.loadState(store, 2000 + page.MAX_AGE_MS + 1), null, '過期草稿必須移除');
assert.strictEqual(store.getItem(page.STORAGE_KEY), null);

const broken = storage({ [page.STORAGE_KEY]: '{broken' });
assert.strictEqual(page.loadState(broken, 2000), null);

const invalidSavedAt = Object.assign({}, state, { saved_at: '2000' });
assert.strictEqual(page.loadState(storage({ [page.STORAGE_KEY]: JSON.stringify(invalidSavedAt) }), 2001), null, '字串 saved_at 必須丟棄');
const futureSavedAt = Object.assign({}, state, { saved_at: 2001 + page.FUTURE_TOLERANCE_MS + 1 });
assert.strictEqual(page.loadState(storage({ [page.STORAGE_KEY]: JSON.stringify(futureSavedAt) }), 2001), null, '超過容忍值的未來時間必須丟棄');
const invalidTemplate = JSON.parse(JSON.stringify(state));
invalidTemplate.saved_at = 2000;
invalidTemplate.plan.template_id = 'tampered-template';
assert.strictEqual(page.loadState(storage({ [page.STORAGE_KEY]: JSON.stringify(invalidTemplate) }), 2001), null, '未知範本必須丟棄');
const staleItems = JSON.parse(JSON.stringify(state));
staleItems.saved_at = 2000;
const keptId = staleItems.plan.days[0].slots.afternoon[0];
staleItems.plan.days[0].slots.afternoon.push(keptId, 'retired-place', 123);
const cleanedState = page.loadState(storage({ [page.STORAGE_KEY]: JSON.stringify(staleItems) }), 2001);
assert.strictEqual(cleanedState.removed_item_count, 3);
assert.strictEqual(cleanedState.plan.days[0].slots.afternoon.filter(id => id === keptId).length, 1);

let plan = planner.createEmptyPlan(3, 'ui_test');
plan = planner.addItem(plan, 'magong_old_town_walk', 1, 'afternoon');
plan = planner.addItem(plan, 'guanyinting_sunset', 1, 'afternoon');
assert.strictEqual(planner.allPlacements(plan).length, 2);
const movedUp = page.moveWithinSlot(plan, 'guanyinting_sunset', 'up');
assert.deepStrictEqual(movedUp.days[0].slots.afternoon, ['guanyinting_sunset', 'magong_old_town_walk']);
const movedDay = page.moveToDay(movedUp, 'guanyinting_sunset', 'next');
assert.strictEqual(page.findPlacement(movedDay, 'guanyinting_sunset').day_index, 2);
const movedBack = page.moveToDay(movedDay, 'guanyinting_sunset', 'previous');
assert.strictEqual(page.findPlacement(movedBack, 'guanyinting_sunset').day_index, 1);
assert.strictEqual(page.findPlacement(movedBack, 'guanyinting_sunset').slot, 'afternoon');

const restored = page.restorePlanFor(state.answers);
assert.strictEqual(restored.days.length, 4);
const empty = page.emptyPlanFor(state.answers);
assert.strictEqual(planner.allPlacements(empty).length, 0);
assert.strictEqual(empty.days.length, 4);

const quizStore = storage({
  [page.QUIZ_KEY]: JSON.stringify(raw)
});
const quiz = page.quizAnswers(quizStore);
assert.strictEqual(quiz.travel_days, '4d3n');
assert(!('travel_date' in quiz) && !('adults' in quiz) && !('name' in quiz));
const newerQuiz = Object.assign({}, raw, { answered_at: 4000, travel_days: '2d1n' });
const decisionStore = storage();
assert.strictEqual(page.shouldOfferNewQuiz(Object.assign({}, state, { saved_at: 3000 }), newerQuiz, decisionStore), true);
decisionStore.setItem(page.QUIZ_DECISION_KEY, '4000');
assert.strictEqual(page.shouldOfferNewQuiz(Object.assign({}, state, { saved_at: 3000 }), newerQuiz, decisionStore), false, '同一 session 決定後不可重複提示');
assert.deepStrictEqual(page.explicitProfile({ travel_days: '4d3n', answered_at: 1 }), { travel_days: '4d3n' });

assert.strictEqual(page.clearStoredState(storage({ [page.STORAGE_KEY]: '{}' })), true);

const summary = page.buildPlanSummary(state.plan, Object.assign({}, raw, { name: '不可外送', phone: '0900000000' }));
assert(summary.includes('潮旅澎湖線上試排程'));
assert(summary.includes('Day 1'));
assert(summary.includes('仍需由潮旅顧問確認'));
assert(!summary.includes('不可外送') && !summary.includes('0900000000') && !summary.includes('2026-10-10'));
const structure = page.buildStructuredPlan(state.plan, raw);
assert.strictEqual(structure.days.length, 4);
assert.strictEqual(structure.template_id, state.plan.template_id);
assert(structure.days.every(day => day.items.every(item => item.item_id && item.category && item.slot)));
assert(!JSON.stringify(structure).includes('travel_date'));

const prefillStore = storage();
const plannerPayload = page.savePlannerPrefill(prefillStore, state, 3000);
assert.strictEqual(plannerPayload.source, 'itinerary_planner');
assert.strictEqual(JSON.parse(prefillStore.getItem(page.PREFILL_KEY)).created_at, 3000);
const formValues = prefill.formValues(plannerPayload);
assert.strictEqual(formValues.travel_date, '');
assert.strictEqual(formValues.travel_date_end, '');
assert.strictEqual(formValues.people, '', '沒有精確人數時不可猜成 1–2 人');
assert.strictEqual(formValues.tour_id, '');
assert(formValues.notes.includes('Day 1'));
assert.strictEqual(prefill.summaryMarker(plannerPayload), '【潮旅澎湖線上試排程】');
// 瀏覽器的 HTMLElement.dataset 只有 getter；strict mode 下重新指定會拋 TypeError，
// 假元素必須照這個行為模擬，否則測試會放過 `form.dataset = ...` 這種寫法。
const contactForm = {};
const contactFormDataset = {};
Object.defineProperty(contactForm, 'dataset', { get() { return contactFormDataset; }, enumerable: true });
const formMore = { open: false };
const fakeElements = { 'contact-form': contactForm, notes: { value: '' } };
const fakeDocument = {
  getElementById(id) { return fakeElements[id] || null; },
  querySelector(selector) { return selector === '.form-more' ? formMore : null; }
};
prefill.apply(plannerPayload, fakeDocument);
const notesOnce = fakeElements.notes.value;
assert.deepStrictEqual(JSON.parse(fakeElements['contact-form'].dataset.plannerStructure), structure);
prefill.apply(plannerPayload, fakeDocument);
assert.strictEqual(fakeElements.notes.value, notesOnce, '重複觸發預填時不可重複附加試排行程');
assert.deepStrictEqual(JSON.parse(fakeElements['contact-form'].dataset.plannerAnalytics), {
  day_bucket: '4d', completion_bucket: 'complete', template_id: state.plan.template_id
});
assert.strictEqual(formMore.open, true, '帶入試排摘要後要展開備註區，旅客才看得到內容');

let copied = '';
page.copyText('LINE 摘要', { clipboard: { writeText(value) { copied = value; return Promise.resolve(); } } }, null);
assert.strictEqual(copied, 'LINE 摘要');
const printHtml = page.printSheetHtml(state);
assert(printHtml.includes('ip-print-sheet') && printHtml.includes('Day 1'));
assert(!printHtml.includes('0900000000') && !printHtml.includes('2026-10-10'));

// 不需啟動 Flask 或載入資料庫驅動，也能確認頁面路由與資產契約存在。
const appSource = fs.readFileSync('./app.py', 'utf8');
const quizSource = fs.readFileSync('./itinerary-quiz.js', 'utf8');
const cssSource = fs.readFileSync('./itinerary-planner.css', 'utf8');
assert(appSource.includes("@app.route('/penghu-itinerary-recommendations/planner')"));
['itinerary-planner.css', 'itinerary-analytics.js', 'itinerary-planner-data.js', 'itinerary-planner.js', 'itinerary-planner-page.js']
  .forEach(asset => assert(appSource.includes(asset), `路由缺少 ${asset}`));
assert(appSource.includes('id="itinerary-planner-v1"'));
assert(quizSource.includes('/penghu-itinerary-recommendations/planner'));
assert(quizSource.includes('開始試排行程'));
assert(cssSource.includes('@media(max-width:520px)'));
['前一天', '後一天', '恢復推薦', '清空行程'].forEach(label => {
  assert(fs.readFileSync('./itinerary-planner-page.js', 'utf8').includes(label), `缺少非拖曳操作：${label}`);
});
['複製 LINE 摘要', '列印行程', '請潮旅確認並報價'].forEach(label => {
  assert(fs.readFileSync('./itinerary-planner-page.js', 'utf8').includes(label), `缺少 P0-C 操作：${label}`);
});
assert(!fs.readFileSync('./itinerary-planner-page.js', 'utf8').includes('/api/contact'));
assert(!fs.readFileSync('./itinerary-prefill.js', 'utf8').includes('.submit('));
assert(!fs.readFileSync('./itinerary-prefill.js', 'utf8').includes('requestSubmit('));
require('./itinerary-planner-data.js').CARDS.forEach(card => {
  assert(appSource.includes(`'${card.id}': '${card.category}'`), `後端白名單缺少 ${card.id}`);
});

const metrics = page.planMetrics(state.plan, state.answers, 5);
assert.strictEqual(metrics.day_bucket, '4d');
assert.strictEqual(metrics.completion_bucket, 'complete');
assert.strictEqual(metrics.edit_count_bucket, '4_7');
assert(['4_6', '7_9', '10_plus'].includes(metrics.item_count_bucket));
assert.strictEqual(page.countBucket(0, 'warnings'), '0');
assert.strictEqual(page.countBucket(4, 'warnings'), '4_plus');

const beforeWarnings = planner.evaluatePlan(conflictFreePlan(), state.answers);
let warningPlan = conflictFreePlan();
warningPlan = planner.addItem(warningPlan, 'qimei_wangan_day_trip', 1, 'morning');
warningPlan = planner.addItem(warningPlan, 'north_loop_highlights', 1, 'afternoon');
const afterWarnings = planner.evaluatePlan(warningPlan, state.answers);
assert(page.warningDiff(beforeWarnings, afterWarnings).shown.length > 0);
const seenWarnings = new Set(['warning-1']), resolvedWarnings = new Set();
assert.strictEqual(page.markResolution('warning-1', seenWarnings, resolvedWarnings), true);
assert.strictEqual(page.markResolution('warning-1', seenWarnings, resolvedWarnings), false, '同一警告只送一次 resolved');
assert.strictEqual(page.markResolution('never-shown', seenWarnings, resolvedWarnings), false, '未送 shown 不可送 resolved');

const plannerEvents = Object.keys(analytics.PLANNER_EVENT_FIELDS);
['planner_start', 'planner_template_generated', 'planner_item_add', 'planner_item_remove',
  'planner_item_move', 'planner_warning_shown', 'planner_warning_resolved',
  'planner_warning_ignored', 'planner_restore_template', 'planner_complete',
  'planner_export', 'planner_quote_click', 'planner_quote_submitted'].forEach(eventName => {
  assert(plannerEvents.includes(eventName), `缺少事件白名單：${eventName}`);
});
const sanitized = analytics.sanitizePlannerParams('planner_quote_click', {
  day_bucket: '4d', completion_bucket: 'complete', warning_count_bucket: '2_3', edit_count_bucket: '4_7',
  name: '王小明', phone: '0912345678', travel_date: '2026-10-10', adults: 2,
  notes: '自由文字', summary: '完整摘要', plan: { secret: true }, unexpected: 'value'
});
assert.deepStrictEqual(sanitized, {
  day_bucket: '4d', completion_bucket: 'complete', warning_count_bucket: '2_3', edit_count_bucket: '4_7'
});
assert.strictEqual(analytics.sanitizePlannerParams('unknown_event', { day_bucket: '4d' }).day_bucket, undefined);
assert.deepStrictEqual(analytics.sanitizePlannerParams('planner_item_add', {
  item_id: 'magong_old_town_walk', category: 'culture', area: 'magong', day_index: 2,
  slot: 'afternoon', source: 'catalog', notes: '不可送出', item_name: '馬公老城慢走'
}), {
  item_id: 'magong_old_town_walk', category: 'culture', area: 'magong', day_index: '2',
  slot: 'afternoon', source: 'catalog'
});
assert.strictEqual(page.entrySourceFrom('?src=home_quiz', false), 'home_quiz');
assert.strictEqual(page.entrySourceFrom('?src=home_block', false), 'home_block');
assert.strictEqual(page.entrySourceFrom('?src=nav', false), 'nav');
assert.strictEqual(page.entrySourceFrom('?src=bad-value', false), 'direct');
assert.strictEqual(page.entrySourceFrom('?src=nav', true), 'quiz_result', '診斷答案優先於 src');
let sentEvent = null;
global.sessionStorage = storage();
analytics.saveProfile({ travel_days: '3d2n', party_type: 'couple', first_visit: 'yes' });
global.gtag = function () { sentEvent = Array.from(arguments); };
analytics.trackPlanner('planner_export', { export_type: 'print', day_bucket: '4d', item_count_bucket: '7_9', notes: '不可送出' });
assert.strictEqual(sentEvent[1], 'planner_export');
assert(!JSON.stringify(sentEvent).includes('不可送出'));
assert(!('notes' in sentEvent[2]));
assert(!('travel_days' in sentEvent[2]) && !('party_type' in sentEvent[2]) && !('first_visit' in sentEvent[2]), 'planner 事件不可合併診斷 profile');
analytics.track('generate_lead', { source: 'test' });
assert.strictEqual(sentEvent[2].travel_days, '3d2n', '非 planner 事件仍須合併 profile');
delete global.gtag;
delete global.sessionStorage;

const focused = { dataset: { ipAction: 'remove', itemId: 'magong_old_town_walk' }, closest() { return { dataset: { day: '1', slot: 'afternoon' } }; } };
const focusRoot = { ownerDocument: { activeElement: focused }, contains() { return true; } };
const descriptor = page.focusDescriptor(focusRoot);
let focusTarget = '';
const restoredFocusRoot = { querySelector(selector) { return selector.includes('#ip-slot-1-afternoon') ? { focus() { focusTarget = selector; } } : null; } };
page.restoreFocus(restoredFocusRoot, descriptor);
assert.strictEqual(focusTarget, '#ip-slot-1-afternoon', '移除後焦點應退回同一時段標題，不可掉回 body');

assert(!appSource.includes('id="itinerary-planner-v1" aria-live='), '試排器根節點不可設 aria-live');
assert(fs.readFileSync('./itinerary-planner-page.js', 'utf8').includes('刪除這台裝置上的試排資料'));
assert(fs.readFileSync('./itinerary-planner-page.js', 'utf8').includes('重新產生會取代你目前手動調整的行程'));

const scriptSource = fs.readFileSync('./script.js', 'utf8');
assert(scriptSource.includes('data.planner_structure = JSON.parse(form.dataset.plannerStructure)'));
assert(scriptSource.includes("trackPlanner('planner_quote_submitted'"));
assert(scriptSource.indexOf("trackPlanner('planner_quote_submitted'") > scriptSource.indexOf('if (!res.ok || !result.ok)'), '詢價完成事件只能出現在後端成功判斷之後');

function conflictFreePlan() {
  return planner.createEmptyPlan(3, 'warning_diff_test');
}
// ── init() 互動流程：用最小假 DOM 實際點按鈕，驗證確認、復原、刪除與狀態播報的行為 ──
(function plannerInitFlow() {
  const liveRegion = { textContent: '', setAttribute() {} };
  let liveRegionMounted = false;
  const statusEl = { textContent: '' };
  const handlers = {};
  const doc = {
    activeElement: null,
    getElementById(id) {
      if (id === 'itinerary-planner-v1') return rootEl;
      if (id === 'itinerary-planner-status') return liveRegionMounted ? liveRegion : null;
      return null;
    },
    createElement() { return liveRegion; },
    addEventListener() {}
  };
  const rootEl = {
    ownerDocument: doc, innerHTML: '',
    parentNode: { insertBefore() { liveRegionMounted = true; } },
    addEventListener(type, fn) { handlers[type] = fn; },
    contains() { return true; },
    querySelector(selector) { return selector === '.ip-action-status' ? statusEl : null; }
  };
  const events = [];
  let confirmAnswer = true;
  const saved = {};
  ['document', 'localStorage', 'sessionStorage', 'PhbayAnalytics', 'confirm', 'FormData', 'location'].forEach(key => {
    saved[key] = Object.getOwnPropertyDescriptor(globalThis, key);
  });
  const local = storage();
  const session = storage();
  Object.assign(globalThis, {
    document: doc, localStorage: local, sessionStorage: session,
    PhbayAnalytics: { trackPlanner(name, params) { events.push([name, params]); }, saveProfile() {} },
    confirm: () => confirmAnswer,
    FormData: class { constructor(form) { this.values = form.values; } get(key) { return this.values[key]; } },
    location: { search: '?src=nav', href: '' }
  });
  const click = (action, extra) => handlers.click({ target: { closest() { return { dataset: Object.assign({ ipAction: action }, extra || {}) }; } } });
  const submitSettings = values => handlers.submit({ target: { id: 'ip-settings', values }, preventDefault() {} });
  const unusedCard = st => require('./itinerary-planner-data.js').CARDS.find(card => !page.isUsed(st.plan, card.id)).id;

  try {
    const st = page.init();
    assert.strictEqual(events[0][0], 'planner_start');
    assert.strictEqual(events[0][1].entry_source, 'nav', '?src=nav 要記成 nav 入口');

    click('add', { itemId: unusedCard(st) });
    assert.strictEqual(st.edit_count, 1);
    assert(liveRegion.textContent.startsWith('已將 '), '加入景點後要播報結果');

    const beforeSettings = JSON.stringify(st.plan);
    confirmAnswer = false;
    submitSettings({ travel_days: '2d1n', party_type: 'couple', pace: 'balanced' });
    assert.strictEqual(JSON.stringify(st.plan), beforeSettings, '取消確認不可丟掉手動調整');
    assert.strictEqual(st.answers.travel_days, '3d2n');

    confirmAnswer = true;
    submitSettings({ travel_days: '2d1n', party_type: 'couple', pace: 'balanced' });
    assert.strictEqual(st.plan.days.length, 2);
    assert(rootEl.innerHTML.includes('data-ip-action="undo-regenerate"'), '重新產生後要提供復原');
    click('undo-regenerate');
    assert.strictEqual(JSON.stringify(st.plan), beforeSettings, '復原要回到重新產生前的行程');
    assert.strictEqual(st.answers.travel_days, '3d2n');

    submitSettings({ travel_days: '2d1n', party_type: 'couple', pace: 'balanced' });
    click('add', { itemId: unusedCard(st) });
    const afterLaterEdit = JSON.stringify(st.plan);
    assert.strictEqual(st.undo_snapshot, null, '重新產生之後又手動調整，舊的復原點必須作廢');
    assert(!rootEl.innerHTML.includes('data-ip-action="undo-regenerate"'));
    click('undo-regenerate');
    assert.strictEqual(JSON.stringify(st.plan), afterLaterEdit, '作廢的復原點不可蓋掉新的調整');

    st.storage_failed = false;
    session.setItem(page.PREFILL_KEY, '{"x":1}');
    confirmAnswer = false;
    click('delete-local');
    assert.notStrictEqual(local.getItem(page.STORAGE_KEY), null, '取消確認時不可刪除');
    confirmAnswer = true;
    click('delete-local');
    assert.strictEqual(local.getItem(page.STORAGE_KEY), null);
    assert.strictEqual(session.getItem(page.PREFILL_KEY), null, '刪除本機資料也要清掉詢價暫存');
    assert.strictEqual(liveRegion.textContent, '已刪除本機資料');

    session.setItem = () => { throw new Error('quota'); };
    click('quote');
    assert.strictEqual(liveRegion.textContent, '無法暫存行程，請先複製摘要再聯絡我們。', '報價失敗訊息要經由播報區讀出');
  } finally {
    Object.keys(saved).forEach(key => {
      if (saved[key]) Object.defineProperty(globalThis, key, saved[key]); else delete globalThis[key];
    });
  }
})();
console.log('itinerary planner P0-B/P0-C/P0-D page and privacy tests: ok');
