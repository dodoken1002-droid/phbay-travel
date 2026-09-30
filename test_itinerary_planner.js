'use strict';

const assert = require('assert');
const data = require('./itinerary-planner-data.js');
const planner = require('./itinerary-planner.js');

function base(overrides) {
  return Object.assign({
    travel_days: '3d2n', party_type: 'couple', children_age: ['none'],
    travel_style: ['photo'], avoid_preference: ['rushed'],
    arrival_method: 'flight_planning', first_visit: 'yes', profile_key: 'classic_first'
  }, overrides || {});
}

const validation = planner.validateCards(data.CARDS);
assert.deepStrictEqual(validation.errors, [], validation.errors.join('\n'));
assert.strictEqual(validation.ok, true);
assert.strictEqual(Object.keys(data.CARD_INDEX).length, data.CARDS.length);
assert(data.CARDS.length >= 12, 'P0-A 需涵蓋足夠的區域與活動類型');
['magong', 'north', 'south', 'huxi', 'xiyu', 'baisha', 'offshore'].forEach(area => {
  assert(data.CARDS.some(card => card.area === area), `缺少 ${area} 卡片`);
});

['2d1n', '3d2n', '4d3n', '5dplus'].forEach(days => {
  const result = planner.generateTemplate(base({ travel_days: days }));
  assert.strictEqual(result.plan.days.length, planner.dayCount(days));
  assert(result.plan.days.every(day => Object.values(day.slots).some(items => items.length)), `${days} 不可產生空白日`);
  assert(result.explanations.length >= 2);
  assert(result.explanations.every(x => x.rule_id && x.message), '每個推薦理由都要有規則 id');
  const departure = planner.allPlacements(result.plan).find(x => x.item_id === 'departure_transfer_buffer');
  assert.strictEqual(departure.day_index, result.plan.days.length, '交通緩衝只能在最後一天');
  assert(!result.warnings.some(x => x.type === 'departure_buffer'), `${days} 的自動草案不應與回程衝突`);
});

const twoDayRows = planner.allPlacements(planner.generateTemplate(base({ travel_days: '2d1n', avoid_preference: [] })).plan);
assert(!twoDayRows.some(x => x.day_index === 2 && x.card.duration_bucket === 'full_day'), '兩天一夜最後一天不可自動安排全日活動');

const fiveDayNoBoat = planner.generateTemplate(base({
  travel_days: '5dplus', travel_style: ['culture', 'relax'],
  avoid_preference: ['water', 'long_boat', 'walking', 'rushed']
}));
assert(fiveDayNoBoat.plan.days.every(day => Object.values(day.slots).some(items => items.length)), '五天陸上版本不可因卡片重複而留下空白日');
assert(!planner.allPlacements(fiveDayNoBoat.plan).some(x => x.card && x.card.boat_level !== 'none'));

const island = planner.generateTemplate(base({
  travel_days: '4d3n', first_visit: 'no', profile_key: 'island_adventure',
  travel_style: ['water', 'island'], avoid_preference: []
}));
const islandRows = planner.allPlacements(island.plan);
assert(islandRows.some(x => x.item_id === 'qimei_wangan_day_trip'));
assert(!island.warnings.some(x => x.type === 'full_day_overlap'), '自動草案不可在全日活動上疊加主要行程');

['water', 'long_boat', 'seasick'].forEach(avoid => {
  const result = planner.generateTemplate(base({
    travel_days: '4d3n', profile_key: 'island_adventure',
    travel_style: ['water', 'island'], avoid_preference: [avoid]
  }));
  const rows = planner.allPlacements(result.plan);
  assert(!rows.some(x => x.card && x.card.boat_level === 'long'), `${avoid} 不得自動安排長船程`);
  if (avoid === 'water') assert(!rows.some(x => x.card && x.card.category === 'water'), '避水不得自動安排水上活動');
  assert(result.explanations.some(x => x.rule_id === 'avoid_boat_filter'));
});

