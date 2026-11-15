import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";

const MOON_MAP = "https://threejs.org/examples/textures/planets/moon_1024.jpg";
const MARS_MAP = "https://raw.githubusercontent.com/jeromeetienne/threex.planets/master/images/marsmap1k.jpg";
const EARTH_MAP = "https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg";
const EARTH_CLOUDS = "https://threejs.org/examples/textures/planets/earth_clouds_1024.png";

/**
 * Convert Latitude and Longitude to 3D Cartesian coordinates on a sphere.
 */
function latLngToVector(lat, lng, radius) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lng + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

/**
 * Mars atmospheric rim glow shader
 */
function marsAtmosphere(radius = 1.09) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(radius, 64, 64),
    new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float fresnel = pow(0.60 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
          gl_FragColor = vec4(0.92, 0.40, 0.18, 1.0) * fresnel;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
    })
  );
}

/**
 * Earth atmospheric rim glow shader (Deep blue/cyan ozone scattering)
 */
function earthAtmosphere(radius = 1.12) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(radius, 64, 64),
    new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float fresnel = pow(0.62 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.2);
          gl_FragColor = vec4(0.24, 0.65, 1.0, 1.0) * fresnel;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
    })
  );
}

/**
 * Lightweight PlanetView component for the Landing page's circular orbital preview
 */
export const PlanetView = forwardRef(function PlanetView({ body = "moon" }, ref) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0, 3.1);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);
    const sunLight = new THREE.DirectionalLight(0xffffff, 2.5);
    sunLight.position.set(5, 3, 5);
    scene.add(sunLight);

    const isMars = body === "mars";
    const material = new THREE.MeshPhongMaterial({
      color: isMars ? 0xc47a52 : 0xb7bcc4,
      shininess: 4,
    });
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 48), material);
    scene.add(mesh);

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(isMars ? MARS_MAP : MOON_MAP, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      material.map = tex;
      material.color.set(0xffffff);
      material.needsUpdate = true;
    });

    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      mesh.rotation.y += 0.003;
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!mount) return;
      camera.aspect = (mount.clientWidth || 1) / (mount.clientHeight || 1);
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      renderer.domElement.remove();
      mesh.geometry.dispose();
      material.map?.dispose();
      material.dispose();
    };
  }, [body]);

  return <div ref={mountRef} className="planet-view" />;
});

/**
 * Cinematic Rotating Triangle Scene: Earth, Mars, and Moon in orbital trinity constellation
 */
