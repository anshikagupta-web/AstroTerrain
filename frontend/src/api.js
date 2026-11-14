const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const FALLBACK_TARGETS_DATA = [
  {
    planet: "moon",
    site_id: "shackleton-crater",
    site_name: "Shackleton Crater",
    coordinates: { lat: -89.9, lng: 0.0 },
    avg_slope_deg: 12.5,
    elevation_m: -4000,
    primary_rock: "Basalt & Anorthosite",
    temp_range_c: [-80, 20],
    data_source: "LRO LOLA / synthetic_demo",
    description: "Permanently shadowed ultra-cold crater near the Lunar South Pole with confirmed water ice volatiles.",
  },
  {
    planet: "moon",
    site_id: "oceanus-procellarum",
    site_name: "Oceanus Procellarum",
    coordinates: { lat: 18.4, lng: -57.4 },
    avg_slope_deg: 2.1,
    elevation_m: -1800,
    primary_rock: "KREEP Basalt",
    temp_range_c: [-130, 120],
    data_source: "Chang'e-5 / LRO",
    description: "Vast lunar mare featuring radioactive heat-producing elements and young flood basalts.",
  },
  {
    planet: "moon",
    site_id: "spa-basin",
    site_name: "South Pole-Aitken Basin",
    coordinates: { lat: -53.0, lng: 169.0 },
    avg_slope_deg: 14.5,
    elevation_m: -8200,
    primary_rock: "Noritic Impact Melt",
    temp_range_c: [-230, -150],
    data_source: "LRO LAMP",
    description: "One of the largest known impact structures in the Solar System, exposing deep lower crust.",
  },
  {
    planet: "moon",
    site_id: "tycho-crater",
    site_name: "Tycho Crater",
    coordinates: { lat: -43.31, lng: -11.36 },
    avg_slope_deg: 26.0,
    elevation_m: -4800,
    primary_rock: "Impact Melt Breccia",
    temp_range_c: [-180, 100],
    data_source: "Clementine UVVIS",
    description: "Prominent young impact crater with distinctive ray system spanning thousands of kilometers.",
  },
  {
    planet: "mars",
    site_id: "jezero-crater",
    site_name: "Jezero Crater",
    coordinates: { lat: 18.38, lng: 77.58 },
    avg_slope_deg: 6.0,
    elevation_m: -2500,
    primary_rock: "Basaltic sediment & Clays",
    temp_range_c: [-70, 10],
    data_source: "Mars 2020 / synthetic_demo",
    description: "Ancient Martian lakebed delta rich in phyllosilicates, smectite clays, and carbonate biosignatures.",
  },
  {
    planet: "mars",
    site_id: "gale-crater",
    site_name: "Gale Crater",
    coordinates: { lat: -5.4, lng: 137.8 },
    avg_slope_deg: 11.4,
    elevation_m: -4500,
    primary_rock: "Fluvial Sandstone",
    temp_range_c: [-100, 0],
    data_source: "MSL Curiosity",
    description: "Layered central mound (Aeolis Mons) preserving sedimentary sequences of Mars' wet-to-dry transition.",
  },
  {
    planet: "mars",
    site_id: "olympus-mons",
    site_name: "Olympus Mons",
    coordinates: { lat: 18.65, lng: -133.8 },
    avg_slope_deg: 5.0,
    elevation_m: 21287,
    primary_rock: "Tholeiitic Basalt Shield",
    temp_range_c: [-110, -20],
    data_source: "MGS MOLA",
    description: "The colossal shield volcano on Mars, rising 21 km above the datum with complex caldera collapses.",
  },
  {
    planet: "mars",
    site_id: "valles-marineris",
    site_name: "Valles Marineris",
    coordinates: { lat: -13.9, lng: -59.2 },
    avg_slope_deg: 28.5,
    elevation_m: -7000,
    primary_rock: "Stratified Basaltic Lava",
    temp_range_c: [-85, 15],
    data_source: "THEMIS / Viking",
    description: "Grand tectonic canyon system extending 4,000 km across the Martian equator with stratified walls.",
  },
];

