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
let sentEvent = null;
global.gtag = function () { sentEvent = Array.from(arguments); };
analytics.trackPlanner('planner_export', { export_type: 'print', day_bucket: '4d', item_count_bucket: '7_9', notes: '不可送出' });
delete global.gtag;
assert.strictEqual(sentEvent[1], 'planner_export');
assert(!JSON.stringify(sentEvent).includes('不可送出'));
assert(!('notes' in sentEvent[2]));

const scriptSource = fs.readFileSync('./script.js', 'utf8');
assert(scriptSource.includes("trackPlanner('planner_quote_submitted'"));
assert(scriptSource.indexOf("trackPlanner('planner_quote_submitted'") > scriptSource.indexOf('if (!res.ok || !result.ok)'), '詢價完成事件只能出現在後端成功判斷之後');

function conflictFreePlan() {
  return planner.createEmptyPlan(3, 'warning_diff_test');
}
console.log('itinerary planner P0-B/P0-C/P0-D page and privacy tests: ok');
