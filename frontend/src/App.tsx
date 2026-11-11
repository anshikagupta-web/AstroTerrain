import { useEffect, useState } from "react";
import "./index.css";

type IconName = "orbit" | "arrow" | "layers" | "download" | "target" | "cube" | "scan" | "plus" | "minus" | "chevron";

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

const moonImage = "https://images.unsplash.com/photo-1711559652900-51614fe511ef?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixlib=rb-4.1.0&q=85&w=1400";

function Logo() {
  return <div className="logo"><span className="logo-mark"><Icon name="orbit" size={22}/></span><span>ASTRO<span>TERRAIN</span></span></div>;
}

function Landing({ onLaunch }: { onLaunch: () => void }) {
  const [target, setTarget] = useState<"lunar" | "mars">("lunar");
  return <main className="landing">
    <div className="stars"/>
    <div className="planet moon"/>
    <div className="planet mars"/>
    <nav className="landing-nav">
      <Logo/>
      <div className="nav-actions"><span className="nasa-source">NASA OPEN DATA <b>LRO · MRO</b></span><span className="status"><i/> API <b>OPERATIONAL</b></span><button className="btn primary" onClick={onLaunch}>Launch engine <Icon name="arrow"/></button></div>
    </nav>
    <div className="mission-ribbon"><span>ASTROTERRAIN / MISSION ANALOG SYSTEM</span><span>LIVE ORBITAL DATA</span><span>02 TARGETS</span><span>12 EARTH ANALOGS</span><span>CALIBRATION 99.8%</span></div>
    <section className="launch-stage">
      <div className="launch-copy">
        <div className="eyebrow"><span>PLANETARY ANALOG EXPLORER / 2025</span><i/></div>
        <h1>Earth is our<br/><em>testing ground.</em></h1>
        <p>Find the places on Earth that behave like another world. Compare terrain, climate, and chemistry using live NASA orbital data.</p>
        <button className="launch-cta" onClick={onLaunch}><span>Begin mission</span><i><Icon name="arrow" size={21}/></i></button>
      </div>
      <div className={`orbital-display ${target}`}>
        <div className="orbit-ring ring-one"/><div className="orbit-ring ring-two"/><div className="orbit-ring ring-three"/>
        <div className="crosshair horizontal"/><div className="crosshair vertical"/>
        <div className="display-planet"/>
        <div className="planet-scan"/>
        <span className="orbit-label label-a">ORBIT 89.7°</span><span className="orbit-label label-b">ALT 50 KM</span>
        <div className="target-readout"><span>ACTIVE TARGET / {target === "lunar" ? "LUNAR" : "MARTIAN"}</span><strong>{target === "lunar" ? "Shackleton" : "Jezero"}</strong><small>{target === "lunar" ? "89.90°S · 0.00°E" : "18.38°N · 77.58°E"}</small></div>
      </div>
      <div className="mission-selector">
        <span className="selector-caption">CHOOSE DESTINATION</span>
        <button className={target === "lunar" ? "active" : ""} onClick={() => setTarget("lunar")}><i>01</i><span><small>MOON / SOUTH POLE</small><b>Shackleton Crater</b></span><em>89.90°S</em></button>
        <button className={target === "mars" ? "active mars-choice" : ""} onClick={() => setTarget("mars")}><i>02</i><span><small>MARS / JEZERO</small><b>Jezero Crater</b></span><em>18.38°N</em></button>
      </div>
      <div className="launch-stats"><span><b>42</b> ORBITAL DATASETS</span><span><b>5M</b> SURFACE RESOLUTION</span><span><b>12</b> ANALOG SITES READY</span></div>
    </section>
    <footer><span>NASA SPACE APPS / 2025</span><span className="mono">SYS.TIME 14:32:08 UTC</span><span>SCROLL TO EXPLORE ↓</span></footer>
  </main>;
}

function Range({ label, value, color = "cyan" }: { label: string; value: number; color?: string }) {
  return <div className="range-field"><div><span>{label}</span><b>{value}%</b></div><input aria-label={label} type="range" defaultValue={value} style={{ "--value": `${value}%`, "--range": color === "cyan" ? "#A0BEFF" : "#F2E8C9" } as React.CSSProperties}/></div>;
}