// Rich fallback analog dataset with scientific rationale
const SITE_ANALOG_MAP = {
  "shackleton-crater": [
    {
      site_id: "mcmurdo-dry-valleys",
      name: "McMurdo Dry Valleys",
      country: "Antarctica",
      coordinates: { lat: -77.5, lng: 161.0 },
      similarity_score: 96.4,
      breakdown: { topography_match: 94, geochemistry_match: 96, climate_match: 99 },
      metadata: { elevation_m: 300, primary_rock: "Permafrost & Basalt Breccia", accessibility_rating: "Challenging" },
      rationale: "Coldest hyper-arid polar desert on Earth; perennial subsurface permafrost mirrors lunar PSR cryogenic cold traps.",
    },
    {
      site_id: "svalbard-analog-c",
      name: "Svalbard Volcanic Field",
      country: "Norway",
      coordinates: { lat: 78.0, lng: 16.0 },
      similarity_score: 91.2,
      breakdown: { topography_match: 90, geochemistry_match: 92, climate_match: 92 },
      metadata: { elevation_m: 120, primary_rock: "Volcanic Rock & Basalt", accessibility_rating: "Moderate" },
      rationale: "Sub-polar glacial-basalt interface used by ESA for lunar rover mobility and drill testing.",
    },
    {
      site_id: "haughton-impact-crater",
      name: "Haughton Impact Crater",
      country: "Canada (Devon Island)",
      coordinates: { lat: 75.38, lng: -89.67 },
      similarity_score: 88.5,
      breakdown: { topography_match: 92, geochemistry_match: 87, climate_match: 86 },
      metadata: { elevation_m: 180, primary_rock: "Shocked Dolomite & Impact Breccia", accessibility_rating: "Challenging" },
      rationale: "Devon Island Arctic impact structure with shattered shatter cones and continuous permafrost.",
    },
  ],
  "jezero-crater": [
    {
      site_id: "atacama-desert-yungay",
      name: "Atacama Desert (Yungay)",
      country: "Chile",
      coordinates: { lat: -23.5, lng: -68.2 },
      similarity_score: 94.8,
      breakdown: { topography_match: 92, geochemistry_match: 98, climate_match: 94 },
      metadata: { elevation_m: 2300, primary_rock: "Halite & Nitrate Evaporites", accessibility_rating: "High" },
      rationale: "Hyper-arid ancient clay basin with extreme UV exposure and desiccated salt-crust sedimentology.",
    },
    {
      site_id: "rio-tinto-basin",
      name: "Río Tinto Gossan Field",
      country: "Spain",
      coordinates: { lat: 37.7, lng: -6.6 },
      similarity_score: 91.5,
      breakdown: { topography_match: 84, geochemistry_match: 99, climate_match: 91 },
      metadata: { elevation_m: 350, primary_rock: "Jarosite & Iron Sulfates", accessibility_rating: "High" },
      rationale: "Acidic iron-sulfate weathering mimicking the exact jarosite mineralogy detected by Mars rovers.",
    },
    {
      site_id: "lake-salda-delta",
      name: "Lake Salda Hydromagnesite Basin",
      country: "Turkey",
      coordinates: { lat: 37.55, lng: 29.71 },
      similarity_score: 89.2,
      breakdown: { topography_match: 93, geochemistry_match: 95, climate_match: 79 },
      metadata: { elevation_m: 1190, primary_rock: "Hydromagnesite & Stromatolites", accessibility_rating: "Very High" },
      rationale: "The only known lake on Earth with mineralogy and deltaic deposition closely matching Jezero's ancient shoreline.",
    },
  ],
  "olympus-mons": [
    {
      site_id: "mauna-kea-volcanic",
      name: "Mauna Kea Volcanic Ridge",
      country: "USA (Hawaii)",
      coordinates: { lat: 19.5, lng: -155.5 },
      similarity_score: 95.7,
      breakdown: { topography_match: 98, geochemistry_match: 96, climate_match: 93 },
      metadata: { elevation_m: 4207, primary_rock: "Alkaline Basalt & Tephra", accessibility_rating: "Very High" },
      rationale: "Earth's largest shield volcano measured from base; prime structural and geochemical analog for Martian shields.",
    },
    {
      site_id: "askja-iceland-analog",
      name: "Askja Volcanic Caldera",
      country: "Iceland",
      coordinates: { lat: 65.03, lng: -16.75 },
      similarity_score: 88.4,
      breakdown: { topography_match: 92, geochemistry_match: 89, climate_match: 84 },
      metadata: { elevation_m: 1100, primary_rock: "Basaltic Tephra & Pumice", accessibility_rating: "Moderate" },
      rationale: "Apollo-tested caldera collapse and basaltic lava fields with sub-arctic wind scouring.",
    },
  ],
  "tycho-crater": [
    {
      site_id: "meteor-crater-arizona",
      name: "Barringer Meteor Crater",
      country: "USA (Arizona)",
      coordinates: { lat: 35.03, lng: -111.02 },
      similarity_score: 96.2,
      breakdown: { topography_match: 98, geochemistry_match: 94, climate_match: 96 },
      metadata: { elevation_m: 1740, primary_rock: "Coesite, Stishovite & Impact Breccia", accessibility_rating: "Very High" },
      rationale: "Pristine simple impact crater preserving overturned rim stratigraphy, ejecta blanket, and shocked quartz.",
    },
    {
      site_id: "lonar-crater-india",
      name: "Lonar Impact Crater",
      country: "India (Maharashtra)",
      coordinates: { lat: 19.97, lng: 76.51 },
      similarity_score: 92.1,
      breakdown: { topography_match: 94, geochemistry_match: 95, climate_match: 87 },
      metadata: { elevation_m: 563, primary_rock: "Deccan Basalt & Maskelynite", accessibility_rating: "High" },
      rationale: "The only known hypervelocity impact crater carved directly into flood basalt, exactly like lunar mare craters.",
    },
  ],
};