export const CelestialTrinity = forwardRef(function CelestialTrinity(
  { onSelectPlanet, onHoverPlanet },
  ref
) {
  const mountRef = useRef(null);
  const onSelectRef = useRef(onSelectPlanet);
  onSelectRef.current = onSelectPlanet;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    camera.position.set(0, 3.2, 7.8);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const labels = new CSS2DRenderer();
    labels.domElement.style.position = "absolute";
    labels.domElement.style.inset = "0";
    labels.domElement.style.pointerEvents = "none";
    mount.appendChild(labels.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.minDistance = 4.5;
    controls.maxDistance = 14.0;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;

    // Deep space lighting
    const ambientLight = new THREE.AmbientLight(0xddeeff, 0.4);
    scene.add(ambientLight);
    const sunLight = new THREE.DirectionalLight(0xfff8ee, 3.2);
    sunLight.position.set(6, 5, 8);
    scene.add(sunLight);
    const fillLight = new THREE.DirectionalLight(0x334466, 0.5);
    fillLight.position.set(-6, -3, -6);
    scene.add(fillLight);

    // Stars particle field
    const starsCount = 600;
    const starsGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starsCount * 3);
    for (let i = 0; i < starsCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 50;
      starPositions[i + 1] = (Math.random() - 0.5) * 50;
      starPositions[i + 2] = (Math.random() - 0.5) * 50;
    }
    starsGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    const starsMat = new THREE.PointsMaterial({ color: 0xa0beff, size: 0.08, transparent: true, opacity: 0.6 });
    const starField = new THREE.Points(starsGeo, starsMat);
    scene.add(starField);

    // Constellation Group
    const constellationGroup = new THREE.Group();
    scene.add(constellationGroup);

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");

    // Triangle Geometry Parameters
    const R = 2.65; // Radius of equilateral triangle

    // 1. Earth (Radius 0.70)
    const earthPos = new THREE.Vector3(R * Math.cos(0), 0, R * Math.sin(0));
    const earthGroup = new THREE.Group();
    earthGroup.position.copy(earthPos);

    const earthMat = new THREE.MeshPhongMaterial({ shininess: 12, specular: new THREE.Color(0x223344) });
    const earthMesh = new THREE.Mesh(new THREE.SphereGeometry(0.7, 64, 64), earthMat);
    earthMesh.userData = { planet: "earth", name: "Earth" };
    earthGroup.add(earthMesh);

    const cloudsMat = new THREE.MeshPhongMaterial({ transparent: true, opacity: 0.82, blending: THREE.AdditiveBlending });
    const cloudsMesh = new THREE.Mesh(new THREE.SphereGeometry(0.71, 48, 48), cloudsMat);
    earthGroup.add(cloudsMesh);

    const earthAtmos = earthAtmosphere(0.77);
    earthGroup.add(earthAtmos);

    loader.load(EARTH_MAP, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      earthMat.map = tex;
      earthMat.needsUpdate = true;
    });
    loader.load(EARTH_CLOUDS, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      cloudsMat.map = tex;
      cloudsMat.needsUpdate = true;
    });

    // 2. Mars (Radius 0.52)
    const angleMars = (2 * Math.PI) / 3;
    const marsPos = new THREE.Vector3(R * Math.cos(angleMars), 0, R * Math.sin(angleMars));
    const marsGroup = new THREE.Group();
    marsGroup.position.copy(marsPos);

    const marsMat = new THREE.MeshPhongMaterial({ shininess: 6, specular: new THREE.Color(0x4a2212) });
    const marsMesh = new THREE.Mesh(new THREE.SphereGeometry(0.52, 64, 64), marsMat);
    marsMesh.userData = { planet: "mars", name: "Mars" };
    marsGroup.add(marsMesh);

    const marsAtmos = marsAtmosphere(0.57);
    marsGroup.add(marsAtmos);

    loader.load(MARS_MAP, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      marsMat.map = tex;
      marsMat.needsUpdate = true;
    });

    // 3. Moon (Radius 0.40)
    const angleMoon = (4 * Math.PI) / 3;
    const moonPos = new THREE.Vector3(R * Math.cos(angleMoon), 0, R * Math.sin(angleMoon));
    const moonGroup = new THREE.Group();
    moonGroup.position.copy(moonPos);

    const moonMat = new THREE.MeshPhongMaterial({ shininess: 3, specular: new THREE.Color(0x22262b) });
    const moonMesh = new THREE.Mesh(new THREE.SphereGeometry(0.4, 64, 64), moonMat);
    moonMesh.userData = { planet: "moon", name: "Moon" };
    moonGroup.add(moonMesh);

    loader.load(MOON_MAP, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      moonMat.map = tex;
      moonMat.needsUpdate = true;
    });

    const clickableMeshes = [earthMesh, marsMesh, moonMesh];
    const planetGroups = [earthGroup, marsGroup, moonGroup];
    planetGroups.forEach((g) => constellationGroup.add(g));

    // Connective Constellation Line Loop (Triangle linking Earth ⟷ Mars ⟷ Moon)
    const lineGeo = new THREE.BufferGeometry().setFromPoints([earthPos, marsPos, moonPos, earthPos]);
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x55c7e8,
      transparent: true,
      opacity: 0.35,
    });
    const constellationLine = new THREE.Line(lineGeo, lineMat);
    constellationGroup.add(constellationLine);

    // CSS2D Interactive Floating Badges
    const createBadge = (text, planetKey, group, yOffset) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `trinity-planet-pill ${planetKey}-pill`;
      btn.innerHTML = `<i></i><span>${text}</span>`;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onSelectRef.current?.(planetKey === "earth" ? "mars" : planetKey);
      });
      const obj = new CSS2DObject(btn);
      obj.position.set(0, yOffset, 0);
      group.add(obj);
    };

    createBadge("🌍 EARTH · TERRESTRIAL BASELINE", "earth", earthGroup, 1.05);
    createBadge("🔴 MARS · EXPLORE CRATERS", "mars", marsGroup, 0.85);
    createBadge("🌙 MOON · EXPLORE CRATERS", "moon", moonGroup, 0.72);

    // Raycaster for clicking planets in 3D
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let downPos = null;

    const onDown = (e) => {
      downPos = { x: e.clientX, y: e.clientY };
    };

    const onUp = (e) => {
      if (!downPos) return;
      const dx = e.clientX - downPos.x;
      const dy = e.clientY - downPos.y;
      downPos = null;
      if (dx * dx + dy * dy > 16) return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      const hits = raycaster.intersectObjects(clickableMeshes, false);
      if (hits.length > 0) {
        const clickedPlanet = hits[0].object.userData.planet;
        if (clickedPlanet) {
          onSelectRef.current?.(clickedPlanet === "earth" ? "mars" : clickedPlanet);
        }
      }
    };

    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    // Resize observer
    const resize = () => {
      const width = mount.clientWidth || 1;
      const height = mount.clientHeight || 1;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      labels.setSize(width, height);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    // Render loop: triangle constellation slowly orbits in space
    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);

      // Slow constellation orbital rotation
      constellationGroup.rotation.y += 0.0025;

      // Axial rotations
      earthMesh.rotation.y += 0.005;
      cloudsMesh.rotation.y += 0.007;
      marsMesh.rotation.y += 0.004;
      moonMesh.rotation.y += 0.003;

      controls.update();
      renderer.render(scene, camera);
      labels.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labels.domElement.remove();
      starsGeo.dispose();
      starsMat.dispose();
      lineGeo.dispose();
      lineMat.dispose();
      clickableMeshes.forEach((m) => {
        m.geometry.dispose();
        m.material.map?.dispose();
        m.material.dispose();
      });
    };
  }, []);

  return <div ref={mountRef} className="trinity-view-canvas" />;
});

