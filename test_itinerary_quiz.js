'use strict';

const assert = require('assert');
const quiz = require('./itinerary-quiz.js');
const analytics = require('./itinerary-analytics.js');
const prefill = require('./itinerary-prefill.js');

function base(overrides) {
  return Object.assign({
    travel_date:'undecided', travel_days:'3d2n', adults:2, children:0,
    children_age:['none'], party_type:'couple', first_visit:'yes',
    travel_style:['photo'], avoid_preference:['rushed'],
    arrival_method:'flight_planning', budget_range:'5k_8k'
  }, overrides || {});
}

assert.strictEqual(quiz.QUESTIONS.length, 10, 'P0 必須維持約 10 題的完整診斷');

const family = quiz.recommend(base({
  children:2, children_age:['age_0_3','age_4_6'], party_type:'family',
  travel_style:['relax'], avoid_preference:['long_boat','rushed']
}));
assert.strictEqual(family.key, 'family_slow');
assert(family.reasons.some(x => x.includes('兒童')));
assert(family.itinerary[1].title.includes('潮間帶'));

const island = quiz.recommend(base({
  first_visit:'no', party_type:'friends', travel_style:['water','island'],
  avoid_preference:[], travel_days:'4d3n'
}));
assert.strictEqual(island.key, 'island_adventure');
assert.strictEqual(island.itinerary.length, 4);

const noWater = quiz.recommend(base({
  first_visit:'no', travel_style:['culture','food'], avoid_preference:['water','seasick']
}));
assert.notStrictEqual(noWater.key, 'island_adventure');
assert(noWater.itinerary[1].title.includes('內海') || noWater.itinerary[1].title.includes('潮間帶'));

const liveTours = [
  {id:2,title:'澎湖經典三日遊',price_display:'NT$ 8,800 起 / 人',is_active:true},
  {id:3,title:'親子海島體驗行程',price_display:'NT$ 9,500 起 / 人',is_active:true},
  {id:5,title:'SUP × 浮潛 × 海洋體驗',price_display:'NT$ 5,800 起 / 人',is_active:true},
  {id:6,title:'澎湖日出快閃之旅',price_display:'NT$ 4,500 起 / 人',is_active:true},
  {id:12,title:'南方四島＋七美深度遊',price_display:'NT$ 1,500 起 / 人',is_active:true},
  {id:17,title:'花火船・海上賞澎湖花火',price_display:'NT$ 380 / 人',is_active:true},
  {id:21,title:'小城故事・內海巡禮',price_display:'2026 試航價 NT$ 1,000 / 人',is_active:true},
  {id:67,title:'澎湖慢旅 4 日',price_display:'線上詢價',is_active:true},
  {id:72,title:'台灣好行環島輕旅',price_display:'交通費 NT$ 560 起',is_active:true},
];

// 五種結果必須使用五個不同的真實 primary，價格來自 API，不是設定檔手抄。
const productIds = Object.keys(quiz.PROFILES).map(key => quiz.resolveRecommendedProduct(key, [], liveTours).tourId);
assert.strictEqual(new Set(productIds).size, 5);
assert.strictEqual(quiz.resolveRecommendedProduct('classic_first', [], liveTours).price, '2026 試航價 NT$ 1,000 / 人');
assert.strictEqual(quiz.resolveRecommendedProduct('classic_first', [], liveTours).cta, '直接預訂');

// 暈船、長船程、不玩水任一條件都不能推薦 boat 商品。
['seasick','long_boat','water'].forEach(avoid => {
  Object.keys(quiz.PROFILES).forEach(key => {
    const product = quiz.resolveRecommendedProduct(key, [avoid], liveTours);
    assert.strictEqual(product.boat, false, `${key}/${avoid} 不得推薦海上商品`);
  });
});

// primary 下架會依序 fallback；無 API 時文案不得假裝仍可直接預訂。
const inactive = liveTours.map(t => t.id === 12 ? Object.assign({}, t, {is_active:false}) : t);
assert.notStrictEqual(quiz.resolveRecommendedProduct('island_adventure', [], inactive).tourId, 12);
assert.strictEqual(quiz.resolveRecommendedProduct('classic_first', [], []).cta, '查看行程與洽詢');

const estimate = quiz.estimatePrice(base({travel_days:'4d3n',adults:2,children:1,arrival_method:'flight_planning'}), quiz.resolveRecommendedProduct('classic_first', [], liveTours));
assert.strictEqual(quiz.PRICE_MODEL.confirmed, false);
assert.strictEqual(estimate.partySize, 3);
assert.strictEqual(estimate.party[0], estimate.perPerson[0] * 3);
assert(estimate.rows.some(row => row.source === '官網即時售價'));
assert.deepStrictEqual(estimate.rows.find(row => row.key === 'product').range, [1000,1000], '年份不能被誤認為價格');

// 微調只建立 sessionStorage payload；日期、人數、交通與摘要由純函式映射，不含姓名電話。
const prefillPayload = quiz.buildPrefillPayload(base({travel_date:'2026-10-10',travel_days:'3d2n',adults:2,children:2,arrival_method:'ferry_booked'}), family, quiz.resolveRecommendedProduct('family_slow', [], liveTours));
const form = prefill.formValues(prefillPayload);
assert.strictEqual(form.travel_date_end, '2026-10-12');
assert.strictEqual(form.people, '3-5');
assert.strictEqual(form.transport, '搭船');
assert(form.notes.includes('30 秒行程診斷'));
assert(!('name' in prefillPayload.answers) && !('phone' in prefillPayload.answers) && !('email' in prefillPayload.answers));

const safe = analytics.sanitizeProfile(Object.assign({}, family.analytics, {
  name:'王小明', phone:'0912345678', travel_date:'2026-10-10', adults:2
}));
assert.deepStrictEqual(Object.keys(safe).sort(), analytics.ALLOWED.slice().sort());
assert(!JSON.stringify(safe).includes('王小明'));
assert(!JSON.stringify(safe).includes('0912345678'));
assert(!JSON.stringify(safe).includes('2026-10-10'));

// 前往機場／港口只能出現在最後一天
['3d2n','4d3n','5dplus'].forEach(days => {
  const plan = quiz.recommend(base({ travel_days:days })).itinerary;
  plan.forEach((d, i) => {
    const leaves = /機場|港口/.test(d.detail);
    assert.strictEqual(leaves, i === plan.length - 1, `${days} 的 ${d.day} 不該${leaves ? '' : '不'}安排離島`);
  });
});

// track() 不論呼叫端傳什麼，都不能把個資或內含日期的訂位代號送進 GA4
const sent = [];
global.gtag = function () { sent.push(Array.from(arguments)); };
const payload = analytics.track('preorder_created', {
  transaction_id:'NH202610031630-0012', booking_ref:'FESTIV20260919-0005', name:'王小明',
  phone:'0912345678', email:'a@b.c', travel_date:'2026-10-10', adults:2, children:1,
  travel_style:['water','island'], item_id:'neihai_cruise'
});
delete global.gtag;
['transaction_id','booking_ref','name','phone','email','travel_date','adults','children']
  .forEach(k => assert(!(k in payload), `${k} 不能送 GA4`));
assert(!JSON.stringify(sent).includes('2026'), '事件內容不能含日期');
assert.strictEqual(payload.travel_style, 'water|island', '診斷維度要與 sessionStorage 格式一致');
assert.strictEqual(payload.item_id, 'neihai_cruise');

console.log('itinerary quiz rule tests: ok');
