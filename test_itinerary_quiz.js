'use strict';

const assert = require('assert');
const quiz = require('./itinerary-quiz.js');
const analytics = require('./itinerary-analytics.js');

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
assert(family.itinerary[1].title.includes('內海'));

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
