import { useEffect, useMemo, useRef, useState } from "react";
import "./index.css";
import { getTargets, searchAnalogs, getHealth, FALLBACK_TARGETS_DATA } from "./api.js";
import { PlanetaryGlobe, EarthGlobe, CelestialTrinity, PlanetView } from "./Globe.jsx";

type Planet = "moon" | "mars";
type ViewMode = "landing" | "warp" | "trinity" | "dual";

type Target = {
  planet: Planet;
  site_id: string;
  site_name: string;
  coordinates: { lat: number; lng: number };
  avg_slope_deg: number | null;
  elevation_m: number | null;
  primary_rock: string | null;
  temp_range_c: number[] | null;
  data_source: string;
  description?: string;
};

type Analog = {
  site_id: string;
  name: string;
  country: string;
  coordinates: { lat: number; lng: number };
  similarity_score: number;
  breakdown: { topography_match: number; geochemistry_match: number; climate_match: number };
  metadata: { elevation_m: number | null; primary_rock: string | null; accessibility_rating: string };
  rationale?: string;
};

const SEARCH_WEIGHTS = {
  weights: { topography: 0.4, geochemistry: 0.35, climate: 0.25 },
  constraints: { subterranean_only: false, min_similarity: 0, limit: 20 },
};

function formatCoord(lat: number, lng: number) {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lng >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns} · ${Math.abs(lng).toFixed(2)}°${ew}`;
}

function formatNumber(value: number | null | undefined, suffix = "") {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value).toLocaleString("en-US")}${suffix}`;
}

