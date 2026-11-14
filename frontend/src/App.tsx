import { useEffect, useMemo, useRef, useState } from "react";
import "./index.css";
import { ApiError, getHealth, getTargets, searchAnalogs } from "./api.js";
import { EarthView, PlanetView } from "./Globe.jsx";

type IconName = "orbit" | "arrow" | "layers" | "download" | "target" | "cube" | "scan" | "plus" | "minus" | "chevron";
type Planet = "moon" | "mars";
type Layer = "similarity" | "topography" | "mineralogy" | "climate";

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
};

type Analog = {
  site_id: string;
  name: string;
  country: string;
  coordinates: { lat: number; lng: number };
  similarity_score: number;
  breakdown: { topography_match: number; geochemistry_match: number; climate_match: number };
  metadata: { elevation_m: number | null; primary_rock: string | null; accessibility_rating: string };
};

type Health = { status: string; database?: string };

const FALLBACK_TARGETS: Target[] = [
  { planet: "moon", site_id: "shackleton-crater", site_name: "Shackleton Crater", coordinates: { lat: -89.9, lng: 0 }, avg_slope_deg: null, elevation_m: null, primary_rock: null, temp_range_c: null, data_source: "offline" },
  { planet: "mars", site_id: "jezero-crater", site_name: "Jezero Crater", coordinates: { lat: 18.38, lng: 77.58 }, avg_slope_deg: null, elevation_m: null, primary_rock: null, temp_range_c: null, data_source: "offline" },
];

const SEARCH_BODY = {
  weights: { topography: 0.4, geochemistry: 0.35, climate: 0.25 },
  constraints: { subterranean_only: false, min_similarity: 0, limit: 20 },
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    orbit: <><circle cx="12" cy="12" r="3"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-25 12 12)"/><path d="M5 4.5c2-2 6.7-.8 10.5 2.7s5.4 7.8 3.5 10"/></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5"/><path d="M5 21h14"/></>,
    target: <><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2V0M12 24v-2M2 12H0M24 12h-2"/></>,
    cube: <><path d="m12 2 9 5v10l-9 5-9-5V7l9-5Z"/><path d="m3 7 9 5 9-5M12 22V12"/></>,
    scan: <><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/><circle cx="12" cy="12" r="3"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    minus: <path d="M5 12h14"/>,
    chevron: <path d="m8 10 4 4 4-4"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{paths[name]}</svg>;
}

function Logo() {
  return <div className="logo"><span className="logo-mark"><Icon name="orbit" size={22}/></span><span>ASTRO<span>TERRAIN</span></span></div>;
}

function formatCoord(lat: number, lng: number) {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lng >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns} · ${Math.abs(lng).toFixed(2)}°${ew}`;
}

function formatNumber(value: number | null | undefined, suffix = "") {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value).toLocaleString("en-US")}${suffix}`;
}

function errorText(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) return error.message;
    if (error.status === 422) return error.message || "The search filters were rejected.";
    if (error.status === 0) return error.message;
    return error.message;
  }
  return "Something went wrong while talking to the API.";
}

function pinLabel(site: Analog, layer: Layer) {
  if (layer === "topography") return `${Math.round(site.breakdown.topography_match)}%`;
  if (layer === "climate") return `${Math.round(site.breakdown.climate_match)}%`;
  if (layer === "mineralogy") return (site.metadata.primary_rock ?? "—").toUpperCase();
  return `${Math.round(site.similarity_score)}%`;
}