function Radar() {
  return <svg className="radar" viewBox="0 0 220 170" aria-label="Parameters comparison radar chart">
    <g className="radar-grid"><path d="M110 14 192 62 169 146H51L28 62Z"/><path d="M110 39 167 72 151 130H69L53 72Z"/><path d="M110 64 143 82 133 113H87L77 82Z"/><path d="M110 14v132M28 62l141 84M192 62 51 146M28 62h164M110 14l59 132"/></g>
    <path className="radar-earth" d="M110 28 177 69 158 130 60 137 45 67Z"/>
    <path className="radar-target" d="M110 48 155 77 139 118 73 126 60 73Z"/>
    <g className="radar-labels"><text x="110" y="9">TOPOGRAPHY</text><text x="198" y="63">SLOPE</text><text x="167" y="162">CLIMATE</text><text x="21" y="162">ACCESS</text><text x="0" y="63">MINERAL</text></g>
  </svg>;
}

function Dashboard({ onHome }: { onHome: () => void }) {
  const [report, setReport] = useState(false);
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const sites = {
    atacama: { name: "Atacama Desert", place: "Antofagasta, Chile", score: 94, coords: "24.50° S · 69.25° W", temp: "−12°C", slope: "18.4°" },
    mauna: { name: "Mauna Loa", place: "Hawaiʻi, USA", score: 89, coords: "19.47° N · 155.60° W", temp: "−4°C", slope: "22.1°" },
    iceland: { name: "Askja Caldera", place: "Highlands, Iceland", score: 86, coords: "65.03° N · 16.75° W", temp: "−8°C", slope: "16.8°" },
  };
  const active = selectedSite ? sites[selectedSite as keyof typeof sites] : null;
  return <main className="dashboard">
    <header className="dash-nav"><button className="plain" onClick={onHome}><Logo/></button><div className="target-switch"><span className="tiny-orb"/><span><small>ACTIVE TARGET</small><b>Shackleton Crater, Moon</b></span><Icon name="chevron"/></div><div className="dash-meta"><span className="mission-id">MISSION AT–01</span><span className="status"><i/> LIVE DATA</span><span className="mono">89.90°S&nbsp;&nbsp;0.00°E</span><button className="btn secondary" onClick={() => setReport(true)}><Icon name="download"/> Export</button></div></header>
    <section className="earth-workspace">
      <div className="space-dust"/>
      <div className="globe-heading"><span>EARTH ANALOG NETWORK</span><b>Explore candidate terrain</b><small>Select a signal to descend to site level</small></div>
      <div className="globe-wrap">
        <div className="globe-orbit orbit-a"/><div className="globe-orbit orbit-b"/>
        <div className="earth-globe"><div className="earth-texture"/><div className="earth-atmosphere"/></div>
        <button className="globe-pin atacama" onClick={() => setSelectedSite("atacama")}><i/><span>ATACAMA <b>94%</b></span></button>
        <button className="globe-pin mauna" onClick={() => setSelectedSite("mauna")}><i/><span>MAUNA LOA <b>89%</b></span></button>
        <button className="globe-pin iceland" onClick={() => setSelectedSite("iceland")}><i/><span>ASKJA <b>86%</b></span></button>
      </div>
      <div className="globe-tools">
        <button aria-label="Zoom in"><Icon name="plus"/></button><button aria-label="Zoom out"><Icon name="minus"/></button><i/><button aria-label="Reset view"><Icon name="scan"/></button><button aria-label="Map layers"><Icon name="layers"/></button>
      </div>
      <div className="layer-rail"><span>DATA LAYERS</span><button className="active"><i/> Similarity</button><button><i/> Topography</button><button><i/> Mineralogy</button><button><i/> Climate</button></div>
      <div className="globe-compass"><span>N</span><i/><b>3D</b></div>
      <div className="globe-readout mono"><span>ALT 12,742 KM</span><span>CAM 18.4°</span><span>RES 5.0 M/PX</span></div>
      <div className="candidate-strip"><span><b>12</b> ANALOG SITES</span><span><b>03</b> HIGH CONFIDENCE</span><span><b>42</b> DATA LAYERS</span><span className="live-pulse">ORBITAL FEED LIVE</span></div>
      {active && <aside className="location-sheet">
        <button className="sheet-close" onClick={() => setSelectedSite(null)}>×</button>
        <div className="sheet-kicker"><span>SELECTED ANALOG</span><em>{active.score}% MATCH</em></div>
        <h2>{active.name}</h2><p>{active.place}</p>
        <div className="sheet-coords mono">{active.coords}</div>
        <div className="flyover"><div className="flyover-terrain"/><span><Icon name="scan"/> LIVE TERRAIN PREVIEW</span></div>
        <div className="sheet-metrics"><div><small>SURFACE TEMP.</small><b>{active.temp}</b></div><div><small>MEAN SLOPE</small><b>{active.slope}</b></div><div><small>ACCESS</small><b>GOOD</b></div></div>
        <div className="match-bar"><span>Terrain similarity</span><b>{active.score}%</b><i style={{ "--match": `${active.score}%` } as React.CSSProperties}/></div>
        <button className="descend" onClick={() => setReport(true)}>Descend to site <Icon name="arrow"/></button>
      </aside>}
    </section>
    {report && <Report onClose={() => setReport(false)}/>}
  </main>;
}