const DEFAULT_ANALOGS = [
  {
    site_id: "atacama-desert-yungay",
    name: "Atacama Desert (Yungay)",
    country: "Chile",
    coordinates: { lat: -23.5, lng: -68.2 },
    similarity_score: 94.2,
    breakdown: { topography_match: 91, geochemistry_match: 97, climate_match: 95 },
    metadata: { elevation_m: 2300, primary_rock: "Halite & Nitrate Evaporites", accessibility_rating: "High" },
    rationale: "Hyper-arid terrain with extreme diurnal shifts, high ultraviolet radiation, and Mars-like evaporite salt crusts.",
  },
  {
    site_id: "mcmurdo-dry-valleys",
    name: "McMurdo Dry Valleys",
    country: "Antarctica",
    coordinates: { lat: -77.5, lng: 161.0 },
    similarity_score: 91.8,
    breakdown: { topography_match: 89, geochemistry_match: 88, climate_match: 98 },
    metadata: { elevation_m: 300, primary_rock: "Permafrost & Basalt Breccia", accessibility_rating: "Challenging" },
    rationale: "Polar cold-desert analog with near-zero precipitation and cryogenic freeze-thaw patterning.",
  },
  {
    site_id: "mauna-kea-volcanic",
    name: "Mauna Kea Volcanic Ridge",
    country: "USA (Hawaii)",
    coordinates: { lat: 19.5, lng: -155.5 },
    similarity_score: 88.7,
    breakdown: { topography_match: 95, geochemistry_match: 92, climate_match: 79 },
    metadata: { elevation_m: 4200, primary_rock: "Weathered Alkaline Basalt", accessibility_rating: "Very High" },
    rationale: "Shield volcano basalt flow sequences and cinder cones frequently utilized for rover mobility and instrument calibration.",
  },
  {
    site_id: "svalbard-analog-c",
    name: "Svalbard Volcanic Field",
    country: "Norway",
    coordinates: { lat: 78.0, lng: 16.0 },
    similarity_score: 86.4,
    breakdown: { topography_match: 85, geochemistry_match: 89, climate_match: 85 },
    metadata: { elevation_m: 120, primary_rock: "Volcanic Rock & Basalt", accessibility_rating: "Moderate" },
    rationale: "High-latitude permafrost landscape exposing volcanic pipes and carbonate mantle nodules.",
  },
  {
    site_id: "rio-tinto-basin",
    name: "Río Tinto Gossan Field",
    country: "Spain",
    coordinates: { lat: 37.7, lng: -6.6 },
    similarity_score: 85.1,
    breakdown: { topography_match: 78, geochemistry_match: 98, climate_match: 80 },
    metadata: { elevation_m: 350, primary_rock: "Jarosite & Iron Sulfates", accessibility_rating: "High" },
    rationale: "Acid mine drainage and gossan deposits that produce spectral signatures identical to Martian jarosite.",
  },
  {
    site_id: "askja-iceland-analog",
    name: "Askja Volcanic Caldera",
    country: "Iceland",
    coordinates: { lat: 65.03, lng: -16.75 },
    similarity_score: 83.9,
    breakdown: { topography_match: 89, geochemistry_match: 84, climate_match: 79 },
    metadata: { elevation_m: 1100, primary_rock: "Basaltic Tephra & Pumice", accessibility_rating: "Moderate" },
    rationale: "Remote volcanic caldera in the Icelandic highlands used by NASA Apollo astronauts for lunar geology training.",
  },
];

