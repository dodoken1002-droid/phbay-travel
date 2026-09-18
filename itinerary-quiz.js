(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PhbayItineraryQuiz = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
  'use strict';

  const STORAGE_KEY = 'phbay_itinerary_answers_v1';
  const PREFILL_KEY = 'phbay_itinerary_prefill_v1';
  const QUIZ_VERSION = 'p1_v1';
  const QUESTIONS = [
    { key:'travel_date', title:'預計什麼時候來澎湖？', type:'date', options:[['undecided','還沒決定日期']] },
    { key:'travel_days', title:'想玩幾天？', options:[['2d1n','2 天 1 夜'],['3d2n','3 天 2 夜'],['4d3n','4 天 3 夜'],['5dplus','5 天以上']] },
    { key:'party_size', title:'這次有幾位大人與小孩？', type:'party' },
    { key:'children_age', title:'同行小朋友的年齡？', type:'multi', options:[['none','沒有小朋友'],['age_0_3','0–3 歲'],['age_4_6','4–6 歲'],['age_7_12','7–12 歲'],['age_13_17','13–17 歲']] },
    { key:'party_type', title:'這次和誰一起來？', options:[['couple','情侶'],['friends','朋友'],['family','親子家庭'],['three_generation','三代同堂'],['company','公司／團體'],['solo','一個人']] },
    { key:'first_visit', title:'是第一次來澎湖嗎？', options:[['yes','第一次'],['no','來過了']] },
    { key:'travel_style', title:'最想怎麼玩？（可複選）', type:'multi', options:[['water','玩水'],['island','跳島'],['photo','拍照'],['food','美食'],['culture','文化聚落'],['relax','放空慢遊']] },
    { key:'avoid_preference', title:'這趟最不想遇到什麼？（可複選）', type:'multi', options:[['sun','曬太陽'],['long_boat','坐太久船'],['rushed','趕行程'],['water','玩水'],['walking','走太多路'],['seasick','暈船']] },
    { key:'arrival_method', title:'往返交通目前的狀態？', options:[['flight_booked','機票已訂'],['ferry_booked','船票已訂'],['flight_planning','想搭飛機、尚未訂'],['ferry_planning','想搭船、尚未訂'],['undecided','還沒決定']] },
    { key:'budget_range', title:'每人預算大約是？', options:[['under_5k','NT$5,000 內'],['5k_8k','NT$5,000–8,000'],['8k_12k','NT$8,000–12,000'],['quality_first','品質優先'],['undecided','還沒決定']] }
  ];
  const PROFILES = {
    family_slow:{type:'親子安心慢遊型',summary:'把孩子的體力、午休與船程放在景點數量之前，玩得少一點，回憶反而更多。'},
    classic_first:{type:'經典初訪收藏型',summary:'先把北環、本島與一次海上體驗排順，第一次來也能看到澎湖最有代表性的風景。'},
    island_adventure:{type:'跳島海洋冒險型',summary:'你重視海上活動與離島風景，適合把完整一天交給一個海域，不在船班之間趕場。'},
    romantic_photo:{type:'海景拍照約會型',summary:'用海景、聚落與夕陽串起旅程，保留足夠停留時間，比打卡數量更重要。'},
    culture_slow:{type:'聚落美食慢旅型',summary:'你適合把澎湖當成一座有故事的島，慢慢走聚落、吃海味，也為天氣保留彈性。'}
  };

  // 商品名稱、價格與 active 狀態由 /api/tours 取得，這裡只維護推薦決策。
  const RECOMMENDED_PRODUCTS = {
    family_slow:{item_id:'tour_3',tourId:3,name:null,url:'/tours/3',type:'tour',boat:true,fallback:[21]},
    classic_first:{item_id:'tour_21',tourId:21,name:null,url:'/tours/21',type:'preorder',boat:true,fallback:[2]},
    island_adventure:{item_id:'tour_12',tourId:12,name:null,url:'/tours/12',type:'tour',boat:true,fallback:[5,21]},
    romantic_photo:{item_id:'tour_17',tourId:17,name:null,url:'/tours/17',type:'tour',boat:true,fallback:[6,21]},
    culture_slow:{item_id:'tour_67',tourId:67,name:null,url:'/tours/67',type:'tour',boat:true,fallback:[21]}
  };
  const PRODUCT_SETTINGS = {
    2:{type:'tour',boat:true},3:{type:'tour',boat:true},5:{type:'tour',boat:true},6:{type:'tour',boat:true},
    12:{type:'tour',boat:true},17:{type:'tour',boat:true},21:{type:'preorder',boat:true,bookingUrl:'/neihai-preorder.html'},
    67:{type:'tour',boat:true}
  };
  const PRICE_MODEL = {
    version:'p1_v1',confirmed:false,source:'潮旅官網商品售價（/api/tours）＋P1 規劃假設',sourceUrl:'/api/tours',
    assumptions:{
      accommodationPerNight:[1200,2400],mealsPerDay:[600,1000],localTransitPerDay:[300,600],
      transport:{flight_planning:[4000,7000],ferry_planning:[1800,3200],undecided:[1800,7000],flight_booked:[0,0],ferry_booked:[0,0]}
    }
  };
  const LABELS = {
    budget:{under_5k:'NT$5,000 內','5k_8k':'NT$5,000–8,000','8k_12k':'NT$8,000–12,000',quality_first:'品質優先',undecided:'尚未決定'},
    days:{'2d1n':'2 天 1 夜','3d2n':'3 天 2 夜','4d3n':'4 天 3 夜','5dplus':'5 天以上'},
    party:{couple:'情侶',friends:'朋友',family:'親子家庭',three_generation:'三代同堂',company:'公司／團體',solo:'一個人'}
  };

  function list(v){return Array.isArray(v)?v:(v?[v]:[]);}
  function has(v,x){return list(v).indexOf(x)!==-1;}
  function unique(xs){return xs.filter((x,i)=>xs.indexOf(x)===i);}
  function tripDayCount(v){return ({'2d1n':2,'3d2n':3,'4d3n':4,'5dplus':5})[v]||3;}
  function avoidsBoat(v){return ['long_boat','seasick','water'].some(x=>has(v,x));}

  function recommend(a){
    const score={family_slow:0,classic_first:0,island_adventure:0,romantic_photo:0,culture_slow:0};
    const style=list(a.travel_style),avoid=list(a.avoid_preference),ages=list(a.children_age);
    if(a.party_type==='family'||ages.some(x=>x!=='none'))score.family_slow+=8;
    if(a.party_type==='three_generation')score.family_slow+=9;
    if(a.first_visit==='yes')score.classic_first+=6;
    if(a.party_type==='couple')score.romantic_photo+=5;
    if(a.party_type==='friends'||a.party_type==='company')score.island_adventure+=3;
    if(style.includes('water'))score.island_adventure+=5;
    if(style.includes('island'))score.island_adventure+=6;
    if(style.includes('photo'))score.romantic_photo+=6;
    if(style.some(x=>['food','culture','relax'].includes(x)))score.culture_slow+=4;
    if(avoid.some(x=>['long_boat','seasick','rushed'].includes(x)))score.family_slow+=4;
    if(avoid.includes('water'))score.culture_slow+=5;
    const key=Object.keys(score).sort((x,y)=>score[y]-score[x])[0],reasons=[];
    if(a.first_visit==='yes')reasons.push('保留澎湖經典動線，第一次來也不會漏掉重點');
    if(ages.some(x=>x!=='none'))reasons.push('依兒童年齡縮短單次移動，午後保留休息');
    if(avoid.includes('long_boat')||avoid.includes('seasick'))reasons.push('避開長時間船程，優先安排陸上或短程備案');
    if(avoid.includes('water'))reasons.push('不把玩水活動列為主要推薦');
    if(avoid.includes('rushed'))reasons.push('每天主要活動控制在 2 個以內');
    if(style.length)reasons.push('以你選的玩法偏好作為每天主題');
    const warnings=[];
    if(/planning|undecided/.test(a.arrival_method||''))warnings.push('交通尚未確認，機票／船票敲定後需依實際抵離時間微調。');
    if(avoid.includes('sun'))warnings.push('11:30–15:00 優先安排室內、用餐或休息，戶外活動仍需防曬補水。');
    if(avoid.includes('seasick'))warnings.push('船班受海況影響，請先諮詢醫師或藥師準備暈船對策，並保留陸上備案。');
    if(avoid.includes('walking'))warnings.push('聚落與景點仍有短距離步行，可改接送或減少停靠點。');
    if(a.travel_days==='2d1n')warnings.push('2 天 1 夜抵離時間吃掉不少可玩時數，建議只選一條主線。');
    if(!warnings.length)warnings.push('海上活動與潮間帶會受天候、潮汐影響，出發前仍需再次確認。');
    return {key,profile:PROFILES[key],itinerary:makeItinerary(key,a.travel_days||'3d2n',avoid),reasons:unique(reasons).slice(0,5),warnings,analytics:analyticsFor(a)};
  }

  function makeItinerary(key,days,avoid){
    const noBoat=avoidsBoat(avoid),middle=noBoat?'本島聚落與潮間帶陸上備案':(key==='island_adventure'?'選一個海域跳島或海上體驗':'內海巡禮＋潮汐體驗');
    const base=[
      {day:'Day 1',title:'抵達・馬公慢慢進入狀態',detail:'依抵達時間走中央老街、天后宮與觀音亭，晚上安排在地海味。'},
      {day:'Day 2',title:middle,detail:key==='family_slow'?'上午體驗、午後休息；主要活動不超過兩個。':'把完整一天留給同一區域，避免折返趕場。'},
      {day:'Day 3',title:'北環精華・伴手禮',detail:'通梁古榕、跨海大橋、小門或二崁擇重點停留。'},
      {day:'Day 4',title:'南環／聚落深度日',detail:'風櫃、山水或湖西聚落擇一，為天候與體力保留彈性。'},
      {day:'Day 5',title:'留白與雨天備案',detail:'自由補上最喜歡的海邊、美食或室內文化景點。'}
    ];
    const count=tripDayCount(days);
    if(count===2)return [base[0],{day:'Day 2',title:'北環或單一體驗二選一',detail:'只選一條主線，預留回程交通緩衝。'}];
    const plan=base.slice(0,count),last=plan[plan.length-1];
    plan[plan.length-1]=Object.assign({},last,{detail:last.detail+'最後依班次前往機場或港口。'});
    return plan;
  }

  function flattenTours(payload){
    const groups=payload&&payload.tours?payload.tours:payload,seen=new Set(),rows=[];
    Object.values(groups||{}).forEach(group=>(Array.isArray(group)?group:[]).forEach(t=>{if(!seen.has(String(t.id))){seen.add(String(t.id));rows.push(t);}}));
    return rows;
  }
  function resolveRecommendedProduct(profileKey,avoid,tours){
    const rule=RECOMMENDED_PRODUCTS[profileKey]||RECOMMENDED_PRODUCTS.classic_first,noBoat=avoidsBoat(avoid),byId={};
    (tours||[]).forEach(t=>{byId[String(t.id)]=t;});
    let selected=null;
    for(const id of [rule.tourId].concat(rule.fallback||[])){
      const live=byId[String(id)],setting=PRODUCT_SETTINGS[id]||{type:'tour',boat:false};
      if(live&&live.is_active!==false&&(!noBoat||!setting.boat)){selected={id,live,setting};break;}
    }
    if(noBoat&&!selected)return {item_id:'land_itinerary_consultation',tourId:null,name:'陸上行程客製建議',price:'由顧問依需求報價',url:'/#contact',type:'consultation',boat:false,active:true,cta:'請潮旅規劃陸上行程',unverified:false};
    if(!selected){const id=21;selected={id,live:byId[String(id)]||null,setting:PRODUCT_SETTINGS[id],unverified:true};}
    const live=selected.live||{},bookingUrl=!selected.unverified&&selected.setting.bookingUrl?selected.setting.bookingUrl:null;
    return {item_id:`tour_${selected.id}`,tourId:selected.id,name:live.title||'潮旅推薦行程',price:live.price_display||'價格請見商品頁',url:bookingUrl||`/tours/${selected.id}`,type:bookingUrl?'preorder':'tour',boat:!!selected.setting.boat,active:!!selected.live&&selected.live.is_active!==false,cta:bookingUrl?'直接預訂':'查看行程與洽詢',unverified:!!selected.unverified};
  }
  function parsePriceRange(display){
    const price=String(display||'').match(/NT\$\s*([\d,]+)/i);if(!price)return [0,0];
    const value=Number(price[1].replace(/,/g,''));return Number.isFinite(value)?[value,value]:[0,0];
  }
  function estimatePrice(a,product){
    const days=tripDayCount(a.travel_days),nights=Math.max(1,days-1),A=PRICE_MODEL.assumptions,transport=A.transport[a.arrival_method]||A.transport.undecided,productPrice=parsePriceRange(product&&product.price);
    const rows=[
      {key:'transport',label:'往返交通',range:transport,source:'規劃假設'},
      {key:'accommodation',label:'住宿',range:A.accommodationPerNight.map(v=>v*nights),source:'規劃假設'},
      {key:'meals',label:'餐食',range:A.mealsPerDay.map(v=>v*days),source:'規劃假設'},
      {key:'localTransit',label:'島上交通',range:A.localTransitPerDay.map(v=>v*days),source:'規劃假設'},
      {key:'product',label:'推薦商品',range:productPrice,source:productPrice[0]?'官網即時售價':'尚待報價'}
    ];
    const perPerson=rows.reduce((sum,row)=>[sum[0]+row.range[0],sum[1]+row.range[1]],[0,0]),partySize=Math.max(1,Number(a.adults||0)+Number(a.children||0));
    return {confirmed:PRICE_MODEL.confirmed,rows,perPerson,partySize,party:[perPerson[0]*partySize,perPerson[1]*partySize],budget:budgetComparison(a.budget_range,perPerson)};
  }
  function budgetComparison(budget,range){
    const limits={under_5k:[0,5000],'5k_8k':[5000,8000],'8k_12k':[8000,12000]};
    if(!limits[budget])return budget==='quality_first'?'你選擇品質優先，可依住宿與體驗再微調。':'尚未設定預算，可先用明細抓範圍。';
    const b=limits[budget];if(range[0]>b[1])return '目前試算高於你選的預算，建議由顧問協助刪減或改選。';if(range[1]<b[0])return '目前試算低於你選的預算，仍有升級住宿或體驗的空間。';return '目前試算與你選的預算有交集，可再依班次與住宿確認。';
  }
  function analyticsFor(a){
    const children=list(a.children_age).filter(x=>x!=='none');
    return {travel_days:a.travel_days,party_type:a.party_type,children_age:children.length?children:['none'],budget_range:a.budget_range,travel_style:list(a.travel_style),avoid_preference:list(a.avoid_preference),arrival_method:a.arrival_method,first_visit:a.first_visit};
  }
  function localToday(){const d=new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10);}
  function money(n){return `NT$${Math.round(n).toLocaleString('zh-TW')}`;}
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function track(name,params){return root.PhbayAnalytics&&root.PhbayAnalytics.track(name,params);}
  function saveState(state){try{root.sessionStorage.setItem(STORAGE_KEY,JSON.stringify(state));}catch(_){}}
  function loadState(){try{return JSON.parse(root.sessionStorage.getItem(STORAGE_KEY)||'{}');}catch(_){return {};}}
  function buildPrefillPayload(answers,result,product){return {version:1,created_at:Date.now(),answers,result:{key:result.key,type:result.profile.type},product:{tour_id:product.tourId,item_id:product.item_id,name:product.name}};}
  function savePrefill(answers,result,product){try{root.sessionStorage.setItem(PREFILL_KEY,JSON.stringify(buildPrefillPayload(answers,result,product)));}catch(_){}}

  function renderQuestion(container,idx,answers){
    const q=QUESTIONS[idx],options=(q.options||[]).map(o=>`<label class="iq-option"><input type="${q.type==='multi'?'checkbox':'radio'}" name="${q.key}" value="${o[0]}"><span>${o[1]}</span></label>`).join('');
    let field=`<div class="iq-options">${options}</div>`;
    if(q.type==='date')field=`<div class="iq-date"><input type="date" name="travel_date" min="${localToday()}"><label class="iq-option"><input type="checkbox" name="travel_date_undecided" value="1"><span>還沒決定日期</span></label></div>`;
    if(q.type==='party')field='<div class="iq-counts"><label>成人<input type="number" name="adults" min="1" max="50" value="2" inputmode="numeric"></label><label>兒童<input type="number" name="children" min="0" max="30" value="0" inputmode="numeric"></label></div>';
    container.innerHTML=`<div class="iq-progress"><span>第 ${idx+1} / ${QUESTIONS.length} 題</span><div><i style="width:${Math.round((idx/QUESTIONS.length)*100)}%"></i></div></div><section class="iq-card"><p class="iq-eyebrow">30 秒澎湖行程診斷</p><h2 tabindex="-1">${q.title}</h2>${field}<p class="iq-error" role="alert"></p><div class="iq-nav">${idx?'<button type="button" class="iq-back">上一步</button>':'<span></span>'}<button type="button" class="iq-next">${idx===QUESTIONS.length-1?'看我的推薦':'下一題'}</button></div></section>`;
    if(answers[q.key]!=null){const vals=list(answers[q.key]);container.querySelectorAll(`[name="${q.key}"]`).forEach(el=>{el.checked=vals.includes(el.value);});}
    if(q.type==='party'){container.querySelector('[name=adults]').value=answers.adults||2;container.querySelector('[name=children]').value=answers.children||0;}
    if(q.type==='date'&&answers.travel_date&&answers.travel_date!=='undecided')container.querySelector('[name=travel_date]').value=answers.travel_date;
    if(q.type==='date'&&answers.travel_date==='undecided')container.querySelector('[name=travel_date_undecided]').checked=true;
  }
  function readAnswer(container,q){
    if(q.type==='party')return {adults:Number(container.querySelector('[name=adults]').value),children:Number(container.querySelector('[name=children]').value)};
    if(q.type==='date')return {travel_date:container.querySelector('[name=travel_date_undecided]').checked?'undecided':container.querySelector('[name=travel_date]').value};
    const selected=Array.from(container.querySelectorAll(`[name="${q.key}"]:checked`)).map(el=>el.value);return {[q.key]:q.type==='multi'?selected:selected[0]};
  }
  function initQuiz(){
    const container=root.document&&root.document.getElementById('itinerary-quiz-v1');if(!container)return;
    let idx=0,answers={},started=false;
    function draw(moveFocus){
      renderQuestion(container,idx,answers);if(moveFocus)container.querySelector('h2').focus({preventScroll:true});
      container.querySelector('.iq-next').addEventListener('click',function(){
        const q=QUESTIONS[idx],value=readAnswer(container,q),invalid=q.type==='party'?(!value.adults||value.children<0):(!value[q.key]||(Array.isArray(value[q.key])&&!value[q.key].length));
        if(invalid){container.querySelector('.iq-error').textContent='請先完成這一題。';return;}Object.assign(answers,value);
        if(q.key==='party_size'&&Number(answers.children)===0)answers.children_age=['none'];
        if(q.key==='children_age'&&Number(answers.children)>0&&has(answers.children_age,'none')){container.querySelector('.iq-error').textContent='有兒童同行時，請選擇實際年齡區間。';return;}
        if(q.key==='children_age'&&Number(answers.children)===0)answers.children_age=['none'];
        if(idx===0&&!started){started=true;track('quiz_start',{quiz_version:QUIZ_VERSION});}
        if(idx<QUESTIONS.length-1){idx++;draw(true);container.scrollIntoView({behavior:'smooth',block:'start'});return;}
        const result=recommend(answers);saveState(answers);if(root.PhbayAnalytics)root.PhbayAnalytics.saveProfile(result.analytics);
        track('quiz_complete',Object.assign({quiz_version:QUIZ_VERSION,itinerary_type:result.key},result.analytics));root.location.href='/penghu-itinerary-recommendations/result';
      });
      const back=container.querySelector('.iq-back');if(back)back.addEventListener('click',function(){idx--;draw(true);});
    }draw();
  }
  async function fetchTours(){try{const res=await root.fetch('/api/tours',{credentials:'same-origin'});if(!res.ok)throw new Error(`HTTP ${res.status}`);return flattenTours(await res.json());}catch(_){return [];}}
  function pricePreviewHtml(e){
    const rows=e.rows.map(row=>`<li><span>${esc(row.label)} <small>${esc(row.source)}</small></span><b>${money(row.range[0])}–${money(row.range[1])}</b></li>`).join('');
    return `<section class="ir-card ir-price-preview"><p class="ir-preview-badge">內部估算預覽・尚未確認</p><h2>價格模型試算</h2><ul>${rows}</ul><div class="ir-price-total"><span>每人參考</span><strong>${money(e.perPerson[0])}–${money(e.perPerson[1])}</strong></div><div class="ir-price-total"><span>${e.partySize} 人合計參考</span><strong>${money(e.party[0])}–${money(e.party[1])}</strong></div><p>${esc(e.budget)}</p><small>此試算含規劃假設，不是正式報價；以實際班次、房況與潮旅確認為準。</small></section>`;
  }
  async function initResult(){
    const container=root.document&&root.document.getElementById('itinerary-result-v1');if(!container)return;
    const answers=loadState();if(!answers.travel_days){container.innerHTML='<div class="iq-empty"><h1>先完成 30 秒行程診斷</h1><p>完成 10 題後，這裡會立即出現推薦行程。</p><a class="iq-primary" href="/penghu-itinerary-recommendations#itinerary-quiz-v1">開始診斷</a></div>';return;}
    const r=recommend(answers),product=resolveRecommendedProduct(r.key,answers.avoid_preference,await fetchTours());
    const preview=new URLSearchParams(root.location.search).get('price_preview')==='1',estimate=estimatePrice(answers,product),budgetLabel=LABELS.budget[answers.budget_range]||LABELS.budget.undecided,adjustHref=product.tourId?`/?tour_id=${encodeURIComponent(product.tourId)}#contact`:'/#contact';
    if(!preview&&root.PhbayAnalytics)root.PhbayAnalytics.saveProfile(r.analytics);
    const resultTrack=(name,params)=>preview?null:track(name,params);
    const actions=`<a class="iq-primary" data-ir-action="book" href="${esc(product.url)}">${esc(product.cta)}</a><a class="iq-secondary" data-ir-action="adjust" href="${adjustHref}">請潮旅幫我微調</a><a class="iq-line" data-ir-action="line" href="https://line.me/R/ti/p/@phbay2018" target="_blank" rel="noopener noreferrer">LINE 諮詢</a>`;
    container.innerHTML=`<header class="ir-hero"><p>你的澎湖旅行類型</p><h1>${esc(r.profile.type)}</h1><div>${esc(r.profile.summary)}</div><strong>你的預算：${esc(budgetLabel)}</strong><small>先呈現你選擇的預算；商品售價以官網即時資訊為準。</small></header><nav class="ir-mobile-actions" aria-label="推薦結果快捷操作">${actions}</nav><div class="ir-grid"><main><section class="ir-card"><h2>推薦行程</h2>${r.itinerary.map(x=>`<article class="ir-day"><b>${esc(x.day)}</b><div><h3>${esc(x.title)}</h3><p>${esc(x.detail)}</p></div></article>`).join('')}</section><section class="ir-card"><h2>為什麼適合你</h2><ul>${r.reasons.map(x=>`<li>✓ ${esc(x)}</li>`).join('')}</ul></section><section class="ir-card ir-warn"><h2>出發前注意</h2><ul>${r.warnings.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section>${preview?pricePreviewHtml(estimate):''}</main><aside class="ir-card ir-product"><p>依診斷推薦的官網商品</p><h2>${esc(product.name)}</h2><strong>${esc(product.price)}</strong>${product.unverified?'<small>目前無法確認即時上架狀態，請進商品頁確認。</small>':''}${actions}<button class="iq-link" data-ir-action="redo" type="button">重新診斷</button></aside></div>`;
    resultTrack('itinerary_view',{itinerary_type:r.key,quiz_version:QUIZ_VERSION});resultTrack('product_view',{item_id:product.item_id,item_name:product.name,itinerary_type:r.key});
    container.querySelectorAll('[data-ir-action="book"]').forEach(el=>el.addEventListener('click',()=>resultTrack('book_now_click',{item_id:product.item_id,source:'itinerary_result',itinerary_type:r.key})));
    container.querySelectorAll('[data-ir-action="adjust"]').forEach(el=>el.addEventListener('click',()=>{savePrefill(answers,r,product);resultTrack('itinerary_adjust_click',{item_id:product.item_id,itinerary_type:r.key});}));
    container.querySelectorAll('[data-ir-action="line"]').forEach(el=>el.addEventListener('click',()=>resultTrack('line_click',{source:'itinerary_result',item_id:product.item_id,itinerary_type:r.key})));
    container.querySelector('[data-ir-action="redo"]').addEventListener('click',()=>{try{root.sessionStorage.removeItem(STORAGE_KEY);root.sessionStorage.removeItem(PREFILL_KEY);}catch(_){}root.location.href='/penghu-itinerary-recommendations#itinerary-quiz-v1';});
  }
  if(root.document)root.document.addEventListener('DOMContentLoaded',function(){initQuiz();initResult();});
  return {QUESTIONS,PROFILES,RECOMMENDED_PRODUCTS,PRODUCT_SETTINGS,PRICE_MODEL,LABELS,recommend,makeItinerary,analyticsFor,flattenTours,resolveRecommendedProduct,estimatePrice,budgetComparison,buildPrefillPayload,initQuiz,initResult};
});