function download(filename: string, contents: string, type: string) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function Landing({
  targets,
  target,
  health,
  error,
  onSelect,
  onLaunch,
}: {
  targets: Target[];
  target: Target | null;
  health: Health | null;
  error: string | null;
  onSelect: (target: Target) => void;
  onLaunch: () => void;
}) {
  const planet = target?.planet ?? "moon";
  const apiLabel = !health ? "CHECKING" : health.status === "ok" ? "OPERATIONAL" : "DEGRADED";
  return <main className="landing">
    <div className="stars"/>
    <div className="planet moon"/>
    <div className="planet mars"/>
    <nav className="landing-nav">
      <Logo/>
      <div className="nav-actions">
        <span className="nasa-source">NASA OPEN DATA <b>LRO · MRO</b></span>
        <span className="status"><i/> API <b>{apiLabel}</b></span>
        <button className="btn primary" onClick={onLaunch} disabled={!target}>Launch engine <Icon name="arrow"/></button>
      </div>
    </nav>
    <div className="mission-ribbon">
      <span>ASTROTERRAIN / MISSION ANALOG SYSTEM</span>
      <span>{health?.database === "connected" ? "DATABASE CONNECTED" : "DATABASE CHECK"}</span>
      <span>{String(targets.length).padStart(2, "0")} TARGETS</span>
      <span>{target ? target.data_source.replaceAll("_", " ").toUpperCase() : "AWAITING TARGETS"}</span>
    </div>
    <section className="launch-stage">
      <div className="launch-copy">
        <div className="eyebrow"><span>PLANETARY ANALOG EXPLORER / 2025</span><i/></div>
        <h1>Earth is our<br/><em>testing ground.</em></h1>
        <p>Find the places on Earth that behave like another world. Compare terrain, climate, and chemistry using the analog search API.</p>
        <button className="launch-cta" onClick={onLaunch} disabled={!target}><span>Begin mission</span><i><Icon name="arrow" size={21}/></i></button>
        {error && <p className="api-note">Backend is offline, so analog scores are unavailable. The globes still open.</p>}
      </div>
      <div className={`orbital-display ${planet === "mars" ? "mars" : ""}`}>
        <div className="orbit-ring ring-one"/><div className="orbit-ring ring-two"/><div className="orbit-ring ring-three"/>
        <div className="crosshair horizontal"/><div className="crosshair vertical"/>
        <PlanetView body={planet === "mars" ? "mars" : "moon"} />
        <div className="planet-scan"/>
        <span className="orbit-label label-a">{planet === "mars" ? "MARS" : "MOON"}</span>
        <span className="orbit-label label-b">{target ? `${formatNumber(target.elevation_m, " M")}` : "NO TARGET"}</span>
        <div className="target-readout">
          <span>ACTIVE TARGET / {planet === "mars" ? "MARTIAN" : "LUNAR"}</span>
          <strong>{target ? target.site_name.replace(/ \(synthetic demo profile\)/i, "") : "Loading"}</strong>
          <small>{target ? formatCoord(target.coordinates.lat, target.coordinates.lng) : "—"}</small>
        </div>
      </div>
      <div className="mission-selector">
        <span className="selector-caption">CHOOSE DESTINATION</span>
        {targets.length === 0 && <p className="selector-empty">{error ? "Targets unavailable" : "Loading targets"}</p>}
        {targets.map((item, index) => (
          <button
            key={`${item.planet}-${item.site_id}`}
            className={target?.site_id === item.site_id && target.planet === item.planet ? `active${item.planet === "mars" ? " mars-choice" : ""}` : ""}
            onClick={() => onSelect(item)}
          >
            <i>{String(index + 1).padStart(2, "0")}</i>
            <span><small>{item.planet === "mars" ? "MARS" : "MOON"} / {item.site_id.replaceAll("-", " ").toUpperCase()}</small><b>{item.site_name.replace(/ \(synthetic demo profile\)/i, "")}</b></span>
            <em>{formatCoord(item.coordinates.lat, item.coordinates.lng).split(" · ")[0]}</em>
          </button>
        ))}
      </div>
    </section>
  </main>;
}

function Report({ target, analog, onClose }: { target: Target; analog: Analog; onClose: () => void }) {
  const brief = {
    target: { planet: target.planet, site_id: target.site_id, site_name: target.site_name, coordinates: target.coordinates },
    analog,
  };
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="report glass" onMouseDown={(event) => event.stopPropagation()}>
    <div className="report-head"><div><span className="eyebrow-mini">COMPARATIVE REPORT / {analog.site_id.toUpperCase()}</span><h2>Mission Analog Brief</h2></div><button className="close" onClick={onClose}>×</button></div>
    <div className="compare">
      <div className="compare-tile earth-tile"><span>EARTH ANALOG</span><strong>{analog.name}</strong><small>{formatCoord(analog.coordinates.lat, analog.coordinates.lng)}</small></div>
      <div className="compare-divider"><span>{Math.round(analog.similarity_score)}%</span><small>SIMILARITY</small></div>
      <div className="compare-tile lunar-tile"><span>{target.planet === "mars" ? "MARS TARGET" : "LUNAR TARGET"}</span><strong>{target.site_name.replace(/ \(synthetic demo profile\)/i, "")}</strong><small>{formatCoord(target.coordinates.lat, target.coordinates.lng)}</small></div>
    </div>
    <div className="ai-summary">
      <div className="ai-title"><Icon name="orbit"/><span><small>ANALOG SEARCH</small><b>Score breakdown from the API</b></span><em>{target.data_source.replaceAll("_", " ").toUpperCase()}</em></div>
      <p>{analog.name} in {analog.country} scores {analog.similarity_score} against {target.site_name}. Topography {analog.breakdown.topography_match}, geochemistry {analog.breakdown.geochemistry_match}, climate {analog.breakdown.climate_match}. These figures come from the current scoring baseline.</p>
      <div className="summary-grid">
        <div><span>ELEVATION</span><b>{formatNumber(analog.metadata.elevation_m, " m")}</b><small>metadata.elevation_m</small></div>
        <div><span>ROCK</span><b>{analog.metadata.primary_rock ?? "Unknown"}</b><small>metadata.primary_rock</small></div>
        <div><span>ACCESS</span><b>{analog.metadata.accessibility_rating}</b><small>metadata.accessibility_rating</small></div>
      </div>
    </div>
    <div className="export-bar">
      <div><span>REPORT READY</span><small>{analog.country} · {analog.site_id}</small></div>
      <button className="btn secondary" onClick={() => download(`${analog.site_id}.geojson`, JSON.stringify({ type: "Feature", geometry: { type: "Point", coordinates: [analog.coordinates.lng, analog.coordinates.lat] }, properties: { site_id: analog.site_id, name: analog.name, similarity_score: analog.similarity_score } }, null, 2), "application/geo+json")}><Icon name="download"/> Download GeoJSON</button>
      <button className="btn primary" onClick={() => download(`${analog.site_id}-brief.json`, JSON.stringify(brief, null, 2), "application/json")}><Icon name="download"/> Export JSON brief</button>
    </div>
  </div></div>;
}

