# AstroTerrain 3D Globe Module

**Owner:** Pranjil  
**Backend Integration:** Module 3 — Anshika  
**Reference Contract:** `GLOBE_PRANJIL.md`

---

## 1. Module Overview: Systematic Side-by-Side Dual-Globe Architecture

This module implements a side-by-side 3D planetary reconnaissance and Earth analog matching system:

1. **Left Viewport — Celestial Body (Moon or Mars):**
   - Seamless toggle between **Moon** and **Mars**.
   - Photorealistic planetary surfaces:
     - Lunar high-resolution regolith texture with vacuum lighting.
     - Martian regolith texture with thin carbon dioxide atmospheric rim glow.
   - Crater hotspots (e.g. Jezero Crater, Gale Crater, Olympus Mons, Valles Marineris; Shackleton Crater, Tycho, SPA Basin, Oceanus Procellarum).
   - Hotspot beacons & CSS2D pins stay physically anchored to spherical coordinates and orbit tightly with the globe.

2. **Center Correlation Bridge:**
   - Real-time scanning telemetry beam and status indicator linking the planetary crater to Earth.
   - Visual correlation matrix ticker while querying Anshika's backend API (`POST /api/v1/analogs/search`).

3. **Right Viewport — Earth Terrestrial Analogs:**
   - High-resolution Earth globe with atmospheric Rayleigh scattering shader and independently rotating cloud layer.
   - Plots matching Earth analog markers dynamically at exact `[lat, lng]` coordinates (e.g., Atacama Desert, McMurdo Dry Valleys, Mauna Kea Volcanic Ridge, Svalbard, Río Tinto, Barringer Meteor Crater).
   - Interactive CSS2D pins displaying similarity score badges (e.g., `95% Atacama Desert`).
   - Smooth camera fly-to focusing on the top matching analog.
   - Quick candidate chips (#1, #2, #3...) to navigate between analog sites.

4. **Bottom Comparative Telemetry Deck:**
   - Multi-metric comparative HUD:
     - **Planetary Crater Specs:** Elevation, average slope, mineralogy/rock type, temperature range, and mission data source.
     - **Correlation & Breakdown:** Overall composite similarity score, Topography Match %, Geochemistry Match %, Climate Match %, and scientific rationale.
     - **Earth Analog Specs & Data Handoff:** Elevation, primary rock, accessibility rating, and geographic coordinates.
     - **GeoJSON Export Button:** Downloads GeoJSON adhering strictly to standard `[lng, lat]` coordinate order per section 3 of `GLOBE_PRANJIL.md`.

5. **Camera & Orbital Behavior:**
   - Both globes start **zoomed out** (`distance: ~3.45`) on refresh/load and planet toggle (no unwanted auto-zooming).
   - Both globes rotate gently (`autoRotateSpeed: 0.45`).
   - Auto-rotation pauses on user drag/inspection and automatically resumes after 2 seconds of inactivity.

---

## 2. Backend Integration Contract Compliance

All 8 Definition-of-Done items from `GLOBE_PRANJIL.md` are fulfilled:

| Item | Requirement | Implementation |
|---|---|---|
| 1 | Fetch Moon/Mars targets from API | Consumes `GET /api/v1/targets?planet={moon\|mars}` |
| 2 | Selecting target triggers analog search | Dispatches `POST /api/v1/analogs/search` |
| 3 | Use returned coordinates | Dynamic point positions from API response |
| 4 | GeoJSON uses `[lng, lat]` order | `[coordinates.lng, coordinates.lat]` strictly enforced |
| 5 | Marker selection displays metadata & score | Interactive location sheet & comparative report |
| 6 | Loading, empty results & errors handled | Non-blocking states & offline fallback mode |
| 7 | No terrain tile/mesh assumptions | Client-side point geometries on standard sphere maps |
| 8 | Documented data contract | Fully aligned with backend routes |

---

## 3. How to Run & Share

### A. Run Locally
```bash
cd frontend
npm install
npm run dev
```
The application opens on `http://localhost:3000` (matching backend `CORS_ORIGINS`).

### B. Share with Teammates (Instant Public Link)
To share your screen/app live with your teammates or partner without requiring them to set up anything:
```bash
# Option 1: Localtunnel (Free instant public HTTPS URL)
npx localtunnel --port 3000

# Option 2: Cloudflare Tunnel (Zero-config)
npx cloudflared tunnel --url http://localhost:3000
```
The application includes calibrated fallback data for both Moon/Mars craters and Earth analogs, so anyone can explore the dual globes even if the backend is offline!