function Report({ onClose }: { onClose: () => void }) {
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="report glass" onMouseDown={e => e.stopPropagation()}>
    <div className="report-head"><div><span className="eyebrow-mini">COMPARATIVE REPORT / AT-0084</span><h2>Mission Analog Brief</h2></div><button className="close" onClick={onClose}>×</button></div>
    <div className="compare">
      <div className="compare-tile earth-tile"><span>EARTH ANALOG</span><strong>Atacama Desert</strong><small>24.50°S · 69.25°W</small></div>
      <div className="compare-divider"><span>94%</span><small>SIMILARITY</small></div>
      <div className="compare-tile lunar-tile"><span>LUNAR TARGET</span><strong>Shackleton Crater</strong><small>89.90°S · 0.00°E</small></div>
    </div>
    <div className="ai-summary"><div className="ai-title"><Icon name="orbit"/><span><small>ASTROTERRAIN INTELLIGENCE</small><b>Mission suitability assessment</b></span><em>GENERATED 14:32 UTC</em></div><p>The Atacama’s hyper-arid, high-UV terrain offers an exceptional operational analog for south-polar lunar missions. Surface mineralogy and regolith mechanics support high-fidelity rover mobility and suit abrasion testing.</p><div className="summary-grid"><div><span>LOGISTICS</span><b>High accessibility</b><small>Road access within 8 km</small></div><div><span>PRIMARY HAZARD</span><b>Extreme UV exposure</b><small>UV index 11+</small></div><div><span>SUIT TESTING</span><b>Excellent</b><small>Fine particulate environment</small></div></div></div>
    <div className="export-bar"><div><span>REPORT READY</span><small>All datasets validated · 18.4 MB</small></div><button className="btn secondary"><Icon name="download"/> Download GeoJSON</button><button className="btn primary"><Icon name="download"/> Export PDF Brief</button></div>
  </div></div>;
}

export default function App() {
  const [view, setView] = useState<"landing" | "warp" | "dashboard">("landing");
  const launch = () => setView("warp");
  useEffect(() => { if (view === "warp") { const id = setTimeout(() => setView("dashboard"), 1450); return () => clearTimeout(id); }}, [view]);
  return <div className="figma-app">
    {view === "warp"
      ? <div className="warp"><Logo/><div className="warp-lines"/><span>INITIALIZING TERRAIN ENGINE</span><small>CALIBRATING ORBITAL DATA</small></div>
      : view === "landing" ? <Landing onLaunch={launch}/> : <Dashboard onHome={() => setView("landing")}/>}
  </div>;
}
