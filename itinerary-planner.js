(function (root, factory) {
  const data = typeof module === 'object' && module.exports
    ? require('./itinerary-planner-data.js')
    : root.PhbayItineraryPlannerData;
  const api = factory(data);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PhbayItineraryPlanner = api;
})(typeof window !== 'undefined' ? window : globalThis, function (data) {
  'use strict';

  if (!data || !Array.isArray(data.CARDS)) throw new Error('itinerary planner data is required');

  const SLOTS = ['morning', 'noon', 'afternoon', 'evening'];
  const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 };
  const AREA_GROUP = {
    magong: 'magong', north: 'north_west', baisha: 'north_west', xiyu: 'north_west',
    south: 'south_east', huxi: 'south_east', offshore: 'offshore'
  };
  const STYLE_CATEGORIES = {
    water: ['water'], island: ['island'], photo: ['attraction'], food: ['food'],
    culture: ['culture'], relax: ['rest']
  };
  const MAIN_CATEGORIES = ['attraction', 'island', 'water', 'culture'];

  function list(value) { return Array.isArray(value) ? value : (value ? [value] : []); }
  function has(value, item) { return list(value).indexOf(item) !== -1; }
  function unique(values) { return values.filter(function (value, index) { return values.indexOf(value) === index; }); }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function dayCount(value) { return ({ '2d1n': 2, '3d2n': 3, '4d3n': 4, '5dplus': 5 })[value] || 3; }
  function avoidsLongBoat(answers) { return has(answers.avoid_preference, 'long_boat') || has(answers.avoid_preference, 'seasick'); }
  function avoidsWater(answers) { return has(answers.avoid_preference, 'water'); }
  function isSlowPace(answers) { return has(answers.avoid_preference, 'rushed') || has(answers.travel_style, 'relax'); }
  function isMain(card) { return card && MAIN_CATEGORIES.indexOf(card.category) !== -1; }

  function normalizeAnswers(answers) {
    answers = answers || {};
    return {
      travel_days: answers.travel_days || '3d2n',
      party_type: answers.party_type || 'couple',
      children_age: list(answers.children_age).length ? list(answers.children_age) : ['none'],
      travel_style: unique(list(answers.travel_style)),
      avoid_preference: unique(list(answers.avoid_preference)),
      arrival_method: answers.arrival_method || 'undecided',
      first_visit: answers.first_visit || 'yes',
      profile_key: answers.profile_key || ''
    };
  }

  function validateCards(cards) {
    const required = [
      'id', 'name', 'category', 'area', 'duration_bucket', 'preferred_slots',
      'indoor_level', 'boat_level', 'walking_level', 'child_friendly',
      'elder_friendly', 'weather_sensitive', 'tide_sensitive', 'fixed_schedule',
      'source_url', 'verified_at'
    ];
    const ids = new Set();
    const errors = [];
    (cards || []).forEach(function (card, index) {
      required.forEach(function (key) {
        if (card[key] === undefined || card[key] === null || card[key] === '') errors.push(`${index}:${card.id || '?'} missing ${key}`);
      });
      if (ids.has(card.id)) errors.push(`${index}:${card.id} duplicate id`);
      ids.add(card.id);
      ['category', 'area', 'duration_bucket', 'indoor_level', 'boat_level', 'walking_level'].forEach(function (key) {
        if (data.ENUMS[key].indexOf(card[key]) === -1) errors.push(`${index}:${card.id} invalid ${key}`);
      });
      if (!Array.isArray(card.preferred_slots) || !card.preferred_slots.length || card.preferred_slots.some(function (slot) { return data.ENUMS.slot.indexOf(slot) === -1; })) {
        errors.push(`${index}:${card.id} invalid preferred_slots`);
      }
      ['child_friendly', 'elder_friendly'].forEach(function (key) {
        if (data.ENUMS.suitability.indexOf(card[key]) === -1) errors.push(`${index}:${card.id} invalid ${key}`);
      });
      if (!/^https:\/\//.test(card.source_url || '')) errors.push(`${index}:${card.id} source_url must be https`);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(card.verified_at || '')) errors.push(`${index}:${card.id} invalid verified_at`);
    });
    return { ok: errors.length === 0, errors: errors };
  }

  function emptyDay(index) {
    return { day_index: index, slots: { morning: [], noon: [], afternoon: [], evening: [] } };
  }

  function createEmptyPlan(days, templateId) {
    const count = Math.max(2, Math.min(5, Number(days) || 3));
    return {
      version: 1,
      template_id: templateId || 'custom',
      days: Array.from({ length: count }, function (_, index) { return emptyDay(index + 1); })
    };
  }

  function assertPlacement(plan, itemId, dayIndex, slot, cardsById) {
    if (!cardsById[itemId]) throw new Error(`unknown itinerary item: ${itemId}`);
    if (!Number.isInteger(dayIndex) || dayIndex < 1 || dayIndex > plan.days.length) throw new Error(`invalid day index: ${dayIndex}`);
    if (SLOTS.indexOf(slot) === -1) throw new Error(`invalid slot: ${slot}`);
  }

  function removeItem(plan, itemId) {
    const next = clone(plan);
    next.days.forEach(function (day) {
      SLOTS.forEach(function (slot) { day.slots[slot] = day.slots[slot].filter(function (id) { return id !== itemId; }); });
    });
    return next;
  }

  function addItem(plan, itemId, dayIndex, slot, position, cardsById) {
    cardsById = cardsById || data.CARD_INDEX;
    assertPlacement(plan, itemId, dayIndex, slot, cardsById);
    const next = removeItem(plan, itemId);
    const items = next.days[dayIndex - 1].slots[slot];
    const at = Number.isInteger(position) ? Math.max(0, Math.min(position, items.length)) : items.length;
    items.splice(at, 0, itemId);
    return next;
  }

  function moveItem(plan, itemId, dayIndex, slot, position, cardsById) {
    return addItem(plan, itemId, dayIndex, slot, position, cardsById);
  }

  function allPlacements(plan, cardsById) {
    cardsById = cardsById || data.CARD_INDEX;
    const rows = [];
    plan.days.forEach(function (day) {
      SLOTS.forEach(function (slot) {
        day.slots[slot].forEach(function (itemId, position) {
          rows.push({ item_id: itemId, card: cardsById[itemId], day_index: day.day_index, slot: slot, position: position });
        });
      });
    });
    return rows;
  }

  function scoreCard(card, answers, options) {
    answers = normalizeAnswers(answers);
    options = options || {};
    let score = 0;
    const rules = [];
    const styles = answers.travel_style;
    styles.forEach(function (style) {
      if ((STYLE_CATEGORIES[style] || []).indexOf(card.category) !== -1) { score += 5; rules.push(`preference_${style}`); }
    });
    if (answers.first_visit === 'yes' && ['attraction', 'culture'].indexOf(card.category) !== -1) { score += 2; rules.push('first_visit_classic'); }
    if ((answers.party_type === 'family' || answers.party_type === 'three_generation') && card.child_friendly === true) { score += 2; rules.push('family_fit'); }
    if (answers.party_type === 'three_generation' && card.elder_friendly === true) { score += 3; rules.push('elder_fit'); }
    if (isSlowPace(answers) && ['short', 'flexible'].indexOf(card.duration_bucket) !== -1) { score += 2; rules.push('slow_pace_fit'); }
    if (avoidsWater(answers) && card.category === 'water') { score -= 100; rules.push('avoid_water'); }
    if (avoidsLongBoat(answers) && card.boat_level === 'long') { score -= 100; rules.push('avoid_long_boat'); }
    if (has(answers.avoid_preference, 'walking') && card.walking_level === 'high') { score -= 30; rules.push('avoid_high_walking'); }
    if (has(answers.avoid_preference, 'sun') && card.indoor_level === 'outdoor' && options.slot === 'noon') { score -= 20; rules.push('avoid_noon_sun'); }
    if (options.slot && card.preferred_slots.indexOf(options.slot) !== -1) { score += 2; rules.push('preferred_slot'); }
    if (options.previousArea && AREA_GROUP[options.previousArea] === AREA_GROUP[card.area]) { score += 2; rules.push('same_area_group'); }
    return { score: score, rule_ids: unique(rules) };
  }

  function place(plan, itemId, dayIndex, slot) {
    return addItem(plan, itemId, dayIndex, slot);
  }

  function selectSouthCard(answers) {
    if (has(answers.travel_style, 'water') && !avoidsWater(answers)) return 'shanshui_beach';
    return 'suogang_stone_pagodas';
  }

  function generateTemplate(rawAnswers) {
    const answers = normalizeAnswers(rawAnswers);
    const count = dayCount(answers.travel_days);
    const wantsIsland = has(answers.travel_style, 'island') || has(answers.travel_style, 'water') || answers.profile_key === 'island_adventure';
    const canUseLongBoat = !avoidsLongBoat(answers) && !avoidsWater(answers);
    const templateId = answers.profile_key || (wantsIsland ? 'island' : (answers.party_type === 'family' || answers.party_type === 'three_generation' ? 'family_slow' : 'classic'));
    let plan = createEmptyPlan(count, templateId);
    const explanations = [];

    plan = place(plan, 'magong_old_town_walk', 1, 'afternoon');
    plan = place(plan, 'magong_food_break', 1, 'evening');
    explanations.push({ rule_id: 'gentle_arrival_day', message: '第一天以馬公短程內容為主，避免抵達後立刻長距離移動。' });

    const middleDays = [];
    for (let index = 2; index < count; index += 1) middleDays.push(index);
    let cursor = 0;
    if (middleDays.length && wantsIsland && canUseLongBoat) {
      plan = place(plan, 'qimei_wangan_day_trip', middleDays[cursor], 'morning');
      cursor += 1;
      explanations.push({ rule_id: 'island_preference_full_day', message: '你偏好跳島或海上活動，因此把完整一天保留給單一離島路線。' });
    } else if (wantsIsland && !canUseLongBoat) {
      explanations.push({ rule_id: 'avoid_boat_filter', message: '你選擇避開玩水、長船程或暈船，因此草案不自動安排長程跳島。' });
    }

    if (cursor < middleDays.length) {
      if (isSlowPace(answers) || answers.party_type === 'family' || answers.party_type === 'three_generation') {
        plan = place(plan, 'tongliang_banyan', middleDays[cursor], 'morning');
        plan = place(plan, 'erkan_settlement', middleDays[cursor], 'afternoon');
        explanations.push({ rule_id: 'north_west_slow_pair', message: '北環採同方向的短停留組合，降低折返與單次步行負擔。' });
      } else {
        plan = place(plan, 'north_loop_highlights', middleDays[cursor], 'morning');
        explanations.push({ rule_id: 'first_visit_north_loop', message: '第一次來訪優先保留一個完整北環主題日。' });
      }
      cursor += 1;
    }

    let southEastAdded = false;
    while (cursor < middleDays.length) {
      const day = middleDays[cursor];
      if (!southEastAdded) {
        plan = place(plan, 'lintou_park', day, 'morning');
        plan = place(plan, selectSouthCard(answers), day, 'afternoon');
        if (isSlowPace(answers) || answers.party_type === 'family' || answers.party_type === 'three_generation') {
          plan = place(plan, 'hotel_rest_buffer', day, 'noon');
        }
        explanations.push({ rule_id: 'south_east_day', message: '湖西與澎南安排在同一個方向，並依偏好選擇海邊、文化或低步行內容。' });
        southEastAdded = true;
      } else if (!avoidsLongBoat(answers) && !avoidsWater(answers)) {
        plan = place(plan, 'inner_sea_cruise', day, 'morning');
        plan = place(plan, 'guanyinting_sunset', day, 'evening');
        explanations.push({ rule_id: 'short_boat_optional_day', message: '多出的完整旅遊日安排短程海上選項，並保留傍晚回到馬公的彈性。' });
      } else {
        if (!has(answers.avoid_preference, 'walking')) plan = place(plan, 'kuibishan_tidal_walk', day, 'morning');
        plan = place(plan, 'guanyinting_sunset', day, 'evening');
        explanations.push({ rule_id: 'land_only_extra_day', message: '避開船程時，以陸上地景與馬公散步補足行程，潮汐項目仍需另行確認。' });
      }
      cursor += 1;
    }

    const lastDay = count;
    if (count === 2) {
      plan = place(plan, 'tongliang_banyan', lastDay, 'morning');
    } else {
      plan = place(plan, 'souvenir_buffer', lastDay, 'morning');
    }
    plan = place(plan, 'departure_transfer_buffer', lastDay, 'afternoon');
    explanations.push({ rule_id: 'departure_buffer', message: '最後一天保留採買與前往機場或港口的交通緩衝。' });

    return {
      plan: plan,
      explanations: explanations,
      warnings: evaluatePlan(plan, answers),
      gaps: detectPreferenceGaps(plan, answers)
    };
  }

  function evaluatePlan(plan, rawAnswers, cardsById) {
    const answers = normalizeAnswers(rawAnswers);
    cardsById = cardsById || data.CARD_INDEX;
    const warnings = [];
    const seen = new Set();
    function warn(type, severity, dayIndex, itemIds, ruleId, message) {
      const key = [type, dayIndex, (itemIds || []).join('|')].join(':');
      if (seen.has(key)) return;
      seen.add(key);
      warnings.push({ id: key, type: type, severity: severity, day_index: dayIndex, item_ids: itemIds || [], rule_id: ruleId, message: message });
    }

    const placements = allPlacements(plan, cardsById);
    placements.forEach(function (row) {
      const card = row.card;
      if (!card) {
        warn('unknown_item', 'high', row.day_index, [row.item_id], 'known_card_required', '這個項目不在已確認的行程資料中。');
        return;
      }
      if (avoidsWater(answers) && card.category === 'water') warn('avoid_water_conflict', 'high', row.day_index, [card.id], 'avoid_water', '你選擇不玩水，但行程中仍有水上活動。');
      if (avoidsLongBoat(answers) && card.boat_level === 'long') warn('long_boat_conflict', 'high', row.day_index, [card.id], 'avoid_long_boat', '你選擇避開長船程或容易暈船，但行程中仍有長程船班活動。');
      if (has(answers.avoid_preference, 'walking') && card.walking_level === 'high') warn('walking_conflict', 'medium', row.day_index, [card.id], 'avoid_high_walking', '這個項目的步行負擔較高，與你希望少走路的條件不一致。');
      if (has(answers.avoid_preference, 'sun') && row.slot === 'noon' && card.indoor_level === 'outdoor') warn('noon_sun', 'medium', row.day_index, [card.id], 'avoid_noon_sun', '你希望避曬，但中午安排了戶外活動。');
      if (card.tide_sensitive) warn('tide_confirmation', 'medium', row.day_index, [card.id], 'confirm_tide', '此項目受潮汐影響，日期確定後仍需查官方資訊。');
      if (card.fixed_schedule) warn('schedule_confirmation', 'low', row.day_index, [card.id], 'confirm_schedule', '此項目有固定時段或交通條件，出發前仍需確認最新安排。');
    });

    plan.days.forEach(function (day) {
      const rows = placements.filter(function (row) { return row.day_index === day.day_index && row.card; });
      const mains = rows.filter(function (row) { return isMain(row.card); });
      const fullDays = mains.filter(function (row) { return row.card.duration_bucket === 'full_day'; });
      if (fullDays.length && mains.length > 1) warn('full_day_overlap', 'high', day.day_index, mains.map(function (row) { return row.item_id; }), 'full_day_exclusive', '全日活動不應再疊加其他主要行程。');
      SLOTS.forEach(function (slot) {
        const fixed = rows.filter(function (row) { return row.slot === slot && row.card.fixed_schedule; });
        if (fixed.length > 1) warn('fixed_schedule_overlap', 'high', day.day_index, fixed.map(function (row) { return row.item_id; }), 'fixed_slot_exclusive', '同一時段有兩個需要固定時間的項目。');
      });
      const areaGroups = unique(mains.map(function (row) { return AREA_GROUP[row.card.area]; }).filter(Boolean));
      if (areaGroups.length > 1) warn('cross_area', 'medium', day.day_index, mains.map(function (row) { return row.item_id; }), 'same_direction_day', '同一天跨越不同方向，可能增加折返與交通時間。');
      if (isSlowPace(answers) && mains.length > 2) warn('overpacked', 'medium', day.day_index, mains.map(function (row) { return row.item_id; }), 'slow_pace_max_two', '你選擇慢遊或不趕行程，建議每天主要活動不超過兩個。');
      const walkingHeavy = mains.filter(function (row) { return ['medium', 'high'].indexOf(row.card.walking_level) !== -1; });
      if ((answers.party_type === 'family' || answers.party_type === 'three_generation') && walkingHeavy.length > 2) {
        warn('mobility_load', 'medium', day.day_index, walkingHeavy.map(function (row) { return row.item_id; }), 'family_walking_limit', '親子或三代同行連續安排較多步行活動，建議加入休息。');
      }
      if (day.day_index === 1 && /planning|undecided/.test(answers.arrival_method) && mains.length > 1) {
        warn('arrival_buffer', 'medium', day.day_index, mains.map(function (row) { return row.item_id; }), 'arrival_day_max_one', '抵達交通尚未確定，第一天建議只留一個主要活動。');
      }
      if (day.day_index === plan.days.length && (mains.length > 1 || fullDays.length > 0)) {
        warn('departure_buffer', 'medium', day.day_index, mains.map(function (row) { return row.item_id; }), 'departure_day_max_one', '最後一天建議只留一個主要活動，避免影響回程。');
      }
    });

    return warnings.sort(function (a, b) {
      return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || a.day_index - b.day_index || a.type.localeCompare(b.type);
    });
  }

  function detectPreferenceGaps(plan, rawAnswers, cardsById) {
    const answers = normalizeAnswers(rawAnswers);
    cardsById = cardsById || data.CARD_INDEX;
    const placements = allPlacements(plan, cardsById).filter(function (row) { return row.card; });
    const warnings = evaluatePlan(plan, answers, cardsById);
    const finalCategories = unique(placements.map(function (row) { return row.card.category; }));
    const declared = answers.travel_style;
    const represented = declared.some(function (style) {
      return (STYLE_CATEGORIES[style] || []).some(function (category) { return finalCategories.indexOf(category) !== -1; });
    });
    return {
      pace_gap: isSlowPace(answers) && warnings.some(function (warning) { return warning.type === 'overpacked'; }),
      boat_gap: avoidsLongBoat(answers) && placements.some(function (row) { return row.card.boat_level !== 'none'; }),
      category_gap: declared.length > 0 && !represented,
      mobility_gap: has(answers.avoid_preference, 'walking') && placements.some(function (row) { return row.card.walking_level === 'high'; }),
      route_gap: warnings.some(function (warning) { return warning.type === 'cross_area'; })
    };
  }

  return {
    SLOTS, AREA_GROUP, STYLE_CATEGORIES, MAIN_CATEGORIES,
    dayCount, normalizeAnswers, validateCards, createEmptyPlan, addItem, removeItem, moveItem,
    allPlacements, scoreCard, generateTemplate, evaluatePlan, detectPreferenceGaps
  };
});