function downloadGeoJson(analog: Analog, target?: Target | null) {
  const feature = {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [analog.coordinates.lng, analog.coordinates.lat],
    },
    properties: {
      site_id: analog.site_id,
      name: analog.name,
      country: analog.country,
      similarity_score: analog.similarity_score,
      target_planet: target?.planet ?? "unknown",
      target_crater: target?.site_name ?? "unknown",
      topography_match: analog.breakdown.topography_match,
      geochemistry_match: analog.breakdown.geochemistry_match,
      climate_match: analog.breakdown.climate_match,
      elevation_m: analog.metadata.elevation_m,
      primary_rock: analog.metadata.primary_rock,
      accessibility_rating: analog.metadata.accessibility_rating,
      scientific_rationale: analog.rationale ?? "",
    },
  };

  const blob = new Blob([JSON.stringify(feature, null, 2)], { type: "application/geo+json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${analog.site_id}.geojson`;
  a.click();
  URL.revokeObjectURL(url);
}

function Logo() {
  return (
    <div className="logo">
      <span className="logo-mark">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="3" />
          <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-25 12 12)" />
        </svg>
      </span>
      <span>
        ASTRO<span>TERRAIN</span>
      </span>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<ViewMode>("landing");
  const [planet, setPlanet] = useState<Planet>("mars");
  const [allTargets, setAllTargets] = useState<Target[]>(FALLBACK_TARGETS_DATA as Target[]);
  const [selectedTargetId, setSelectedTargetId] = useState<string>("jezero-crater");
  const [analogs, setAnalogs] = useState<Analog[]>([]);
  const [selectedAnalogId, setSelectedAnalogId] = useState<string | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [loadingAnalogs, setLoadingAnalogs] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState<string>("OPERATIONAL");

  const planetGlobeRef = useRef<{ zoomBy: (f: number) => void; reset: () => void; focus?: (lat: number, lng: number) => void } | null>(null);
  const earthGlobeRef = useRef<{ zoomBy: (f: number) => void; reset: () => void; focus?: (lat: number, lng: number) => void } | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Targets for the currently active planet (Moon or Mars)
  const planetTargets = useMemo(() => {
    return allTargets.filter((t) => t.planet === planet);
  }, [allTargets, planet]);

  // Active Target Crater
  const selectedTarget = useMemo(() => {
    return allTargets.find((t) => t.site_id === selectedTargetId && t.planet === planet)
      ?? planetTargets[0]
      ?? allTargets[0]
      ?? null;
  }, [allTargets, selectedTargetId, planet, planetTargets]);

  // Active Earth Analog
  const selectedAnalog = useMemo(() => {
    return analogs.find((a) => a.site_id === selectedAnalogId) ?? analogs[0] ?? null;
  }, [analogs, selectedAnalogId]);

  // Search Results across ALL celestial bodies (Moon & Mars)
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allTargets;
    return allTargets.filter(
      (t) =>
        t.site_name.toLowerCase().includes(q) ||
        t.site_id.toLowerCase().includes(q) ||
        (t.primary_rock && t.primary_rock.toLowerCase().includes(q)) ||
        t.planet.toLowerCase().includes(q)
    );
  }, [allTargets, searchQuery]);

  // Initial data loading
  useEffect(() => {
    getHealth().then((h) => {
      if (h.status === "ok") setHealthStatus("OPERATIONAL");
      else setHealthStatus("DEGRADED");
    }).catch(() => setHealthStatus("OFFLINE"));

    // Fetch targets for moon and mars
    Promise.all([getTargets("moon"), getTargets("mars")])
      .then(([moonRes, marsRes]) => {
        const combined = [...(moonRes.targets ?? []), ...(marsRes.targets ?? [])];
        if (combined.length > 0) {
          setAllTargets(combined);
        }
      })
      .catch(() => {
        // Fallback already preloaded
      });
  }, []);

  // Warp screen auto-transition to trinity
  useEffect(() => {
    if (view !== "warp") return;
    const timer = setTimeout(() => {
      setView("trinity");
    }, 1450);
    return () => clearTimeout(timer);
  }, [view]);

  // Fetch Earth Analogs whenever the selected target changes
  useEffect(() => {
    if (!selectedTarget) return;

    let cancelled = false;
    setLoadingAnalogs(true);

    searchAnalogs({
      target_planet: selectedTarget.planet,
      target_site_id: selectedTarget.site_id,
      ...SEARCH_WEIGHTS,
    })
      .then((res) => {
        if (cancelled) return;
        const list = res.analogs ?? [];
        setAnalogs(list);
        if (list.length > 0) {
          setSelectedAnalogId(list[0].site_id);
        }
      })
      .catch(() => {
        if (!cancelled) setAnalogs([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingAnalogs(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTarget]);

  // Handle crater hotspot selection from search or click
  const selectCrater = (t: Target) => {
    setPlanet(t.planet);
    setSelectedTargetId(t.site_id);
    setSearchQuery("");
    setSearchOpen(false);
    setView("dual");
  };

  // Handle direct planet selection from rotating triangle
  const selectPlanetFromTrinity = (p: Planet) => {
    setPlanet(p);
    const first = allTargets.find((t) => t.planet === p);
    if (first) {
      setSelectedTargetId(first.site_id);
    }
    setView("dual");
  };

  return (
    <div className="figma-app astroterrain-dual-app">
      {/* ══════════════════════════════════════════════════════════════════
          1. WARP HYPER-SPACE TRANSITION SCREEN
         ══════════════════════════════════════════════════════════════════ */}
      {view === "warp" && (
        <div className="warp">
          <Logo />
          <div className="warp-lines" />
          <span>INITIALIZING TERRAIN ENGINE</span>
          <small>CALIBRATING ORBITAL TRINITY & CELESTIAL VECTORS</small>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          2. THE FIRST SCREEN: ORIGINAL LAUNCH & DESCEND LANDING PAGE
         ══════════════════════════════════════════════════════════════════ */}
      {view === "landing" && (
        <main className="landing">
          <div className="stars" />
          <div className="planet moon" />
          <div className="planet mars" />

          {/* Top Navbar */}
          <nav className="landing-nav">
            <Logo />
            <div className="nav-actions">
              <span className="nasa-source">
                NASA OPEN DATA <b>LRO · MRO</b>
              </span>
              <span className="status">
                <i /> API <b>{healthStatus}</b>
              </span>
              <button className="btn primary" onClick={() => setView("warp")}>
                Launch engine <i>→</i>
              </button>
            </div>
          </nav>

          {/* Mission Ribbon */}
          <div className="mission-ribbon">
            <span>ASTROTERRAIN / MISSION ANALOG SYSTEM</span>
            <span>DATABASE {healthStatus === "OPERATIONAL" ? "CONNECTED" : "FALLBACK"}</span>
            <span>{String(allTargets.length).padStart(2, "0")} RECON TARGETS</span>
            <span>{selectedTarget?.data_source?.replaceAll("_", " ")?.toUpperCase() ?? "LOLA / MGS READY"}</span>
          </div>

          {/* Hero Launch Stage */}
          <section className="launch-stage">
            <div className="launch-copy">
              <div className="eyebrow">
                <span>PLANETARY ANALOG EXPLORER / 2026</span>
                <i />
              </div>
              <h1>
                Earth is our
                <br />
                <em>testing ground.</em>
              </h1>
              <p>
                Find the places on Earth that behave like another world. Compare terrain, climate, and geochemistry using
                the analog search ML pipeline and multi-planetary 3D globes.
              </p>

              <button className="launch-cta" onClick={() => setView("warp")}>
                <span>Begin mission</span>
                <i>→</i>
              </button>
            </div>

            {/* Circular Orbital Display with 3D Spinning Planet */}
            <div className={`orbital-display ${planet === "mars" ? "mars" : ""}`}>
              <div className="orbit-ring ring-one" />
              <div className="orbit-ring ring-two" />
              <div className="orbit-ring ring-three" />
              <div className="crosshair horizontal" />
              <div className="crosshair vertical" />
              <PlanetView body={planet} />
              <div className="planet-scan" />
              <span className="orbit-label label-a">{planet.toUpperCase()}</span>
              <span className="orbit-label label-b">{selectedTarget ? `${formatNumber(selectedTarget.elevation_m, " M")}` : "NO TARGET"}</span>
              <div className="target-readout">
                <span>ACTIVE TARGET / {planet === "mars" ? "MARTIAN" : "LUNAR"}</span>
                <strong>{selectedTarget ? selectedTarget.site_name.replace(/ \(synthetic demo profile\)/i, "") : "Loading"}</strong>
                <small>{selectedTarget ? formatCoord(selectedTarget.coordinates.lat, selectedTarget.coordinates.lng) : "—"}</small>
              </div>
            </div>

            {/* Target Destination Selector Strip */}
            <div className="mission-selector">
              <span className="selector-caption">CHOOSE DESTINATION</span>
              {allTargets.slice(0, 4).map((item, index) => {
                const isActive = selectedTarget?.site_id === item.site_id && planet === item.planet;
                return (
                  <button
                    key={`${item.planet}-${item.site_id}`}
                    className={`${isActive ? "active" : ""} ${item.planet === "mars" ? "mars-choice" : ""}`}
                    onClick={() => {
                      setPlanet(item.planet);
                      setSelectedTargetId(item.site_id);
                    }}
                  >
                    <i>{String(index + 1).padStart(2, "0")}</i>
                    <span>
                      <small>
                        {item.planet.toUpperCase()} / {item.site_id.replaceAll("-", " ").toUpperCase()}
                      </small>
                      <b>{item.site_name}</b>
                      <em>{formatCoord(item.coordinates.lat, item.coordinates.lng).split(" · ")[0]}</em>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        </main>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          3. CINEMATIC ROTATING TRIANGLE: EARTH, MARS & MOON + SEARCH BAR
         ══════════════════════════════════════════════════════════════════ */}
      {view === "trinity" && (
        <main className="trinity-stage">
          {/* Top Trinity Nav */}
          <header className="dash-nav trinity-nav">
            <button className="plain" onClick={() => setView("landing")}>
              <Logo />
            </button>
            <div className="trinity-mission-tag">
              <span className="mono">ORBITAL CONSTELLATION / EARTH ⟷ MARS ⟷ MOON</span>
            </div>
            <div className="dash-meta">
              <button className="btn secondary return-btn" onClick={() => setView("landing")}>
                ⟵ Return to Launch
              </button>
              <button
                type="button"
                className={`orbit-toggle-btn ${autoRotate ? "is-orbiting" : ""}`}
                onClick={() => setAutoRotate((prev) => !prev)}
              >
                <i></i> ORBIT: {autoRotate ? "ON" : "OFF"}
              </button>
            </div>
          </header>

          {/* 3D Rotating Constellation Canvas */}
          <div className="trinity-canvas-wrapper">
            <CelestialTrinity onSelectPlanet={selectPlanetFromTrinity} />
          </div>

          {/* Floating Search Bar & Hero UI on Trinity Screen */}
          <div className="trinity-overlay-container">
            <div className="trinity-hero-badge">
              <span className="trinity-badge-tag">CELESTIAL RECONNAISSANCE TRINITY</span>
              <h1>Interplanetary Analog Hub</h1>
              <p>
                Click <strong>Moon</strong> or <strong>Mars</strong> directly in the rotating constellation, or search
                any crater below to cinematically pair it with its closest Earth analog.
              </p>
            </div>

            {/* Central Futuristic Search Bar */}
            <div className="trinity-search-box-wrap">
              <div className={`trinity-search-input-box ${searchOpen ? "is-focused" : ""}`}>
                <span className="search-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </span>
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search any crater or hotspot on Moon or Mars (e.g. Jezero, Shackleton, Gale, Olympus)..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSearchOpen(true);
                  }}
                  onFocus={() => setSearchOpen(true)}
                />
                {searchQuery && (
                  <button className="search-clear-btn" onClick={() => setSearchQuery("")}>
                    ✕
                  </button>
                )}
                <span className="search-hotkey-badge">SELECT CRATER</span>
              </div>

              {/* Autocomplete Results Dropdown */}
              {searchOpen && (
                <div className="trinity-search-dropdown">
                  <div className="dropdown-head">
                    <span>MATCHING HOTSPOTS ({searchResults.length})</span>
                    <button onClick={() => setSearchOpen(false)}>Close ✕</button>
                  </div>
                  <div className="dropdown-list-scroll">
                    {searchResults.map((t) => (
                      <div
                        key={`${t.planet}-${t.site_id}`}
                        className={`dropdown-item ${t.planet === "mars" ? "mars-item" : "moon-item"}`}
                        onClick={() => selectCrater(t)}
                      >
                        <div className="dropdown-item-orb">
                          <span className={`toggle-orb ${t.planet === "mars" ? "mars-orb" : "moon-orb"}`} />
                        </div>
                        <div className="dropdown-item-info">
                          <div className="item-title-row">
                            <strong>{t.site_name}</strong>
                            <span className={`item-planet-tag ${t.planet === "mars" ? "mars-tag" : "moon-tag"}`}>
                              {t.planet.toUpperCase()}
                            </span>
                          </div>
                          <div className="item-details-row">
                            <span>{formatCoord(t.coordinates.lat, t.coordinates.lng)}</span>
                            <span>{t.primary_rock?.split("&")[0]?.split("/")[0] ?? "Regolith"}</span>
                            {t.elevation_m != null && <b className="item-elev">{formatNumber(t.elevation_m, "m")}</b>}
                          </div>
                        </div>
                        <span className="dropdown-item-arrow">→</span>
                      </div>
                    ))}
                    {searchResults.length === 0 && (
                      <div className="dropdown-empty">
                        <p>No craters matched "{searchQuery}". Try searching "Jezero", "Shackleton", "Tycho", or "Olympus".</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Quick Preset Hotspot Chips */}
              <div className="trinity-preset-chips">
                <span className="chips-label">QUICK RECON:</span>
                {allTargets.slice(0, 5).map((t) => (
                  <button
                    key={t.site_id}
                    type="button"
                    className={`trinity-chip ${t.planet === "mars" ? "chip-mars" : "chip-moon"}`}
                    onClick={() => selectCrater(t)}
                  >
                    <i>{t.planet === "mars" ? "♂" : "🌔"}</i>
                    <span>{t.site_name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Bottom Constellation Helper Navigation */}
            <div className="trinity-dest-cards">
              <div className="dest-card moon-card" onClick={() => selectPlanetFromTrinity("moon")}>
                <div className="dest-card-orb moon-orb" />
                <div>
                  <small>CELESTIAL RECON</small>
                  <strong>MOON</strong>
                  <span>{allTargets.filter((t) => t.planet === "moon").length} Crater Hotspots</span>
                </div>
                <button className="dest-open-btn">Pair with Earth →</button>
              </div>

              <div className="dest-card mars-card" onClick={() => selectPlanetFromTrinity("mars")}>
                <div className="dest-card-orb mars-orb" />
                <div>
                  <small>CELESTIAL RECON</small>
                  <strong>MARS</strong>
                  <span>{allTargets.filter((t) => t.planet === "mars").length} Crater Hotspots</span>
                </div>
                <button className="dest-open-btn">Pair with Earth →</button>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          4. CINEMATIC DUAL-GLOBE PAIRING: MOON/MARS BESIDE EARTH
         ══════════════════════════════════════════════════════════════════ */}
      {view === "dual" && (
        <div className="dual-exploration-stage">
          {/* Top Dual Mission Navigation */}
          <header className="dash-nav">
            <button className="plain" onClick={() => setView("trinity")}>
              <Logo />
            </button>

            {/* Navigation back to Trinity Constellation */}
            <button className="btn secondary return-trinity-btn" onClick={() => setView("trinity")}>
              ⟵ Celestial Trinity
            </button>

            {/* In-Nav Crater Search Input */}
            <div className="nav-search-wrap">
              <input
                type="text"
                placeholder="Search any crater..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
              />
              {searchOpen && (
                <div className="nav-search-dropdown">
                  {searchResults.slice(0, 6).map((t) => (
                    <div
                      key={`${t.planet}-${t.site_id}`}
                      className="nav-search-item"
                      onClick={() => selectCrater(t)}
                    >
                      <span>{t.planet === "mars" ? "♂" : "🌔"} {t.site_name}</span>
                      <small>{t.planet.toUpperCase()}</small>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Planet Switcher: Moon ⟷ Mars */}
            <div className="planet-toggle-control">
              <button
                type="button"
                className={`planet-toggle-btn ${planet === "moon" ? "active moon-active" : ""}`}
                onClick={() => setPlanet("moon")}
              >
                <span className="toggle-orb moon-orb" />
                <span>MOON</span>
                <small>{planet === "moon" ? `${planetTargets.length} SITES` : ""}</small>
              </button>
              <button
                type="button"
                className={`planet-toggle-btn ${planet === "mars" ? "active mars-active" : ""}`}
                onClick={() => setPlanet("mars")}
              >
                <span className="toggle-orb mars-orb" />
                <span>MARS</span>
                <small>{planet === "mars" ? `${planetTargets.length} SITES` : ""}</small>
              </button>
            </div>

            {/* Telemetry & Auto-Orbit Controls */}
            <div className="dash-meta">
              <button
                type="button"
                className={`orbit-toggle-btn ${autoRotate ? "is-orbiting" : ""}`}
                onClick={() => setAutoRotate((prev) => !prev)}
                title="Toggle orbital auto-rotation on both globes"
              >
                <i></i> AUTO-ORBIT: {autoRotate ? "ON" : "OFF"}
              </button>
              <span className="status">
                <i /> {loadingAnalogs ? "SEARCHING EARTH" : "DUAL 3D SYNC"}
              </span>
            </div>
          </header>

          {/* Dual Split Globes: Left Moon/Mars beside Right Earth */}
          <div className="dual-globes-viewport-grid">
            {/* ──── LEFT GLOBE: Target Celestial Body (Moon or Mars) ──── */}
            <section className="globe-panel planet-panel">
              <div className="globe-panel-header">
                <div className="panel-badge-group">
                  <span className={`planet-tag ${planet === "mars" ? "mars-tag" : "moon-tag"}`}>
                    TARGET BODY / {planet.toUpperCase()}
                  </span>
                  <h2>{selectedTarget ? selectedTarget.site_name : `${planet.toUpperCase()} HOTSPOTS`}</h2>
                  <div className="coord-chip mono">
                    {selectedTarget ? formatCoord(selectedTarget.coordinates.lat, selectedTarget.coordinates.lng) : "—"}
                  </div>
                </div>

                {/* Crater selector chips */}
                <div className="crater-chips-bar">
                  {planetTargets.map((t) => {
                    const isActive = t.site_id === selectedTargetId;
                    return (
                      <button
                        key={t.site_id}
                        type="button"
                        className={`crater-chip ${isActive ? "is-active" : ""}`}
                        onClick={() => setSelectedTargetId(t.site_id)}
                        title={t.site_name}
                      >
                        <span>{t.site_name}</span>
                        {t.elevation_m != null && <small>{Math.round(t.elevation_m)}m</small>}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3D Planetary Globe */}
              <div className="globe-render-box">
                <PlanetaryGlobe
                  ref={planetGlobeRef}
                  planet={planet}
                  targets={planetTargets}
                  selectedId={selectedTargetId}
                  onSelectTarget={(id) => setSelectedTargetId(id)}
                  autoRotate={autoRotate}
                />
              </div>

              {/* Planet Camera Zoom & Reset Controls */}
              <div className="globe-floating-tools left-tools">
                <button aria-label="Zoom in target" onClick={() => planetGlobeRef.current?.zoomBy(0.8)}>
                  +
                </button>
                <button aria-label="Zoom out target" onClick={() => planetGlobeRef.current?.zoomBy(1.25)}>
                  −
                </button>
                <i />
                <button
                  aria-label="Reset target view"
                  onClick={() => planetGlobeRef.current?.reset()}
                  title="Reset planetary camera"
                >
                  ⟲
                </button>
              </div>
            </section>

            {/* ──── CENTER CORRELATION & SCANNING BRIDGE ──── */}
            <div className="analog-match-bridge">
              <div className="bridge-indicator">
                <div className={`bridge-pulse-dot ${loadingAnalogs ? "is-pulsing" : ""}`} />
                <span className="bridge-status-text">
                  {loadingAnalogs ? "CORRELATING..." : `${Math.round(selectedAnalog?.similarity_score ?? 0)}% SIMILARITY`}
                </span>
                <div className="bridge-laser-line" />
              </div>
            </div>

            {/* ──── RIGHT GLOBE: Earth Terrestrial Analogs ──── */}
            <section className="globe-panel earth-panel">
              <div className="globe-panel-header">
                <div className="panel-badge-group">
                  <span className="planet-tag earth-tag">
                    TERRESTRIAL ANALOG / EARTH
                  </span>
                  <h2>{selectedAnalog ? selectedAnalog.name : "Earth Analogs"}</h2>
                  <div className="coord-chip mono">
                    {selectedAnalog ? `${selectedAnalog.country} · ${formatCoord(selectedAnalog.coordinates.lat, selectedAnalog.coordinates.lng)}` : "—"}
                  </div>
                </div>

                {/* Matched Earth analog candidate selector tabs */}
                <div className="crater-chips-bar analog-chips-bar">
                  {analogs.map((a, idx) => {
                    const isActive = a.site_id === selectedAnalogId;
                    return (
                      <button
                        key={a.site_id}
                        type="button"
                        className={`crater-chip analog-chip ${isActive ? "is-active" : ""}`}
                        onClick={() => setSelectedAnalogId(a.site_id)}
                        title={`${a.name} (${Math.round(a.similarity_score)}% match)`}
                      >
                        <b className="analog-rank">#{idx + 1}</b>
                        <span>{a.name.split(" ")[0]}</span>
                        <small>{Math.round(a.similarity_score)}%</small>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3D Earth Globe with Atmosphere & Clouds */}
              <div className="globe-render-box">
                <EarthGlobe
                  ref={earthGlobeRef}
                  analogs={analogs}
                  selectedId={selectedAnalogId}
                  onSelectAnalog={(id) => setSelectedAnalogId(id)}
                  autoRotate={autoRotate}
                  isSearching={loadingAnalogs}
                />
              </div>

              {/* Earth Camera Zoom & Reset Controls */}
              <div className="globe-floating-tools right-tools">
                <button aria-label="Zoom in Earth" onClick={() => earthGlobeRef.current?.zoomBy(0.8)}>
                  +
                </button>
                <button aria-label="Zoom out Earth" onClick={() => earthGlobeRef.current?.zoomBy(1.25)}>
                  −
                </button>
                <i />
                <button
                  aria-label="Reset Earth view"
                  onClick={() => earthGlobeRef.current?.reset()}
                  title="Reset Earth camera"
                >
                  ⟲
                </button>
              </div>
            </section>
          </div>

          {/* Bottom Systematic Comparative Telemetry Deck */}
          <footer className="comparative-telemetry-deck">
            {selectedTarget && selectedAnalog ? (
              <div className="deck-grid">
                {/* Column 1: Planetary Crater Telemetry */}
                <div className="deck-card planet-tele-card">
                  <div className="deck-card-top">
                    <span className="card-badge">{planet.toUpperCase()} HOTSPOT SPECS</span>
                    <h4>{selectedTarget.site_name}</h4>
                  </div>
                  <p className="deck-description">{selectedTarget.description ?? "Planetary reconnaissance site."}</p>
                  <div className="telemetry-compact-grid">
                    <div className="tele-metric">
                      <small>ELEVATION</small>
                      <b>{formatNumber(selectedTarget.elevation_m, " m")}</b>
                    </div>
                    <div className="tele-metric">
                      <small>AVG SLOPE</small>
                      <b>{selectedTarget.avg_slope_deg != null ? `${selectedTarget.avg_slope_deg}°` : "—"}</b>
                    </div>
                    <div className="tele-metric">
                      <small>PRIMARY ROCK</small>
                      <b>{selectedTarget.primary_rock ?? "Regolith"}</b>
                    </div>
                    <div className="tele-metric">
                      <small>DATA SOURCE</small>
                      <b>{selectedTarget.data_source.split("/")[0]}</b>
                    </div>
                  </div>
                </div>

                {/* Column 2: Composite Similarity & Score Breakdown */}
                <div className="deck-card correlation-card">
                  <div className="deck-card-top">
                    <span className="card-badge highlight-badge">COMPOSITE CORRELATION</span>
                    <div className="score-summary">
                      <span className="large-score">{Math.round(selectedAnalog.similarity_score)}%</span>
                      <small>CORRELATION INDEX</small>
                    </div>
                  </div>

                  {/* Score Breakdown Progress Bars */}
                  <div className="breakdown-stack">
                    <div className="breakdown-item">
                      <div className="breakdown-label-row">
                        <span>Topography Match</span>
                        <b>{Math.round(selectedAnalog.breakdown.topography_match)}%</b>
                      </div>
                      <div className="breakdown-bar">
                        <div
                          className="bar-fill topo-bar"
                          style={{ width: `${Math.round(selectedAnalog.breakdown.topography_match)}%` }}
                        />
                      </div>
                    </div>

                    <div className="breakdown-item">
                      <div className="breakdown-label-row">
                        <span>Geochemistry Match</span>
                        <b>{Math.round(selectedAnalog.breakdown.geochemistry_match)}%</b>
                      </div>
                      <div className="breakdown-bar">
                        <div
                          className="bar-fill geochem-bar"
                          style={{ width: `${Math.round(selectedAnalog.breakdown.geochemistry_match)}%` }}
                        />
                      </div>
                    </div>

                    <div className="breakdown-item">
                      <div className="breakdown-label-row">
                        <span>Climate Match</span>
                        <b>{Math.round(selectedAnalog.breakdown.climate_match)}%</b>
                      </div>
                      <div className="breakdown-bar">
                        <div
                          className="bar-fill climate-bar"
                          style={{ width: `${Math.round(selectedAnalog.breakdown.climate_match)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="scientific-rationale-note">
                    <small>SCIENTIFIC RATIONALE:</small>
                    <p>{selectedAnalog.rationale ?? "High geochemical and topographical correlation index."}</p>
                  </div>
                </div>

                {/* Column 3: Earth Analog Telemetry & GeoJSON Export */}
                <div className="deck-card earth-tele-card">
                  <div className="deck-card-top">
                    <span className="card-badge earth-badge">EARTH ANALOG SPECS</span>
                    <h4>{selectedAnalog.name}</h4>
                  </div>
                  <div className="telemetry-compact-grid">
                    <div className="tele-metric">
                      <small>COUNTRY</small>
                      <b>{selectedAnalog.country}</b>
                    </div>
                    <div className="tele-metric">
                      <small>ELEVATION</small>
                      <b>{formatNumber(selectedAnalog.metadata.elevation_m, " m")}</b>
                    </div>
                    <div className="tele-metric">
                      <small>PRIMARY ROCK</small>
                      <b>{selectedAnalog.metadata.primary_rock ?? "Basalt"}</b>
                    </div>
                    <div className="tele-metric">
                      <small>ACCESSIBILITY</small>
                      <b>{selectedAnalog.metadata.accessibility_rating}</b>
                    </div>
                  </div>

                  <div className="deck-actions">
                    <button
                      type="button"
                      className="geojson-export-btn"
                      onClick={() => downloadGeoJson(selectedAnalog, selectedTarget)}
                      title="Export GeoJSON with [lng, lat] coordinate order per GLOBE_PRANJIL.md"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                      Download GeoJSON [lng, lat]
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="deck-loading-state">
                <span className="mono">INITIALIZING TELEMETRY BRIDGE...</span>
              </div>
            )}
          </footer>

          {/* Operational Bottom Strip */}
          <div className="mission-footer-strip">
            <span><b>TARGET:</b> {selectedTarget?.site_name ?? planet.toUpperCase()}</span>
            <span><b>EARTH ANALOG:</b> {selectedAnalog ? `${selectedAnalog.name} (${selectedAnalog.country})` : "—"}</span>
            <span><b>COORDINATE ORDER:</b> [lng, lat] GeoJSON compliant</span>
            <span className="footer-status-pill">
              ASTROTERRAIN API / v1 CONNECTED
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