async function readError(response, fallback) {
  const body = await response.json().catch(() => ({}));
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const text = detail.map((item) => item.msg || item.message).filter(Boolean).join(" ");
    if (text) return text;
  }
  return fallback;
}

async function request(path, options) {
  let response;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch {
    throw new ApiError(0, "The API could not be reached. Falling back to calibrated seed data.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response, `Request failed: ${response.status}`));
  }
  return response.json();
}

export function getHealth() {
  return request("/api/v1/health").catch(() => ({ status: "offline", database: "disconnected" }));
}

export async function getTargets(planet) {
  const query = planet ? `?planet=${encodeURIComponent(planet)}` : "";
  try {
    const result = await request(`/api/v1/targets${query}`);
    if (result && Array.isArray(result.targets) && result.targets.length > 0) {
      return result;
    }
  } catch {
    // Graceful offline fallback
  }
  const filtered = planet
    ? FALLBACK_TARGETS_DATA.filter((t) => t.planet === planet)
    : FALLBACK_TARGETS_DATA;
  return { targets: filtered };
}

export function getTarget(siteId, planet) {
  return request(`/api/v1/targets/${encodeURIComponent(siteId)}?planet=${encodeURIComponent(planet)}`).catch(() => {
    const found = FALLBACK_TARGETS_DATA.find((t) => t.site_id === siteId);
    if (found) return found;
    throw new ApiError(404, "Target site not found");
  });
}

export async function searchAnalogs(payload) {
  try {
    const result = await request("/api/v1/analogs/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (result && Array.isArray(result.analogs) && result.analogs.length > 0) {
      return result;
    }
  } catch {
    // Graceful offline fallback
  }

  // Target-specific calibrated response
  const targetId = payload.target_site_id;
  const specific = SITE_ANALOG_MAP[targetId] || [];
  const otherDefaults = DEFAULT_ANALOGS.filter(
    (d) => !specific.some((s) => s.site_id === d.site_id)
  );
  const combined = [...specific, ...otherDefaults].slice(0, 6);

  return {
    target_planet: payload.target_planet,
    target_site_id: payload.target_site_id,
    analogs: combined,
    total: combined.length,
    is_fallback: true,
  };
}
