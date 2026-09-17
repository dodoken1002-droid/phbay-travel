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

console.log('itinerary quiz rule tests: ok');
