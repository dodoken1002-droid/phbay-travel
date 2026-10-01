(function (root, factory) {
  const planner = typeof module === 'object' && module.exports
    ? require('./itinerary-planner.js')
    : root.PhbayItineraryPlanner;
  const data = typeof module === 'object' && module.exports
    ? require('./itinerary-planner-data.js')
    : root.PhbayItineraryPlannerData;
  const api = factory(root, planner, data);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PhbayItineraryPlannerPage = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root, planner, data) {
  'use strict';

  const STORAGE_KEY = 'phbay_itinerary_plan_v1';
  const QUIZ_KEY = 'phbay_itinerary_answers_v1';
  const PREFILL_KEY = 'phbay_itinerary_prefill_v1';
  const QUIZ_DECISION_KEY = 'phbay_itinerary_quiz_decision_v1';
  const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;
  const FUTURE_TOLERANCE_MS = 5 * 60 * 1000;
  const KNOWN_TEMPLATE_IDS = new Set([
    'custom', 'classic', 'island', 'family_slow', 'classic_first',
    'island_adventure', 'romantic_photo', 'culture_slow'
  ]);
  const CATEGORY_LABELS = {
    all: '全部', attraction: '景點', island: '跳島', water: '玩水', food: '餐食',
    culture: '文化', rest: '休息', transport: '交通', shopping: '採買'
  };
  const SLOT_LABELS = { morning: '早上', noon: '中午', afternoon: '下午', evening: '晚上' };
  const PARTY_LABELS = {
    couple: '情侶', friends: '朋友', family: '親子家庭', three_generation: '三代同堂',
    company: '公司／團體', solo: '一個人'
  };

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char];
    });
  }

  function safeAnswers(raw) { return planner.normalizeAnswers(raw || {}); }

  function buildState(rawAnswers, now) {
    const answers = safeAnswers(rawAnswers);
    const generated = planner.generateTemplate(answers);
    return { version: 1, saved_at: now || Date.now(), edit_count: 0, answers: answers, plan: generated.plan };
  }

  function validPlan(plan) {
    if (!plan || plan.version !== 1 || !Array.isArray(plan.days) || plan.days.length < 2 || plan.days.length > 5) return false;
    return plan.days.every(function (day, index) {
      return day && day.day_index === index + 1 && day.slots && planner.SLOTS.every(function (slot) { return Array.isArray(day.slots[slot]); });
    });
  }

  function sanitizeStoredPlan(plan) {
    if (!validPlan(plan) || !KNOWN_TEMPLATE_IDS.has(plan.template_id)) return null;
    const seen = new Set();
    let removed = 0;
    const safe = {
      version: 1,
      template_id: plan.template_id,
      days: plan.days.map(function (day) {
        const slots = {};
        planner.SLOTS.forEach(function (slot) {
          slots[slot] = day.slots[slot].filter(function (itemId) {
            const keep = typeof itemId === 'string' && !!data.CARD_INDEX[itemId] && !seen.has(itemId);
            if (keep) seen.add(itemId); else removed += 1;
            return keep;
          });
        });
        return { day_index: day.day_index, slots: slots };
      })
    };
    return { plan: safe, removed_count: removed };
  }

  function loadState(storage, now) {
    try {
      const state = JSON.parse(storage.getItem(STORAGE_KEY) || 'null');
      const currentTime = now || Date.now();
      const savedAtValid = state && typeof state.saved_at === 'number' && Number.isFinite(state.saved_at) &&
        state.saved_at > 0 && state.saved_at <= currentTime + FUTURE_TOLERANCE_MS;
      const sanitized = state && sanitizeStoredPlan(state.plan);
      if (!state || state.version !== 1 || !savedAtValid || currentTime - state.saved_at > MAX_AGE_MS || !sanitized) {
        if (state) storage.removeItem(STORAGE_KEY);
        return null;
      }
      state.answers = safeAnswers(state.answers);
      state.edit_count = Math.max(0, Number(state.edit_count) || 0);
      state.plan = sanitized.plan;
      state.removed_item_count = sanitized.removed_count;
      return state;
    } catch (_) { try { storage.removeItem(STORAGE_KEY); } catch (_) {} return null; }
  }

  function saveState(storage, state, now) {
    const safe = {
      version: 1,
      saved_at: now || Date.now(),
      edit_count: Math.max(0, Number(state.edit_count) || 0),
      answers: safeAnswers(state.answers),
      plan: state.plan
    };
    try { storage.setItem(STORAGE_KEY, JSON.stringify(safe)); return safe; }
    catch (_) { return Object.assign({}, safe, { storage_failed: true }); }
  }

  function clearStoredState(storage) {
    try { storage.removeItem(STORAGE_KEY); return true; }
    catch (_) { return false; }
  }

  function quizAnswers(storage) {
    try { return safeAnswers(JSON.parse(storage.getItem(QUIZ_KEY) || '{}')); }
    catch (_) { return safeAnswers({}); }
  }

  function quizPayload(storage) {
    try {
      const raw = JSON.parse(storage.getItem(QUIZ_KEY) || '{}');
      return raw && typeof raw === 'object' ? raw : {};
    } catch (_) { return {}; }
  }

  function explicitProfile(raw) {
    const keys = ['travel_days', 'party_type', 'children_age', 'budget_range', 'travel_style', 'avoid_preference', 'arrival_method', 'first_visit'];
    return keys.reduce(function (out, key) {
      if (raw && Object.prototype.hasOwnProperty.call(raw, key) && raw[key] != null && raw[key] !== '') out[key] = raw[key];
      return out;
    }, {});
  }

  function answersEqual(left, right) {
    return JSON.stringify(safeAnswers(left)) === JSON.stringify(safeAnswers(right));
  }

  function shouldOfferNewQuiz(stored, rawQuiz, sessionStorage) {
    if (!stored || !rawQuiz || typeof rawQuiz.answered_at !== 'number' || !Number.isFinite(rawQuiz.answered_at)) return false;
    if (rawQuiz.answered_at <= stored.saved_at || answersEqual(rawQuiz, stored.answers)) return false;
    try { if (String(sessionStorage.getItem(QUIZ_DECISION_KEY) || '') === String(rawQuiz.answered_at)) return false; } catch (_) {}
    return true;
  }

  function entrySourceFrom(search, hasQuizAnswers) {
    if (hasQuizAnswers) return 'quiz_result';
    let source = '';
    try { source = new URLSearchParams(search || '').get('src') || ''; } catch (_) {}
    return ['home_quiz', 'home_block', 'nav'].indexOf(source) !== -1 ? source : 'direct';
  }

  function findPlacement(plan, itemId) {
    return planner.allPlacements(plan).find(function (row) { return row.item_id === itemId; }) || null;
  }

  function chooseSlot(card, day) {
    const preferred = card.preferred_slots || planner.SLOTS;
    return preferred.slice().sort(function (a, b) { return day.slots[a].length - day.slots[b].length; })[0] || 'morning';
  }

  function addToDay(plan, itemId, dayIndex) {
    const card = data.CARD_INDEX[itemId];
    if (!card) return plan;
    const day = plan.days[dayIndex - 1];
    if (!day) return plan;
    return planner.addItem(plan, itemId, dayIndex, chooseSlot(card, day));
  }

  function moveWithinSlot(plan, itemId, direction) {
    const row = findPlacement(plan, itemId);
    if (!row) return plan;
    const items = plan.days[row.day_index - 1].slots[row.slot];
    const nextIndex = row.position + (direction === 'up' ? -1 : 1);
    if (nextIndex < 0 || nextIndex >= items.length) return plan;
    return planner.moveItem(plan, itemId, row.day_index, row.slot, nextIndex);
  }

  function moveToDay(plan, itemId, direction) {
    const row = findPlacement(plan, itemId);
    if (!row) return plan;
    const nextDay = row.day_index + (direction === 'previous' ? -1 : 1);
    if (nextDay < 1 || nextDay > plan.days.length) return plan;
    return planner.moveItem(plan, itemId, nextDay, row.slot);
  }

  function emptyPlanFor(answers) {
    return planner.createEmptyPlan(planner.dayCount(answers.travel_days), 'custom');
  }

  function restorePlanFor(answers) { return planner.generateTemplate(answers).plan; }

  function isUsed(plan, itemId) { return !!findPlacement(plan, itemId); }

  function countBucket(count, kind) {
    count = Math.max(0, Number(count) || 0);
    if (kind === 'items') return count <= 3 ? '0_3' : count <= 6 ? '4_6' : count <= 9 ? '7_9' : '10_plus';
    if (kind === 'edits') return count === 0 ? '0' : count <= 3 ? '1_3' : count <= 7 ? '4_7' : '8_plus';
    return count === 0 ? '0' : count === 1 ? '1' : count <= 3 ? '2_3' : '4_plus';
  }

  function planMetrics(plan, answers, editCount) {
    const items = planner.allPlacements(plan);
    const warnings = planner.evaluatePlan(plan, answers);
    const complete = plan.days.length > 0 && plan.days.every(function (day) {
      return planner.SLOTS.some(function (slot) { return day.slots[slot].length > 0; });
    });
    return {
      day_bucket: plan.days.length >= 5 ? '5d_plus' : `${plan.days.length}d`,
      item_count_bucket: countBucket(items.length, 'items'),
      warning_count_bucket: countBucket(warnings.length, 'warnings'),
      edit_count_bucket: countBucket(editCount, 'edits'),
      completion_bucket: items.length === 0 ? 'started' : complete ? 'complete' : 'partial',
      complete: complete,
      item_count: items.length,
      warnings: warnings
    };
  }

  function warningDiff(before, after) {
    const beforeIds = new Set((before || []).map(function (warning) { return warning.id; }));
    const afterIds = new Set((after || []).map(function (warning) { return warning.id; }));
    return {
      shown: (after || []).filter(function (warning) { return !beforeIds.has(warning.id); }),
      resolved: (before || []).filter(function (warning) { return !afterIds.has(warning.id); })
    };
  }

  function markResolution(warningId, seenWarningIds, resolvedWarningIds) {
    if (!seenWarningIds.has(warningId) || resolvedWarningIds.has(warningId)) return false;
    resolvedWarningIds.add(warningId);
    return true;
  }

  function itemEventParams(itemId, row, source) {
    const card = data.CARD_INDEX[itemId];
    if (!card || !row) return {};
    return { item_id: itemId, category: card.category, area: card.area, day_index: row.day_index, slot: row.slot, source: source };
  }

  function trackPlanner(analytics, eventName, params) {
    return analytics && typeof analytics.trackPlanner === 'function' ? analytics.trackPlanner(eventName, params) : {};
  }

  function dayLabel(answers) {
    return ({ '2d1n': '2 天 1 夜', '3d2n': '3 天 2 夜', '4d3n': '4 天 3 夜', '5dplus': '5 天以上' })[answers.travel_days] || '天數未定';
  }

  function buildPlanSummary(plan, rawAnswers) {
    const answers = safeAnswers(rawAnswers);
    const lines = [
      '【潮旅澎湖線上試排程】',
      `${dayLabel(answers)}｜${PARTY_LABELS[answers.party_type] || '同行類型未定'}`
    ];
    plan.days.forEach(function (day) {
      lines.push('', `Day ${day.day_index}`);
      let count = 0;
      planner.SLOTS.forEach(function (slot) {
        day.slots[slot].forEach(function (itemId) {
          const card = data.CARD_INDEX[itemId];
          if (!card) return;
          lines.push(`${SLOT_LABELS[slot]}｜${card.name}`);
          count += 1;
        });
      });
      if (!count) lines.push('尚未安排');
    });
    const warnings = planner.evaluatePlan(plan, answers).filter(function (warning) { return warning.severity !== 'low'; });
    if (warnings.length) {
      lines.push('', '希望顧問協助確認：');
      uniqueStrings(warnings.map(function (warning) { return warning.message; })).slice(0, 5).forEach(function (message) { lines.push(`- ${message}`); });
    }
    lines.push('', '此為旅客自行試排，船班、潮汐、天候、營業、交通與價格仍需由潮旅顧問確認。');
    return lines.join('\n');
  }

  function uniqueStrings(values) {
    return values.filter(function (value, index) { return values.indexOf(value) === index; });
  }

  function buildStructuredPlan(plan, rawAnswers) {
    const answers = safeAnswers(rawAnswers);
    return {
      version: 1,
      template_id: plan.template_id || 'custom',
      travel_days: answers.travel_days,
      party_type: answers.party_type,
      travel_style: answers.travel_style,
      avoid_preference: answers.avoid_preference,
      days: plan.days.map(function (day) {
        return {
          day_index: day.day_index,
          items: planner.SLOTS.reduce(function (rows, slot) {
            day.slots[slot].forEach(function (itemId) {
              const card = data.CARD_INDEX[itemId];
              if (card) rows.push({ item_id: itemId, category: card.category, slot: slot });
            });
            return rows;
          }, [])
        };
      }),
      warning_types: uniqueStrings(planner.evaluatePlan(plan, answers).map(function (warning) { return warning.type; }))
    };
  }

  function buildPlannerPrefillPayload(state, now) {
    return {
      version: 1,
      created_at: now || Date.now(),
      source: 'itinerary_planner',
      answers: safeAnswers(state.answers),
      planner: {
        summary: buildPlanSummary(state.plan, state.answers),
        structure: buildStructuredPlan(state.plan, state.answers)
      }
    };
  }

  function savePlannerPrefill(storage, state, now) {
    const payload = buildPlannerPrefillPayload(state, now);
    try { storage.setItem(PREFILL_KEY, JSON.stringify(payload)); return payload; }
    catch (_) { return null; }
  }

  function copyText(text, navigatorObject, documentObject) {
    if (navigatorObject && navigatorObject.clipboard && typeof navigatorObject.clipboard.writeText === 'function') {
      return navigatorObject.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        const textarea = documentObject.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        documentObject.body.appendChild(textarea);
        textarea.select();
        const copied = documentObject.execCommand('copy');
        documentObject.body.removeChild(textarea);
        if (!copied) throw new Error('copy command failed');
        resolve();
      } catch (error) { reject(error); }
    });
  }

  function printSheetHtml(state) {
    const days = state.plan.days.map(function (day) {
      const rows = planner.SLOTS.reduce(function (items, slot) {
        day.slots[slot].forEach(function (itemId) {
          const card = data.CARD_INDEX[itemId];
          if (card) items.push(`<li><strong>${esc(SLOT_LABELS[slot])}</strong><span>${esc(card.name)}</span></li>`);
        });
        return items;
      }, []);
      return `<section><h2>Day ${day.day_index}</h2>${rows.length ? `<ul>${rows.join('')}</ul>` : '<p>尚未安排</p>'}</section>`;
    }).join('');
    return `<article class="ip-print-sheet"><header><p>潮旅國際旅行社</p><h1>澎湖行程試排</h1><div>${esc(dayLabel(state.answers))}｜${esc(PARTY_LABELS[state.answers.party_type] || '同行類型未定')}</div></header>${days}<footer>此為旅客自行試排，船班、潮汐、天候、營業、交通與價格仍需由潮旅顧問確認。</footer></article>`;
  }

  function itemHtml(itemId, plan) {
    const card = data.CARD_INDEX[itemId];
    const row = findPlacement(plan, itemId);
    if (!card || !row) return '';
    const slotItems = plan.days[row.day_index - 1].slots[row.slot];
    return `<article class="ip-item" data-item-id="${esc(itemId)}">
      <div class="ip-item-copy"><strong>${esc(card.name)}</strong><small>${esc(CATEGORY_LABELS[card.category])}・${esc(card.duration_bucket === 'full_day' ? '全天' : card.duration_bucket === 'half_day' ? '半天' : card.duration_bucket === 'short' ? '短停留' : '彈性')}</small></div>
      <div class="ip-item-actions" aria-label="調整 ${esc(card.name)}">
        <button type="button" data-ip-action="up" data-item-id="${esc(itemId)}" ${row.position === 0 ? 'disabled' : ''} aria-label="往上移動 ${esc(card.name)}">↑</button>
        <button type="button" data-ip-action="down" data-item-id="${esc(itemId)}" ${row.position === slotItems.length - 1 ? 'disabled' : ''} aria-label="往下移動 ${esc(card.name)}">↓</button>
        <button type="button" data-ip-action="previous-day" data-item-id="${esc(itemId)}" ${row.day_index === 1 ? 'disabled' : ''} aria-label="把 ${esc(card.name)} 移到第 ${Math.max(1, row.day_index - 1)} 天">前一天</button>
        <button type="button" data-ip-action="next-day" data-item-id="${esc(itemId)}" ${row.day_index === plan.days.length ? 'disabled' : ''} aria-label="把 ${esc(card.name)} 移到第 ${Math.min(plan.days.length, row.day_index + 1)} 天">後一天</button>
        <button type="button" class="ip-remove" data-ip-action="remove" data-item-id="${esc(itemId)}" aria-label="移除 ${esc(card.name)}">移除</button>
      </div>
    </article>`;
  }

  function slotHtml(day, slot, plan) {
    const items = day.slots[slot];
    return `<section class="ip-slot" data-day="${day.day_index}" data-slot="${esc(slot)}" aria-labelledby="ip-slot-${day.day_index}-${slot}">
      <h3 id="ip-slot-${day.day_index}-${slot}" tabindex="-1">${esc(SLOT_LABELS[slot])}</h3>
      <div class="ip-slot-items">${items.length ? items.map(function (id) { return itemHtml(id, plan); }).join('') : '<p class="ip-empty-slot">尚未安排</p>'}</div>
    </section>`;
  }

  function warningHtml(warning) {
    const messageId = `ip-warning-${String(warning.id).replace(/[^a-z0-9_-]/gi, '-')}`;
    return `<li class="ip-warning ip-warning-${esc(warning.severity)}"><strong>${warning.severity === 'high' ? '需要調整' : warning.severity === 'medium' ? '建議留意' : '出發前確認'}</strong><span id="${esc(messageId)}">${esc(warning.message)}</span><button type="button" data-ip-action="ignore-warning" data-warning-id="${esc(warning.id)}" aria-describedby="${esc(messageId)}">先保留</button></li>`;
  }

  function catalogHtml(state, category) {
    const cards = data.CARDS.filter(function (card) { return category === 'all' || card.category === category; });
    const filters = Object.keys(CATEGORY_LABELS).map(function (key) {
      return `<button type="button" data-ip-action="filter" data-category="${esc(key)}" aria-pressed="${key === category ? 'true' : 'false'}">${esc(CATEGORY_LABELS[key])}</button>`;
    }).join('');
    const cardRows = cards.map(function (card) {
      const used = isUsed(state.plan, card.id);
      const flags = [card.weather_sensitive ? '看天候' : '', card.tide_sensitive ? '看潮汐' : '', card.boat_level !== 'none' ? '含船程' : '', card.walking_level === 'high' ? '步行較多' : ''].filter(Boolean);
      return `<article class="ip-catalog-card">
        <div><strong>${esc(card.name)}</strong><small>${esc(CATEGORY_LABELS[card.category])}・${esc(card.area)}</small>${flags.length ? `<p>${flags.map(function (flag) { return `<span>${esc(flag)}</span>`; }).join('')}</p>` : ''}</div>
        <button type="button" data-ip-action="add" data-item-id="${esc(card.id)}" ${used ? 'disabled' : ''} aria-label="${esc(used ? `${card.name} 已加入` : `把 ${card.name} 加入第 ${state.current_day} 天`)}">${used ? '已加入' : '加入這一天'}</button>
      </article>`;
    }).join('');
    return `<section class="ip-catalog" aria-labelledby="ip-catalog-title"><div class="ip-section-head"><div><p>行程素材</p><h2 id="ip-catalog-title">加入第 ${state.current_day} 天</h2></div></div><div class="ip-filters" aria-label="篩選行程類型">${filters}</div><div class="ip-catalog-list">${cardRows}</div></section>`;
  }

  function focusDescriptor(rootEl) {
    const active = rootEl.ownerDocument && rootEl.ownerDocument.activeElement;
    if (!active || !rootEl.contains(active)) return null;
    const slot = active.closest && active.closest('.ip-slot');
    return {
      action: active.dataset && active.dataset.ipAction,
      itemId: active.dataset && active.dataset.itemId,
      day: active.dataset && active.dataset.day,
      category: active.dataset && active.dataset.category,
      warningId: active.dataset && active.dataset.warningId,
      slotDay: slot && slot.dataset.day,
      slotName: slot && slot.dataset.slot
    };
  }

  function restoreFocus(rootEl, descriptor) {
    if (!descriptor) return;
    const selectors = [];
    if (descriptor.action) {
      let selector = `[data-ip-action="${descriptor.action}"]`;
      if (descriptor.itemId) selector += `[data-item-id="${descriptor.itemId}"]`;
      else if (descriptor.day) selector += `[data-day="${descriptor.day}"]`;
      else if (descriptor.category) selector += `[data-category="${descriptor.category}"]`;
      else if (descriptor.warningId) selector += `[data-warning-id="${descriptor.warningId}"]`;
      selectors.push(selector);
    }
    if (descriptor.slotDay && descriptor.slotName) selectors.push(`#ip-slot-${descriptor.slotDay}-${descriptor.slotName}`);
    selectors.push('[data-ip-day-heading]');
    const target = selectors.map(function (selector) { return rootEl.querySelector(selector); })
      .find(function (element) { return element && !element.disabled; });
    if (target && typeof target.focus === 'function') target.focus({ preventScroll: true });
  }

  function render(rootEl, state) {
    const previousFocus = focusDescriptor(rootEl);
    const current = state.plan.days[state.current_day - 1] || state.plan.days[0];
    state.current_day = current.day_index;
    const ignored = new Set(state.ignored_warning_ids || []);
    const warnings = planner.evaluatePlan(state.plan, state.answers).filter(function (warning) { return warning.day_index === state.current_day && !ignored.has(warning.id); });
    const tabs = state.plan.days.map(function (day) {
      const count = planner.SLOTS.reduce(function (total, slot) { return total + day.slots[slot].length; }, 0);
      return `<button type="button" data-ip-action="day" data-day="${day.day_index}" aria-current="${day.day_index === state.current_day ? 'page' : 'false'}">Day ${day.day_index}<small>${count} 項</small></button>`;
    }).join('');
    const dayOptions = [['2d1n', '2 天 1 夜'], ['3d2n', '3 天 2 夜'], ['4d3n', '4 天 3 夜'], ['5dplus', '5 天以上']].map(function (row) { return `<option value="${row[0]}" ${state.answers.travel_days === row[0] ? 'selected' : ''}>${row[1]}</option>`; }).join('');
    const partyOptions = Object.keys(PARTY_LABELS).map(function (key) { return `<option value="${key}" ${state.answers.party_type === key ? 'selected' : ''}>${esc(PARTY_LABELS[key])}</option>`; }).join('');
    const pace = state.answers.travel_style.indexOf('relax') !== -1 || state.answers.avoid_preference.indexOf('rushed') !== -1 ? 'slow' : 'balanced';
    const quizChoice = state.pending_quiz_answers ? `<section class="ip-notice" aria-labelledby="ip-new-quiz-title"><strong id="ip-new-quiz-title">偵測到新的診斷結果</strong><span>要用新結果重新產生，或繼續上次的行程？</span><div><button type="button" data-ip-action="use-new-quiz">用新結果重新產生</button><button type="button" data-ip-action="keep-stored">繼續上次的行程</button></div></section>` : '';
    rootEl.innerHTML = `${quizChoice}<header class="ip-hero">
      <p>澎湖線上試排程・目前為測試版</p><h1>先排出想玩的樣子，再請顧問協助</h1>
      <div>所有內容都是試排，船班、潮汐、天候、營業與價格仍需再次確認。</div>
      <span class="ip-save-status">${esc(state.storage_failed ? '此瀏覽器無法儲存，關閉頁面後可能遺失' : state.notice || (state.removed_item_count ? '部分景點已下架，已從行程移除' : '已儲存在這台裝置'))}${state.undo_snapshot ? '・<button type="button" data-ip-action="undo-regenerate">復原</button>' : ''}</span>
    </header>
    <form class="ip-settings" id="ip-settings">
      <label>旅遊天數<select name="travel_days">${dayOptions}</select></label>
      <label>同行類型<select name="party_type">${partyOptions}</select></label>
      <label>行程節奏<select name="pace"><option value="balanced" ${pace === 'balanced' ? 'selected' : ''}>適中</option><option value="slow" ${pace === 'slow' ? 'selected' : ''}>慢遊、不趕</option></select></label>
      <button type="submit">套用並重新產生</button>
    </form>
    <div class="ip-day-tabs" role="navigation" aria-label="選擇旅行日">${tabs}</div>
    <div class="ip-output-actions" aria-label="輸出與諮詢">
      <button type="button" data-ip-action="copy">複製 LINE 摘要</button>
      <button type="button" data-ip-action="print">列印行程</button>
      <button type="button" class="ip-quote" data-ip-action="quote">請潮旅確認並報價</button>
      <span class="ip-action-status"></span>
    </div>
    <div class="ip-layout"><main class="ip-board">
      <div class="ip-section-head"><div><p>目前編輯</p><h2 data-ip-day-heading tabindex="-1">Day ${state.current_day}</h2></div><div class="ip-board-actions"><button type="button" data-ip-action="restore">恢復推薦</button><button type="button" class="ip-clear" data-ip-action="clear">清空行程</button><button type="button" class="ip-delete-local" data-ip-action="delete-local">刪除這台裝置上的試排資料</button></div></div>
      <div class="ip-slots">${planner.SLOTS.map(function (slot) { return slotHtml(current, slot, state.plan); }).join('')}</div>
      <section class="ip-warnings" aria-labelledby="ip-warning-title"><h2 id="ip-warning-title">這一天的提醒</h2>${warnings.length ? `<ul>${warnings.map(warningHtml).join('')}</ul>` : '<p>目前沒有發現明顯衝突；出發前仍要確認即時資訊。</p>'}</section>
    </main>${catalogHtml(state, state.category)}</div>${printSheetHtml(state)}`;
    restoreFocus(rootEl, previousFocus);
  }

  function ensureLiveRegion(rootEl) {
    const doc = rootEl.ownerDocument;
    let region = doc.getElementById('itinerary-planner-status');
    if (!region) {
      region = doc.createElement('div');
      region.id = 'itinerary-planner-status';
      region.className = 'sr-only';
      region.setAttribute('role', 'status');
      region.setAttribute('aria-live', 'polite');
      rootEl.parentNode.insertBefore(region, rootEl);
    }
    return region;
  }

  function init() {
    const rootEl = root.document && root.document.getElementById('itinerary-planner-v1');
    if (!rootEl) return null;
    const storage = root.localStorage;
    const stored = loadState(storage);
    const rawQuiz = quizPayload(root.sessionStorage);
    let state = stored || buildState(rawQuiz);
    state.current_day = 1;
    state.category = 'all';
    state.storage_failed = false;
    state.ignored_warning_ids = [];
    state.explicit_profile = explicitProfile(rawQuiz);
    if (shouldOfferNewQuiz(stored, rawQuiz, root.sessionStorage)) state.pending_quiz_answers = rawQuiz;
    const analytics = root.PhbayAnalytics;
    const seenWarningIds = new Set();
    const resolvedWarningIds = new Set();
    const liveRegion = ensureLiveRegion(rootEl);
    let completionTracked = !!stored && planMetrics(state.plan, state.answers, state.edit_count).complete;
    if (analytics && typeof analytics.saveProfile === 'function' && Object.keys(state.explicit_profile).length) analytics.saveProfile(state.explicit_profile);

    function emit(eventName, params) { return trackPlanner(analytics, eventName, params); }

    function emitWarnings(warnings) {
      (warnings || []).forEach(function (warning) {
        if (seenWarningIds.has(warning.id)) return;
        seenWarningIds.add(warning.id);
        emit('planner_warning_shown', { warning_type: warning.type, severity: warning.severity, day_index: warning.day_index });
      });
    }

    function emitTemplate() {
      const metrics = planMetrics(state.plan, state.answers, state.edit_count);
      emit('planner_template_generated', {
        template_id: state.plan.template_id || 'custom',
        itinerary_type: state.answers.profile_key || state.plan.template_id || 'custom',
        item_count_bucket: metrics.item_count_bucket,
        warning_count_bucket: metrics.warning_count_bucket
      });
    }

    function emitComplete(metrics) {
      if (completionTracked || !metrics.complete) return;
      completionTracked = true;
      emit('planner_complete', {
        day_bucket: metrics.day_bucket,
        item_count_bucket: metrics.item_count_bucket,
        warning_count_bucket: metrics.warning_count_bucket,
        edit_count_bucket: metrics.edit_count_bucket
      });
    }

    function announce(message) {
      liveRegion.textContent = '';
      if (message) liveRegion.textContent = message;
    }

    function persistAndRender(message) {
      const saved = saveState(storage, state);
      state.saved_at = saved.saved_at;
      state.storage_failed = !!saved.storage_failed;
      render(rootEl, state);
      announce(message);
    }

    function applyPlanChange(nextPlan, resolutionType, eventName, eventParams, message) {
      if (resolutionType !== 'settings') state.undo_snapshot = null;
      const before = planMetrics(state.plan, state.answers, state.edit_count);
      state.plan = nextPlan;
      state.edit_count += 1;
      const after = planMetrics(state.plan, state.answers, state.edit_count);
      if (eventName) emit(eventName, eventParams || {});
      const changes = warningDiff(before.warnings, after.warnings);
      emitWarnings(changes.shown);
      changes.resolved.forEach(function (warning) {
        if (!markResolution(warning.id, seenWarningIds, resolvedWarningIds)) return;
        emit('planner_warning_resolved', { warning_type: warning.type, resolution_type: resolutionType, day_index: warning.day_index });
      });
      emitComplete(after);
      persistAndRender(message);
    }

    function confirmReplacement(message) {
      return state.edit_count <= 0 || typeof root.confirm !== 'function' || root.confirm(message);
    }

    function rememberQuizDecision() {
      if (!state.pending_quiz_answers) return;
      try { root.sessionStorage.setItem(QUIZ_DECISION_KEY, String(state.pending_quiz_answers.answered_at)); } catch (_) {}
    }

    rootEl.addEventListener('click', function (event) {
      const button = event.target.closest('[data-ip-action]');
      if (!button || !rootEl.contains(button)) return;
      const action = button.dataset.ipAction;
      const itemId = button.dataset.itemId;
      if (action === 'use-new-quiz') {
        const nextAnswers = state.pending_quiz_answers;
        rememberQuizDecision();
        const nextState = buildState(nextAnswers);
        state.answers = nextState.answers;
        state.plan = nextState.plan;
        state.edit_count = 0;
        state.current_day = 1;
        state.pending_quiz_answers = null;
        state.undo_snapshot = null;
        state.explicit_profile = explicitProfile(nextAnswers);
        state.notice = '已使用新的診斷結果重新產生';
        if (analytics && typeof analytics.saveProfile === 'function') analytics.saveProfile(state.explicit_profile);
        emitTemplate();
        persistAndRender('已使用新的診斷結果重新產生行程');
        return;
      }
      if (action === 'keep-stored') {
        rememberQuizDecision();
        state.pending_quiz_answers = null;
        state.notice = '已保留上次的行程';
        render(rootEl, state);
        announce('已保留上次的行程');
        return;
      }
      if (action === 'undo-regenerate' && state.undo_snapshot) {
        const snapshot = state.undo_snapshot;
        state.answers = snapshot.answers;
        state.plan = snapshot.plan;
        state.edit_count = snapshot.edit_count;
        state.undo_snapshot = null;
        state.notice = '已復原重新產生前的行程';
        persistAndRender('已復原重新產生前的行程');
        return;
      }
      if (action === 'copy') {
        const status = rootEl.querySelector('.ip-action-status');
        copyText(buildPlanSummary(state.plan, state.answers), root.navigator, root.document)
          .then(function () {
            const metrics = planMetrics(state.plan, state.answers, state.edit_count);
            emit('planner_export', { export_type: 'line_copy', day_bucket: metrics.day_bucket, item_count_bucket: metrics.item_count_bucket });
            status.textContent = '已複製，可貼到 LINE。';
            announce(status.textContent);
          })
          .catch(function () { status.textContent = '無法自動複製，請改用列印或稍後再試。'; announce(status.textContent); });
        return;
      }
      if (action === 'print') {
        const metrics = planMetrics(state.plan, state.answers, state.edit_count);
        emit('planner_export', { export_type: 'print', day_bucket: metrics.day_bucket, item_count_bucket: metrics.item_count_bucket });
        if (typeof root.print === 'function') root.print();
        return;
      }
      if (action === 'quote') {
        const status = rootEl.querySelector('.ip-action-status');
        if (!savePlannerPrefill(root.sessionStorage, state)) { status.textContent = '無法暫存行程，請先複製摘要再聯絡我們。'; announce(status.textContent); return; }
        const metrics = planMetrics(state.plan, state.answers, state.edit_count);
        emit('planner_quote_click', { day_bucket: metrics.day_bucket, completion_bucket: metrics.completion_bucket, warning_count_bucket: metrics.warning_count_bucket, edit_count_bucket: metrics.edit_count_bucket });
        root.location.href = '/#contact';
        return;
      }
      if (action === 'day') { state.current_day = Number(button.dataset.day); render(rootEl, state); return; }
      if (action === 'filter') { state.category = button.dataset.category; render(rootEl, state); return; }
      if (action === 'ignore-warning') {
        const warning = planner.evaluatePlan(state.plan, state.answers).find(function (row) { return row.id === button.dataset.warningId; });
        if (warning) {
          state.ignored_warning_ids.push(warning.id);
          emit('planner_warning_ignored', { warning_type: warning.type, severity: warning.severity, day_index: warning.day_index });
          render(rootEl, state);
        }
        return;
      }
      if (action === 'add') {
        const next = addToDay(state.plan, itemId, state.current_day);
        const card = data.CARD_INDEX[itemId];
        applyPlanChange(next, 'add', 'planner_item_add', itemEventParams(itemId, findPlacement(next, itemId), 'catalog'), card ? `已將 ${card.name} 加入第 ${state.current_day} 天` : '已加入行程');
        return;
      }
      if (action === 'remove') {
        const row = findPlacement(state.plan, itemId);
        const card = data.CARD_INDEX[itemId];
        applyPlanChange(planner.removeItem(state.plan, itemId), 'remove', 'planner_item_remove', itemEventParams(itemId, row, 'board'), card ? `已從行程移除 ${card.name}` : '已移除行程項目');
        return;
      }
      if (action === 'up' || action === 'down' || action === 'previous-day' || action === 'next-day') {
        const before = findPlacement(state.plan, itemId);
        const next = action === 'up' || action === 'down'
          ? moveWithinSlot(state.plan, itemId, action)
          : moveToDay(state.plan, itemId, action === 'previous-day' ? 'previous' : 'next');
        const after = findPlacement(next, itemId), card = data.CARD_INDEX[itemId];
        applyPlanChange(next, 'move', 'planner_item_move', card && before && after ? {
          item_id: itemId, category: card.category, from_day: before.day_index, to_day: after.day_index,
          from_slot: before.slot, to_slot: after.slot
        } : {}, card && after ? `已將 ${card.name} 移到第 ${after.day_index} 天${SLOT_LABELS[after.slot]}` : '已移動行程項目');
        return;
      }
      if (action === 'restore') {
        if (!confirmReplacement('恢復推薦會取代你目前手動調整的行程，確定嗎？')) return;
        applyPlanChange(restorePlanFor(state.answers), 'restore', null, null, '已恢復推薦行程');
        emit('planner_restore_template', { template_id: state.plan.template_id || 'custom', edit_count_bucket: planMetrics(state.plan, state.answers, state.edit_count).edit_count_bucket });
        emitTemplate();
        return;
      }
      if (action === 'clear') {
        if (!confirmReplacement('清空會移除你目前手動調整的行程，確定嗎？')) return;
        applyPlanChange(emptyPlanFor(state.answers), 'clear', null, null, '已清空行程');
        return;
      }
      if (action === 'delete-local') {
        if (typeof root.confirm === 'function' && !root.confirm('確定要刪除這台裝置上的試排資料嗎？')) return;
        clearStoredState(storage);
        try { root.sessionStorage.removeItem(PREFILL_KEY); } catch (_) {}
        const reset = buildState(rawQuiz);
        state.answers = reset.answers;
        state.plan = reset.plan;
        state.edit_count = 0;
        state.current_day = 1;
        state.undo_snapshot = null;
        state.notice = '已刪除本機資料';
        render(rootEl, state);
        announce('已刪除本機資料');
        return;
      }
    });

    rootEl.addEventListener('submit', function (event) {
      if (event.target.id !== 'ip-settings') return;
      event.preventDefault();
      const form = new root.FormData(event.target);
      const avoid = state.answers.avoid_preference.filter(function (value) { return value !== 'rushed'; });
      const styles = state.answers.travel_style.filter(function (value) { return value !== 'relax'; });
      if (form.get('pace') === 'slow') { avoid.push('rushed'); styles.push('relax'); }
      const nextAnswers = safeAnswers(Object.assign({}, state.answers, {
        travel_days: form.get('travel_days'), party_type: form.get('party_type'),
        avoid_preference: avoid, travel_style: styles
      }));
      if (!confirmReplacement('重新產生會取代你目前手動調整的行程，確定嗎？')) { render(rootEl, state); return; }
      state.undo_snapshot = { answers: state.answers, plan: state.plan, edit_count: state.edit_count };
      state.answers = nextAnswers;
      state.explicit_profile = Object.assign({}, state.explicit_profile, {
        travel_days: nextAnswers.travel_days, party_type: nextAnswers.party_type,
        avoid_preference: nextAnswers.avoid_preference, travel_style: nextAnswers.travel_style
      });
      const nextPlan = restorePlanFor(nextAnswers);
      state.current_day = 1;
      state.notice = '已重新產生';
      if (analytics && typeof analytics.saveProfile === 'function') analytics.saveProfile(state.explicit_profile);
      applyPlanChange(nextPlan, 'settings', null, null, '已依新設定重新產生行程');
      emitTemplate();
    });

    const initialMetrics = planMetrics(state.plan, state.answers, state.edit_count);
    if (!stored) {
      let hasQuizAnswers = false;
      try { hasQuizAnswers = !!root.sessionStorage.getItem(QUIZ_KEY); } catch (_) {}
      const entrySource = entrySourceFrom(root.location && root.location.search, hasQuizAnswers);
      emit('planner_start', { planner_version: 'p0_d_v1', entry_source: entrySource, template_id: state.plan.template_id || 'custom', day_bucket: initialMetrics.day_bucket });
      emitTemplate();
      emitWarnings(initialMetrics.warnings);
      emitComplete(initialMetrics);
      persistAndRender();
    } else {
      initialMetrics.warnings.forEach(function (warning) { seenWarningIds.add(warning.id); });
      render(rootEl, state);
      if (state.removed_item_count) announce('部分景點已下架，已從行程移除');
    }
    return state;
  }

  if (root.document) root.document.addEventListener('DOMContentLoaded', init);
  return {
    STORAGE_KEY, QUIZ_KEY, PREFILL_KEY, QUIZ_DECISION_KEY, MAX_AGE_MS, FUTURE_TOLERANCE_MS, CATEGORY_LABELS, SLOT_LABELS,
    safeAnswers, buildState, validPlan, sanitizeStoredPlan, loadState, saveState, clearStoredState,
    quizAnswers, quizPayload, explicitProfile, answersEqual, shouldOfferNewQuiz, entrySourceFrom, findPlacement, chooseSlot, addToDay, moveWithinSlot, moveToDay,
    emptyPlanFor, restorePlanFor, isUsed, countBucket, planMetrics, warningDiff, markResolution, itemEventParams, trackPlanner,
    dayLabel, buildPlanSummary, buildStructuredPlan,
    buildPlannerPrefillPayload, savePlannerPrefill, copyText, printSheetHtml, focusDescriptor, restoreFocus, init
  };
});