/**
 * Dedicated Moon & Mars 3D Globe with crater pins & camera flyTo
 */
export const PlanetaryGlobe = forwardRef(function PlanetaryGlobe(
  {
    planet = "moon",
    targets = [],
    selectedId = null,
    onSelectTarget,
    autoRotate = true,
  },
  ref
) {
  const mountRef = useRef(null);
  const apiRef = useRef({});
  const onSelectRef = useRef(onSelectTarget);
  onSelectRef.current = onSelectTarget;
  const targetsRef = useRef(targets);
  targetsRef.current = targets;
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;

  useImperativeHandle(
    ref,
    () => ({
      zoomBy(factor) {
        const camera = apiRef.current.camera;
        if (!camera) return;
        const next = THREE.MathUtils.clamp(camera.position.length() * factor, 1.7, 6.0);
        apiRef.current.flyTo(camera.position.clone().normalize().multiplyScalar(next));
      },
      reset() {
        apiRef.current.flyTo?.(latLngToVector(12, -25, 3.45));
      },
      focus(lat, lng) {
        apiRef.current.flyTo?.(latLngToVector(lat, lng, 2.35));
      },
    }),
    []
  );

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const labels = new CSS2DRenderer();
    labels.domElement.style.position = "absolute";
    labels.domElement.style.inset = "0";
    labels.domElement.style.pointerEvents = "none";
    mount.appendChild(labels.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.55;
    controls.zoomSpeed = 0.7;
    controls.minDistance = 1.8;
    controls.maxDistance = 6.0;
    controls.target.set(0, 0, 0);
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.45;

    let idleTimer = 0;
    const resumeAutoRotate = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        if (!desired.position && controls) {
          controls.autoRotate = true;
        }
      }, 2000);
    };

    controls.addEventListener("start", () => {
      window.clearTimeout(idleTimer);
      controls.autoRotate = false;
    });
    controls.addEventListener("end", resumeAutoRotate);

    const ambientLight = new THREE.AmbientLight(0xffffff, planet === "mars" ? 0.35 : 0.28);
    scene.add(ambientLight);
    const sunLight = new THREE.DirectionalLight(0xfff6ea, 2.8);
    scene.add(sunLight);
    const fillLight = new THREE.DirectionalLight(planet === "mars" ? 0xaa4422 : 0x446688, 0.4);
    scene.add(fillLight);

    const isMars = planet === "mars";
    const material = new THREE.MeshPhongMaterial({
      color: isMars ? 0xc47a52 : 0xb7bcc4,
      emissive: isMars ? 0x220c05 : 0x08090c,
      emissiveIntensity: 0.2,
      shininess: isMars ? 6 : 3,
      specular: isMars ? new THREE.Color("#4a2212") : new THREE.Color("#22262b"),
    });

    const planetMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 80, 80), material);
    scene.add(planetMesh);

    let atmosphereMesh = null;
    if (isMars) {
      atmosphereMesh = marsAtmosphere();
      scene.add(atmosphereMesh);
    }

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(isMars ? MARS_MAP : MOON_MAP, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      material.map = texture;
      material.color.set(0xffffff);
      material.emissiveIntensity = 0.05;
      material.needsUpdate = true;
    });

    const markerGroup = new THREE.Group();
    const labelGroup = new THREE.Group();
    scene.add(markerGroup, labelGroup);

    const markerGeometry = new THREE.SphereGeometry(0.016, 16, 16);
    const markerMaterial = new THREE.MeshBasicMaterial({
      color: isMars ? 0xff7b48 : 0x55c7e8,
    });

    const resize = () => {
      const width = mount.clientWidth || 1;
      const height = mount.clientHeight || 1;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      labels.setSize(width, height);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = null;

    const onDown = (event) => {
      down = { x: event.clientX, y: event.clientY };
    };

    const onUp = (event) => {
      if (!down) return;
      const dx = event.clientX - down.x;
      const dy = event.clientY - down.y;
      down = null;
      if (dx * dx + dy * dy > 16) return;

      const bounds = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
      pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(markerGroup.children, false)[0];
      if (hit?.object.userData.id) {
        onSelectRef.current?.(hit.object.userData.id);
      }
    };

    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    const desired = { position: null };
    const flyTo = (position) => {
      desired.position = position;
      controls.autoRotate = false;
      controls.enabled = false;
    };

    apiRef.current = { scene, camera, renderer, labels, controls, flyTo, markerGroup, labelGroup };

    const rebuild = () => {
      markerGroup.clear();
      while (labelGroup.children.length) {
        const child = labelGroup.children[0];
        child.element.remove();
        labelGroup.remove(child);
      }

      targetsRef.current.forEach((t) => {
        const pos = latLngToVector(t.coordinates.lat, t.coordinates.lng, 1.02);
        const dot = new THREE.Mesh(markerGeometry, markerMaterial);
        dot.position.copy(pos);
        dot.userData.id = t.site_id;
        markerGroup.add(dot);

        const button = document.createElement("button");
        button.type = "button";
        button.className = `globe-pin planet-pin ${isMars ? "mars-pin" : "moon-pin"}`;
        const elev = t.elevation_m != null ? `${Math.round(t.elevation_m)}M` : "SITE";
        button.innerHTML = `<i></i><span>${t.site_name} <b data-badge>${elev}</b></span>`;
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectRef.current?.(t.site_id);
        });

        const label = new CSS2DObject(button);
        label.position.copy(latLngToVector(t.coordinates.lat, t.coordinates.lng, 1.05));
        label.userData.id = t.site_id;
        labelGroup.add(label);
      });
    };

    apiRef.current.rebuild = rebuild;
    rebuild();

    camera.position.copy(latLngToVector(12, -20, 3.45));
    controls.update();

    let frame = 0;
    const sunOffset = new THREE.Vector3();

    const animate = () => {
      frame = requestAnimationFrame(animate);

      if (desired.position) {
        camera.position.lerp(desired.position, 0.05);
        camera.lookAt(0, 0, 0);
        if (camera.position.distanceTo(desired.position) < 0.02) {
          camera.position.copy(desired.position);
          desired.position = null;
          controls.enabled = true;
          controls.update();
          resumeAutoRotate();
        }
      } else {
        controls.update();
      }

      sunOffset.set(4.2, 0.8, 1.6).applyQuaternion(camera.quaternion);
      sunLight.position.copy(camera.position).add(sunOffset);
      fillLight.position.copy(camera.position).add(sunOffset.clone().multiplyScalar(-0.55));

      const origin = camera.position.clone().normalize();
      markerGroup.children.forEach((marker) => {
        const facing = marker.position.clone().normalize().dot(origin) > 0.08;
        marker.visible = facing;
        marker.scale.setScalar(marker.userData.id === selectedRef.current ? 2.0 : 1.0);
      });

      labelGroup.children.forEach((label) => {
        const facing = label.position.clone().normalize().dot(origin) > 0.1;
        label.element.style.opacity = facing ? "1" : "0";
        label.element.style.pointerEvents = facing ? "auto" : "none";
        label.element.classList.toggle("is-selected", label.userData.id === selectedRef.current);
      });

      renderer.render(scene, camera);
      labels.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(idleTimer);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labels.domElement.remove();
      scene.remove(planetMesh, markerGroup, labelGroup);
      if (atmosphereMesh) {
        scene.remove(atmosphereMesh);
        atmosphereMesh.geometry.dispose();
        atmosphereMesh.material.dispose();
      }
      planetMesh.geometry.dispose();
      material.map?.dispose();
      material.dispose();
      markerGeometry.dispose();
      markerMaterial.dispose();
      apiRef.current = {};
    };
  }, [planet]);

  useEffect(() => {
    if (apiRef.current.controls) {
      apiRef.current.controls.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  useEffect(() => {
    apiRef.current.rebuild?.();
  }, [targets]);

  useEffect(() => {
    if (!selectedId || targets.length === 0) return;
    const target = targets.find((t) => t.site_id === selectedId);
    if (target && apiRef.current.flyTo) {
      apiRef.current.flyTo(latLngToVector(target.coordinates.lat, target.coordinates.lng, 2.35));
    }
  }, [selectedId, targets]);

  return <div ref={mountRef} className="planet-view" />;
});

/**
 * Dedicated Earth 3D Globe with atmosphere, rotating clouds, and analog pins
 */
export const EarthGlobe = forwardRef(function EarthGlobe(
  {
    analogs = [],
    selectedId = null,
    onSelectAnalog,
    autoRotate = true,
    isSearching = false,
  },
  ref
) {
  const mountRef = useRef(null);
  const apiRef = useRef({});
  const onSelectRef = useRef(onSelectAnalog);
  onSelectRef.current = onSelectAnalog;
  const analogsRef = useRef(analogs);
  analogsRef.current = analogs;
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;

  useImperativeHandle(
    ref,
    () => ({
      zoomBy(factor) {
        const camera = apiRef.current.camera;
        if (!camera) return;
        const next = THREE.MathUtils.clamp(camera.position.length() * factor, 1.7, 6.0);
        apiRef.current.flyTo(camera.position.clone().normalize().multiplyScalar(next));
      },
      reset() {
        apiRef.current.flyTo?.(latLngToVector(20, 10, 3.45));
      },
      focus(lat, lng) {
        apiRef.current.flyTo?.(latLngToVector(lat, lng, 2.35));
      },
    }),
    []
  );

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const labels = new CSS2DRenderer();
    labels.domElement.style.position = "absolute";
    labels.domElement.style.inset = "0";
    labels.domElement.style.pointerEvents = "none";
    mount.appendChild(labels.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.55;
    controls.zoomSpeed = 0.7;
    controls.minDistance = 1.8;
    controls.maxDistance = 6.0;
    controls.target.set(0, 0, 0);
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.45;

    let idleTimer = 0;
    const resumeAutoRotate = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        if (!desired.position && controls) {
          controls.autoRotate = true;
        }
      }, 2000);
    };

    controls.addEventListener("start", () => {
      window.clearTimeout(idleTimer);
      controls.autoRotate = false;
    });
    controls.addEventListener("end", resumeAutoRotate);

    const ambientLight = new THREE.AmbientLight(0xddeeff, 0.45);
    scene.add(ambientLight);
    const sunLight = new THREE.DirectionalLight(0xffffff, 2.9);
    scene.add(sunLight);
    const rimLight = new THREE.DirectionalLight(0x4488bb, 0.5);
    scene.add(rimLight);

    const earthMaterial = new THREE.MeshPhongMaterial({
      color: 0x99bbee,
      specular: new THREE.Color(0x223344),
      shininess: 12,
    });
    const earthMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 80, 80), earthMaterial);
    scene.add(earthMesh);

    const cloudsMaterial = new THREE.MeshPhongMaterial({
      transparent: true,
      opacity: 0.82,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const cloudsMesh = new THREE.Mesh(new THREE.SphereGeometry(1.014, 64, 64), cloudsMaterial);
    scene.add(cloudsMesh);

    const atmosphereMesh = earthAtmosphere();
    scene.add(atmosphereMesh);

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(EARTH_MAP, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      earthMaterial.map = tex;
      earthMaterial.color.set(0xffffff);
      earthMaterial.needsUpdate = true;
    });
    loader.load(EARTH_CLOUDS, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      cloudsMaterial.map = tex;
      cloudsMaterial.needsUpdate = true;
    });

    const markerGroup = new THREE.Group();
    const labelGroup = new THREE.Group();
    scene.add(markerGroup, labelGroup);

    const markerGeometry = new THREE.SphereGeometry(0.018, 16, 16);
    const markerMaterial = new THREE.MeshBasicMaterial({
      color: 0x2dd4bf,
    });

    const resize = () => {
      const width = mount.clientWidth || 1;
      const height = mount.clientHeight || 1;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      labels.setSize(width, height);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = null;

    const onDown = (event) => {
      down = { x: event.clientX, y: event.clientY };
    };

    const onUp = (event) => {
      if (!down) return;
      const dx = event.clientX - down.x;
      const dy = event.clientY - down.y;
      down = null;
      if (dx * dx + dy * dy > 16) return;

      const bounds = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
      pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(markerGroup.children, false)[0];
      if (hit?.object.userData.id) {
        onSelectRef.current?.(hit.object.userData.id);
      }
    };

    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    const desired = { position: null };
    const flyTo = (position) => {
      desired.position = position;
      controls.autoRotate = false;
      controls.enabled = false;
    };

    apiRef.current = {
      scene,
      camera,
      renderer,
      labels,
      controls,
      flyTo,
      markerGroup,
      labelGroup,
      cloudsMesh,
    };

    const rebuild = () => {
      markerGroup.clear();
      while (labelGroup.children.length) {
        const child = labelGroup.children[0];
        child.element.remove();
        labelGroup.remove(child);
      }

      analogsRef.current.forEach((a) => {
        const pos = latLngToVector(a.coordinates.lat, a.coordinates.lng, 1.02);
        const dot = new THREE.Mesh(markerGeometry, markerMaterial);
        dot.position.copy(pos);
        dot.userData.id = a.site_id;
        markerGroup.add(dot);

        const button = document.createElement("button");
        button.type = "button";
        button.className = "globe-pin earth-pin";
        const score = Math.round(a.similarity_score);
        button.innerHTML = `<i></i><span><b>${score}%</b> ${a.name}</span>`;
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectRef.current?.(a.site_id);
        });

        const label = new CSS2DObject(button);
        label.position.copy(latLngToVector(a.coordinates.lat, a.coordinates.lng, 1.05));
        label.userData.id = a.site_id;
        labelGroup.add(label);
      });
    };

    apiRef.current.rebuild = rebuild;
    rebuild();

    camera.position.copy(latLngToVector(20, 10, 3.45));
    controls.update();

    let frame = 0;
    const sunOffset = new THREE.Vector3();

    const animate = () => {
      frame = requestAnimationFrame(animate);

      if (cloudsMesh) {
        cloudsMesh.rotation.y += 0.0002;
      }

      if (desired.position) {
        camera.position.lerp(desired.position, 0.05);
        camera.lookAt(0, 0, 0);
        if (camera.position.distanceTo(desired.position) < 0.02) {
          camera.position.copy(desired.position);
          desired.position = null;
          controls.enabled = true;
          controls.update();
          resumeAutoRotate();
        }
      } else {
        controls.update();
      }

      sunOffset.set(4.2, 1.0, 1.8).applyQuaternion(camera.quaternion);
      sunLight.position.copy(camera.position).add(sunOffset);
      rimLight.position.copy(camera.position).add(sunOffset.clone().multiplyScalar(-0.6));

      const origin = camera.position.clone().normalize();
      markerGroup.children.forEach((marker) => {
        const facing = marker.position.clone().normalize().dot(origin) > 0.08;
        marker.visible = facing;
        marker.scale.setScalar(marker.userData.id === selectedRef.current ? 2.2 : 1.0);
      });

      labelGroup.children.forEach((label) => {
        const facing = label.position.clone().normalize().dot(origin) > 0.1;
        label.element.style.opacity = facing ? "1" : "0";
        label.element.style.pointerEvents = facing ? "auto" : "none";
        label.element.classList.toggle("is-selected", label.userData.id === selectedRef.current);
      });

      renderer.render(scene, camera);
      labels.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(idleTimer);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labels.domElement.remove();
      scene.remove(earthMesh, cloudsMesh, atmosphereMesh, markerGroup, labelGroup);
      earthMesh.geometry.dispose();
      earthMaterial.map?.dispose();
      earthMaterial.dispose();
      cloudsMesh.geometry.dispose();
      cloudsMaterial.map?.dispose();
      cloudsMaterial.dispose();
      atmosphereMesh.geometry.dispose();
      atmosphereMesh.material.dispose();
      markerGeometry.dispose();
      markerMaterial.dispose();
      apiRef.current = {};
    };
  }, []);

  useEffect(() => {
    if (apiRef.current.controls) {
      apiRef.current.controls.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  useEffect(() => {
    apiRef.current.rebuild?.();
  }, [analogs]);

  useEffect(() => {
    if (!selectedId || analogs.length === 0) return;
    const analog = analogs.find((a) => a.site_id === selectedId);
    if (analog && apiRef.current.flyTo) {
      apiRef.current.flyTo(latLngToVector(analog.coordinates.lat, analog.coordinates.lng, 2.35));
    }
  }, [selectedId, analogs]);

  return (
    <div className={`planet-view earth-view ${isSearching ? "is-scanning" : ""}`}>
      <div ref={mountRef} className="globe-canvas-mount" />
      {isSearching && (
        <div className="earth-scan-overlay">
          <div className="radar-sweep-beam" />
          <span className="scan-telemetry-text">SCANNING TERRESTRIAL CORRELATION MATRIX...</span>
        </div>
      )}
    </div>
  );
});
