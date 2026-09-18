(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PhbayItineraryPrefill = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
  'use strict';
  const KEY = 'phbay_itinerary_prefill_v1';
  const MAX_AGE_MS = 2 * 60 * 60 * 1000;
  const LABELS = {
    days:{'2d1n':'2 天 1 夜','3d2n':'3 天 2 夜','4d3n':'4 天 3 夜','5dplus':'5 天以上'},
    party:{couple:'情侶',friends:'朋友',family:'親子家庭',three_generation:'三代同堂',company:'公司／團體',solo:'一個人'},
    style:{water:'玩水',island:'跳島',photo:'拍照',food:'美食',culture:'文化聚落',relax:'放空慢遊'},
    avoid:{sun:'曬太陽',long_boat:'長船程',rushed:'趕行程',water:'玩水',walking:'走太多路',seasick:'暈船'}
  };
  function list(v){return Array.isArray(v)?v:(v?[v]:[]);}
  function dayCount(v){return ({'2d1n':2,'3d2n':3,'4d3n':4,'5dplus':5})[v]||3;}
  function endDate(start,days){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(start||''))return '';
    const parts=start.split('-').map(Number),d=new Date(parts[0],parts[1]-1,parts[2]);d.setDate(d.getDate()+dayCount(days)-1);
    const p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
  }
  function peopleRange(adults,children){const n=Math.max(1,Number(adults||0)+Number(children||0));return n<=2?'1-2':n<=5?'3-5':n<=10?'6-10':'11+';}
  function transportValue(method){return String(method||'').startsWith('flight')?'飛機':String(method||'').startsWith('ferry')?'搭船':'';}
  function budgetValue(v){return ({under_5k:'under5000','5k_8k':'5000-8000','8k_12k':'8000-12000',quality_first:'12000-18000'})[v]||'';}
  function summary(payload){
    const a=payload.answers||{},r=payload.result||{},p=payload.product||{},styles=list(a.travel_style).map(x=>LABELS.style[x]||x),avoid=list(a.avoid_preference).map(x=>LABELS.avoid[x]||x);
    return `【30 秒行程診斷】${r.type||'行程推薦'}｜${LABELS.days[a.travel_days]||a.travel_days||'天數未定'}｜${LABELS.party[a.party_type]||a.party_type||'同行類型未定'}｜成人 ${Number(a.adults||0)}、兒童 ${Number(a.children||0)}｜偏好：${styles.join('、')||'未選'}｜避開：${avoid.join('、')||'未選'}｜推薦：${p.name||'待確認'}`;
  }
  function formValues(payload){
    const a=payload.answers||{};
    return {travel_date:a.travel_date==='undecided'?'':(a.travel_date||''),travel_date_end:a.travel_date==='undecided'?'':endDate(a.travel_date,a.travel_days),people:peopleRange(a.adults,a.children),transport:transportValue(a.arrival_method),budget:budgetValue(a.budget_range),tour_id:String((payload.product||{}).tour_id||''),notes:summary(payload)};
  }
  function loadPayload(){
    try{const value=JSON.parse(root.sessionStorage.getItem(KEY)||'null');if(!value||value.version!==1)return null;if(!value.created_at||Date.now()-value.created_at>MAX_AGE_MS){root.sessionStorage.removeItem(KEY);return null;}return value;}catch(_){return null;}
  }
  function setIfEmpty(el,value){if(el&&value&&!el.value){el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}));return true;}return false;}
  function apply(payload,doc){
    doc=doc||root.document;if(!payload||!doc||!doc.getElementById('contact-form'))return {applied:false,tourApplied:false};
    const v=formValues(payload),start=doc.getElementById('travel-date-start'),end=doc.getElementById('travel-date-end');
    setIfEmpty(start,v.travel_date);setIfEmpty(end,v.travel_date_end);setIfEmpty(doc.getElementById('people'),v.people);setIfEmpty(doc.getElementById('budget'),v.budget);
    if(v.transport&&!doc.querySelector('input[name="transport"]:checked')){const radio=doc.querySelector(`input[name="transport"][value="${v.transport}"]`);if(radio){radio.checked=true;radio.dispatchEvent(new Event('change',{bubbles:true}));}}
    const select=doc.getElementById('tour-interest'),option=select&&v.tour_id?select.querySelector(`option[data-tour-id="${v.tour_id}"]`):null;
    if(option&&select.value!==option.value){select.value=option.value;select.dispatchEvent(new Event('change',{bubbles:true}));}
    const notes=doc.getElementById('notes');if(notes&&!notes.value.includes('【30 秒行程診斷】'))notes.value=notes.value?`${notes.value}\n${v.notes}`:v.notes;
    const details=doc.querySelector('.form-more');if(details)details.open=true;
    return {applied:true,tourApplied:!!option,values:v};
  }
  function applyStored(){return apply(loadPayload(),root.document);}
  if(root.document){root.document.addEventListener('DOMContentLoaded',applyStored);root.addEventListener('phbay:tours-ready',applyStored);}
  return {KEY,MAX_AGE_MS,dayCount,endDate,peopleRange,transportValue,budgetValue,summary,formValues,loadPayload,apply,applyStored};
});