function Dashboard({ target, targets, onHome, onTargetChange }: { target: Target; targets: Target[]; onHome: () => void; onTargetChange: (target: Target) => void }) {
  const [layer, setLayer] = useState<Layer>("similarity");
  const [analogs, setAnalogs] = useState<Analog[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState(false);
  const earthRef = useRef<{ zoomBy: (factor: number) => void; reset: () => void } | null>(null);
  const selected = analogs.find((site) => site.site_id === selectedId) ?? null;
  const markers = useMemo(() => analogs.map((site) => ({
    id: site.site_id,
    name: site.name.toUpperCase(),
    lat: site.coordinates.lat,
    lng: site.coordinates.lng,
    badge: pinLabel(site, layer),
  })), [analogs, layer]);
  const high = analogs.filter((site) => site.similarity_score >= 75).length;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelectedId(null);
    searchAnalogs({ target_planet: target.planet, target_site_id: target.site_id, ...SEARCH_BODY })
      .then((result) => { if (!cancelled) setAnalogs(result.analogs ?? []); })
      .catch((reason) => { if (!cancelled) { setAnalogs([]); setError(errorText(reason)); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [target.planet, target.site_id]);

  return <main className="dashboard">
    <header className="dash-nav">
      <button className="plain" onClick={onHome}><Logo/></button>
      <label className="target-switch">
        <span className={`tiny-orb${target.planet === "mars" ? " mars" : ""}`}/>
        <span>
          <small>ACTIVE TARGET</small>
          <select
            aria-label="Active target"
            value={`${target.planet}|${target.site_id}`}
            onChange={(event) => {
              const next = targets.find((item) => `${item.planet}|${item.site_id}` === event.target.value);
              if (next) onTargetChange(next);
            }}
          >
            {targets.map((item) => <option key={`${item.planet}|${item.site_id}`} value={`${item.planet}|${item.site_id}`}>{item.site_name}</option>)}
          </select>
        </span>
        <Icon name="chevron"/>
      </label>
      <div className="dash-meta">
        <span className="mission-id">{target.planet.toUpperCase()} / {target.site_id}</span>
        <span className="status"><i/> {loading ? "SEARCHING" : error ? "SEARCH FAILED" : "LIVE DATA"}</span>
        <span className="mono">{formatCoord(target.coordinates.lat, target.coordinates.lng)}</span>
        <button className="btn secondary" onClick={() => selected && setReport(true)} disabled={!selected}><Icon name="download"/> Export</button>
      </div>
    </header>
    <section className="earth-workspace">
      <div className="space-dust"/>
      <div className="globe-heading">
        <span>EARTH ANALOG NETWORK</span>
        <b>Explore candidate terrain</b>
        <small>{loading ? "Searching analogs…" : error ? error : "Select a signal to descend to site level"}</small>
      </div>
      <div className="globe-wrap is-live">
        <div className="globe-orbit orbit-a"/><div className="globe-orbit orbit-b"/>
        <EarthView ref={earthRef} markers={markers} selectedId={selectedId} onSelect={setSelectedId} />
      </div>
      <div className="globe-tools">
        <button aria-label="Zoom in" onClick={() => earthRef.current?.zoomBy(0.82)}><Icon name="plus"/></button>
        <button aria-label="Zoom out" onClick={() => earthRef.current?.zoomBy(1.22)}><Icon name="minus"/></button>
        <i/>
        <button aria-label="Reset view" onClick={() => earthRef.current?.reset()}><Icon name="scan"/></button>
        <button aria-label="Map layers" onClick={() => setLayer((current) => current === "similarity" ? "topography" : current === "topography" ? "mineralogy" : current === "mineralogy" ? "climate" : "similarity")}><Icon name="layers"/></button>
      </div>
      <div className="layer-rail" role="radiogroup" aria-label="Data layers">
        <span>DATA LAYERS</span>
        {(["similarity", "topography", "mineralogy", "climate"] as Layer[]).map((item) => (
          <button key={item} className={layer === item ? "active" : ""} role="radio" aria-checked={layer === item} onClick={() => setLayer(item)}><i/> {item[0].toUpperCase() + item.slice(1)}</button>
        ))}
      </div>
      {!loading && !error && analogs.length === 0 && <p className="globe-empty">No analogs matched this target.</p>}
      <div className="globe-compass"><span>N</span><i/><b>3D</b></div>
      <div className="globe-readout mono"><span>DRAG TO ORBIT</span><span>LAYER {layer.toUpperCase()}</span><span>{analogs.length} RESULTS</span></div>
      <div className="candidate-strip">
        <span><b>{String(analogs.length).padStart(2, "0")}</b> ANALOG SITES</span>
        <span><b>{String(high).padStart(2, "0")}</b> HIGH CONFIDENCE</span>
        <span><b>03</b> SCORE FIELDS</span>
        <span className="live-pulse">{error ? "SEARCH ERROR" : "ORBITAL FEED LIVE"}</span>
      </div>
      {selected && <aside className="location-sheet">
        <button className="sheet-close" onClick={() => setSelectedId(null)}>×</button>
        <div className="sheet-kicker"><span>SELECTED ANALOG</span><em>{Math.round(selected.similarity_score)}% MATCH</em></div>
        <h2>{selected.name}</h2>
        <p>{selected.country}</p>
        <div className="sheet-coords mono">{formatCoord(selected.coordinates.lat, selected.coordinates.lng)}</div>
        <div className="sheet-metrics">
          <div><small>ELEVATION</small><b>{formatNumber(selected.metadata.elevation_m, " m")}</b></div>
          <div><small>ROCK</small><b>{selected.metadata.primary_rock ?? "Unknown"}</b></div>
          <div><small>ACCESS</small><b>{selected.metadata.accessibility_rating}</b></div>
        </div>
        <div className="score-breakdown">
          <span>Topography {Math.round(selected.breakdown.topography_match)}%</span>
          <span>Geochemistry {Math.round(selected.breakdown.geochemistry_match)}%</span>
          <span>Climate {Math.round(selected.breakdown.climate_match)}%</span>
        </div>
        <div className="match-bar"><span>Terrain similarity</span><b>{Math.round(selected.similarity_score)}%</b><i style={{ "--match": `${selected.similarity_score}%` } as React.CSSProperties}/></div>
        <button className="descend" onClick={() => setReport(true)}>Descend to site <Icon name="arrow"/></button>
      </aside>}
    </section>
    {report && selected && <Report target={target} analog={selected} onClose={() => setReport(false)}/>}
  </main>;
}

export default function App() {
  const [view, setView] = useState<"landing" | "warp" | "dashboard">("landing");
  const [targets, setTargets] = useState<Target[]>(FALLBACK_TARGETS);
  const [target, setTarget] = useState<Target | null>(FALLBACK_TARGETS[0]);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHealth().then((result) => { if (!cancelled) setHealth(result); }).catch(() => { if (!cancelled) setHealth({ status: "degraded", database: "unavailable" }); });
    getTargets()
      .then((result) => {
        if (cancelled) return;
        const list = result.targets ?? [];
        setTargets(list);
        setTarget((current) => current ?? list.find((item) => item.planet === "moon") ?? list[0] ?? null);
      })
      .catch(() => { if (!cancelled) setError("offline"); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (view !== "warp") return undefined;
    const id = window.setTimeout(() => setView("dashboard"), 1450);
    return () => window.clearTimeout(id);
  }, [view]);

  function launch() {
    if (target) setView("warp");
  }

  return <div className="figma-app">
    {view === "warp" && <div className="warp"><Logo/><div className="warp-lines"/><span>INITIALIZING TERRAIN ENGINE</span><small>CALIBRATING ORBITAL DATA</small></div>}
    {view === "landing" && <Landing targets={targets} target={target} health={health} error={error} onSelect={setTarget} onLaunch={launch}/>}
    {view === "dashboard" && target && <Dashboard target={target} targets={targets} onHome={() => setView("landing")} onTargetChange={setTarget}/>}
  </div>;
}
