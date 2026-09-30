(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PhbayItineraryPlannerData = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const VERIFIED_AT = '2026-09-30';
  const SOURCES = Object.freeze({
    city: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/MustIsland/CityTrip.htm',
    north: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/MustIsland/NorthLoop.htm',
    accessible: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/Theme05/Elder01.htm',
    southEast: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/BikeRoutes/SouthPenghuCoast.htm',
    universal: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/Theme09/Tongyong01.htm',
    islands: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/tour/ThematicTours/SouthSea/SevenIslands.htm',
    sailings: 'https://www.penghu-nsa.gov.tw/ChiHoOneLer/transport/Traffic/IslandHoppingTraffic/IHT02.htm',
    firstParty: 'https://www.phbay.info/penghu-itinerary-recommendations'
  });

  const ENUMS = Object.freeze({
    category: ['attraction', 'island', 'water', 'food', 'culture', 'rest', 'transport', 'shopping'],
    area: ['magong', 'north', 'south', 'huxi', 'xiyu', 'baisha', 'offshore'],
    duration_bucket: ['short', 'half_day', 'full_day', 'flexible'],
    slot: ['morning', 'noon', 'afternoon', 'evening'],
    indoor_level: ['indoor', 'mixed', 'outdoor'],
    boat_level: ['none', 'short', 'long'],
    walking_level: ['low', 'medium', 'high'],
    suitability: [true, false, 'conditional']
  });

  const CARDS = [
    {
      id: 'magong_old_town_walk', name: '馬公老城慢走', category: 'culture', area: 'magong',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon', 'evening'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'medium',
      child_friendly: true, elder_friendly: 'conditional', weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.city, verified_at: VERIFIED_AT
    },
    {
      id: 'guanyinting_sunset', name: '觀音亭海邊散步', category: 'attraction', area: 'magong',
      duration_bucket: 'short', preferred_slots: ['afternoon', 'evening'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.city, verified_at: VERIFIED_AT
    },
    {
      id: 'magong_food_break', name: '馬公用餐與休息', category: 'food', area: 'magong',
      duration_bucket: 'flexible', preferred_slots: ['noon', 'evening'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.firstParty, verified_at: VERIFIED_AT
    },
    {
      id: 'hotel_rest_buffer', name: '住宿休息／彈性時間', category: 'rest', area: 'magong',
      duration_bucket: 'flexible', preferred_slots: ['noon', 'afternoon'],
      indoor_level: 'indoor', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.firstParty, verified_at: VERIFIED_AT
    },
    {
      id: 'north_loop_highlights', name: '北環重點路線', category: 'attraction', area: 'north',
      duration_bucket: 'full_day', preferred_slots: ['morning'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'medium',
      child_friendly: true, elder_friendly: 'conditional', weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.north, verified_at: VERIFIED_AT
    },
    {
      id: 'tongliang_banyan', name: '通梁古榕乘涼', category: 'attraction', area: 'baisha',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.accessible, verified_at: VERIFIED_AT
    },
    {
      id: 'erkan_settlement', name: '二崁聚落走讀', category: 'culture', area: 'xiyu',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'medium',
      child_friendly: true, elder_friendly: 'conditional', weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.north, verified_at: VERIFIED_AT
    },
    {
      id: 'lintou_park', name: '林投公園與海岸休息', category: 'attraction', area: 'huxi',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.universal, verified_at: VERIFIED_AT
    },
    {
      id: 'kuibishan_tidal_walk', name: '奎壁山潮間地景', category: 'attraction', area: 'huxi',
      duration_bucket: 'half_day', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'high',
      child_friendly: 'conditional', elder_friendly: false, weather_sensitive: true,
      tide_sensitive: true, fixed_schedule: true, source_url: SOURCES.universal, verified_at: VERIFIED_AT
    },
    {
      id: 'suogang_stone_pagodas', name: '鎖港南北石塔', category: 'culture', area: 'south',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: 'conditional', weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.southEast, verified_at: VERIFIED_AT
    },
    {
      id: 'shanshui_beach', name: '山水海邊停留', category: 'water', area: 'south',
      duration_bucket: 'half_day', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'outdoor', boat_level: 'none', walking_level: 'medium',
      child_friendly: 'conditional', elder_friendly: 'conditional', weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.southEast, verified_at: VERIFIED_AT
    },
    {
      id: 'qimei_wangan_day_trip', name: '七美望安跳島', category: 'island', area: 'offshore',
      duration_bucket: 'full_day', preferred_slots: ['morning'],
      indoor_level: 'outdoor', boat_level: 'long', walking_level: 'medium',
      child_friendly: 'conditional', elder_friendly: false, weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: true, source_url: SOURCES.islands, verified_at: VERIFIED_AT
    },
    {
      id: 'inner_sea_cruise', name: '內海巡禮', category: 'island', area: 'offshore',
      duration_bucket: 'half_day', preferred_slots: ['morning', 'afternoon'],
      indoor_level: 'outdoor', boat_level: 'short', walking_level: 'low',
      child_friendly: 'conditional', elder_friendly: 'conditional', weather_sensitive: true,
      tide_sensitive: false, fixed_schedule: true, source_url: SOURCES.sailings, verified_at: VERIFIED_AT
    },
    {
      id: 'souvenir_buffer', name: '伴手禮與最後採買', category: 'shopping', area: 'magong',
      duration_bucket: 'short', preferred_slots: ['morning', 'afternoon', 'evening'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: false, source_url: SOURCES.city, verified_at: VERIFIED_AT
    },
    {
      id: 'departure_transfer_buffer', name: '前往機場／港口與交通緩衝', category: 'transport', area: 'magong',
      duration_bucket: 'flexible', preferred_slots: ['morning', 'afternoon', 'evening'],
      indoor_level: 'mixed', boat_level: 'none', walking_level: 'low',
      child_friendly: true, elder_friendly: true, weather_sensitive: false,
      tide_sensitive: false, fixed_schedule: true, source_url: SOURCES.firstParty, verified_at: VERIFIED_AT
    }
  ];

  function deepFreeze(value) {
    if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
    Object.freeze(value);
    Object.keys(value).forEach(function (key) { deepFreeze(value[key]); });
    return value;
  }

  deepFreeze(CARDS);
  const CARD_INDEX = deepFreeze(CARDS.reduce(function (out, card) {
    out[card.id] = card;
    return out;
  }, {}));

  return { VERIFIED_AT, SOURCES, ENUMS, CARDS, CARD_INDEX };
});