const original = planner.createEmptyPlan(3, 'immutability_test');
const added = planner.addItem(original, 'magong_old_town_walk', 1, 'morning');
assert.strictEqual(original.days[0].slots.morning.length, 0, '純函式不可修改原計畫');
assert.deepStrictEqual(added.days[0].slots.morning, ['magong_old_town_walk']);
const moved = planner.moveItem(added, 'magong_old_town_walk', 2, 'afternoon');
assert.strictEqual(moved.days[0].slots.morning.length, 0);
assert.deepStrictEqual(moved.days[1].slots.afternoon, ['magong_old_town_walk']);
const removed = planner.removeItem(moved, 'magong_old_town_walk');
assert.strictEqual(planner.allPlacements(removed).length, 0);
assert.throws(() => planner.addItem(original, 'not_real', 1, 'morning'), /unknown itinerary item/);
assert.throws(() => planner.addItem(original, 'magong_old_town_walk', 9, 'morning'), /invalid day index/);

let conflict = planner.createEmptyPlan(3, 'conflict_test');
conflict = planner.addItem(conflict, 'qimei_wangan_day_trip', 2, 'morning');
conflict = planner.addItem(conflict, 'shanshui_beach', 2, 'afternoon');
conflict = planner.addItem(conflict, 'kuibishan_tidal_walk', 2, 'noon');
conflict = planner.addItem(conflict, 'erkan_settlement', 2, 'evening');
const conflictAnswers = base({
  party_type: 'three_generation', travel_style: ['relax', 'culture'],
  avoid_preference: ['water', 'long_boat', 'walking', 'sun', 'rushed']
});
const warnings = planner.evaluatePlan(conflict, conflictAnswers);
['avoid_water_conflict', 'long_boat_conflict', 'walking_conflict', 'noon_sun',
  'tide_confirmation', 'schedule_confirmation', 'full_day_overlap', 'cross_area',
  'overpacked', 'mobility_load'].forEach(type => {
  assert(warnings.some(x => x.type === type), `應產生 ${type}`);
});
assert.strictEqual(warnings[0].severity, 'high', '高風險提醒必須排在前面');
assert(warnings.every(x => x.rule_id && x.message), '每個提醒都要能追溯規則');

const gaps = planner.detectPreferenceGaps(conflict, conflictAnswers);
assert.strictEqual(gaps.pace_gap, true);
assert.strictEqual(gaps.boat_gap, true);
assert.strictEqual(gaps.mobility_gap, true);
assert.strictEqual(gaps.route_gap, true);

let categoryPlan = planner.createEmptyPlan(2, 'category_gap');
categoryPlan = planner.addItem(categoryPlan, 'souvenir_buffer', 1, 'morning');
assert.strictEqual(planner.detectPreferenceGaps(categoryPlan, base({ travel_style: ['culture'] })).category_gap, true);
categoryPlan = planner.addItem(categoryPlan, 'magong_old_town_walk', 1, 'afternoon');
assert.strictEqual(planner.detectPreferenceGaps(categoryPlan, base({ travel_style: ['culture'] })).category_gap, false);

const waterScore = planner.scoreCard(data.CARD_INDEX.shanshui_beach, base({ travel_style: ['water'], avoid_preference: [] }), { slot: 'morning' });
const waterAvoidScore = planner.scoreCard(data.CARD_INDEX.shanshui_beach, base({ travel_style: ['water'], avoid_preference: ['water'] }), { slot: 'morning' });
assert(waterScore.score > waterAvoidScore.score);
assert(waterAvoidScore.rule_ids.includes('avoid_water'));

// P0-A 純規則資料不可偷偷放入姓名、電話、Email 或確切旅遊日期欄位。
const serialized = JSON.stringify({ cards: data.CARDS, generated: island });
['name', 'phone', 'email', 'travel_date', 'booking_ref'].forEach(key => {
  if (key === 'name') return; // 卡片的公開顯示名稱是合法的 name 欄位。
  assert(!new RegExp(`"${key}"`, 'i').test(serialized), `${key} 不應出現在規則輸出`);
});

console.log(`itinerary planner P0-A tests: ok (${data.CARDS.length} cards)`);
