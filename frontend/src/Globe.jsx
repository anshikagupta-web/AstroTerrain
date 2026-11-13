import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";

const EARTH_MAP = "https://threejs.org/examples/textures/planets/earth_atmos_2048.jpg";
const EARTH_CLOUDS = "https://threejs.org/examples/textures/planets/earth_clouds_1024.png";
const MOON_MAP = "https://threejs.org/examples/textures/planets/moon_1024.jpg";
const MARS_MAP = "https://raw.githubusercontent.com/jeromeetienne/threex.planets/master/images/marsmap1k.jpg";

export function latLngToVector(lat, lng, radius) {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lng + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function atmosphere() {
  return new THREE.Mesh(
    new THREE.SphereGeometry(1.12, 64, 64),
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
          float fresnel = pow(0.62 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.8);
          gl_FragColor = vec4(0.35, 0.62, 1.0, 1.0) * fresnel;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
    }),
  );
}

function useStage(mountRef, { distance, minDistance, maxDistance, fov }) {
  const api = useRef({});

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 50);
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
    controls.minDistance = minDistance;
    controls.maxDistance = maxDistance;
    controls.target.set(0, 0, 0);
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    controls.autoRotate = !motion.matches;
    controls.autoRotateSpeed = 0.45;

    scene.add(new THREE.AmbientLight(0x9eb4d8, 0.35));
    const sun = new THREE.DirectionalLight(0xfff6ea, 2.8);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x3d6eaa, 0.35);
    scene.add(fill);

    const desired = { position: null };
    let idle = 0;
    const resume = () => {
      window.clearTimeout(idle);
      idle = window.setTimeout(() => {
        if (!desired.position && !motion.matches) controls.autoRotate = true;
      }, 4000);
    };
    controls.addEventListener("start", () => {
      controls.autoRotate = false;
      desired.position = null;
      controls.enabled = true;
      window.clearTimeout(idle);
    });
    controls.addEventListener("end", resume);

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

    const flyTo = (position) => {
      desired.position = position;
      controls.autoRotate = false;
      controls.enabled = false;
    };

    api.current = { scene, camera, renderer, labels, controls, flyTo, sun, fill, desired };

    let frame = 0;
    const sunOffset = new THREE.Vector3();
    const animate = () => {
      frame = requestAnimationFrame(animate);
      if (desired.position) {
        camera.position.lerp(desired.position, 0.08);
        camera.lookAt(0, 0, 0);
        if (camera.position.distanceTo(desired.position) < 0.02) {
          camera.position.copy(desired.position);
          desired.position = null;
          controls.enabled = true;
          controls.update();
          resume();
        }
      } else {
        controls.update();
      }
      sunOffset.set(4.2, 0.8, 1.6).applyQuaternion(camera.quaternion);
      sun.position.copy(camera.position).add(sunOffset);
      fill.position.copy(camera.position).add(sunOffset.clone().multiplyScalar(-0.55));
      api.current.onFrame?.();
      renderer.render(scene, camera);
      labels.render(scene, camera);
    };
    camera.position.copy(latLngToVector(8, -20, distance));
    controls.update();
    animate();

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(idle);
      observer.disconnect();
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labels.domElement.remove();
      api.current = {};
    };
  }, [distance, fov, maxDistance, minDistance, mountRef]);

  return api;
}

export const PlanetView = forwardRef(function PlanetView({ body = "moon" }, ref) {
  const mountRef = useRef(null);
  const api = useStage(mountRef, { distance: 3.35, minDistance: 1.7, maxDistance: 6, fov: 32 });

  useImperativeHandle(ref, () => ({
    zoomBy(factor) {
      const camera = api.current.camera;
      if (!camera) return;
      const next = THREE.MathUtils.clamp(camera.position.length() * factor, 1.7, 6);
      api.current.flyTo(camera.position.clone().normalize().multiplyScalar(next));
    },
    reset() {
      api.current.flyTo?.(latLngToVector(8, -20, 3.35));
    },
  }), [api]);

  useEffect(() => {
    const scene = api.current.scene;
    if (!scene) return undefined;
    const material = new THREE.MeshPhongMaterial({ color: body === "mars" ? 0xc47a52 : 0xb7bcc4, shininess: 4 });
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), material);
    scene.add(mesh);
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(body === "mars" ? MARS_MAP : MOON_MAP, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      material.map = texture;
      material.color.set(0xffffff);
      material.needsUpdate = true;
    });
    return () => {
      scene.remove(mesh);
      mesh.geometry.dispose();
      material.map?.dispose();
      material.dispose();
    };
  }, [api, body]);

  return <div ref={mountRef} className="planet-view" />;
});

export const EarthView = forwardRef(function EarthView({ markers = [], selectedId, onSelect }, ref) {
  const mountRef = useRef(null);
  const api = useStage(mountRef, { distance: 2.55, minDistance: 1.35, maxDistance: 5.2, fov: 32 });
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const markersRef = useRef(markers);
  markersRef.current = markers;
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;

  useImperativeHandle(ref, () => ({
    zoomBy(factor) {
      const camera = api.current.camera;
      if (!camera) return;
      const next = THREE.MathUtils.clamp(camera.position.length() * factor, 1.35, 5.2);
      api.current.flyTo(camera.position.clone().normalize().multiplyScalar(next));
    },
    reset() {
      api.current.flyTo?.(latLngToVector(8, -90, 2.55));
    },
    focus(lat, lng) {
      api.current.flyTo?.(latLngToVector(lat, lng, 1.7));
    },
  }), [api]);

  useEffect(() => {
    const scene = api.current.scene;
    const camera = api.current.camera;
    const renderer = api.current.renderer;
    if (!scene || !camera || !renderer) return undefined;

    const material = new THREE.MeshPhongMaterial({
      color: 0x8fb7d8,
      emissive: 0x071428,
      emissiveIntensity: 0.4,
      shininess: 8,
      specular: new THREE.Color("#1a3d66"),
    });
    const earth = new THREE.Mesh(new THREE.SphereGeometry(1, 80, 80), material);
    scene.add(earth);
    const cloudMaterial = new THREE.MeshPhongMaterial({ transparent: true, opacity: 0, depthWrite: false });
    const clouds = new THREE.Mesh(new THREE.SphereGeometry(1.02, 64, 64), cloudMaterial);
    scene.add(clouds);
    const air = atmosphere();
    scene.add(air);

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(EARTH_MAP, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      material.map = texture;
      material.color.set(0xffffff);
      material.emissiveIntensity = 0.05;
      material.needsUpdate = true;
    });
    loader.load(EARTH_CLOUDS, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      cloudMaterial.map = texture;
      cloudMaterial.opacity = 0.38;
      cloudMaterial.needsUpdate = true;
    });

    const markerGeometry = new THREE.SphereGeometry(0.014, 14, 14);
    const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xf4f7ff });
    const markerGroup = new THREE.Group();
    const labelGroup = new THREE.Group();
    scene.add(markerGroup, labelGroup);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = null;
    const onDown = (event) => { down = { x: event.clientX, y: event.clientY }; };
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
      if (hit?.object.userData.id) onSelectRef.current?.(hit.object.userData.id);
    };
    renderer.domElement.addEventListener("pointerdown", onDown);
    renderer.domElement.addEventListener("pointerup", onUp);

    const rebuild = () => {
      markerGroup.clear();
      while (labelGroup.children.length) {
        const child = labelGroup.children[0];
        child.element.remove();
        labelGroup.remove(child);
      }
      markersRef.current.forEach((marker) => {
        const dot = new THREE.Mesh(markerGeometry, markerMaterial);
        dot.position.copy(latLngToVector(marker.lat, marker.lng, 1.02));
        dot.userData.id = marker.id;
        markerGroup.add(dot);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "globe-pin";
        button.innerHTML = `<i></i><span>${marker.name} <b data-badge>${marker.badge}</b></span>`;
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectRef.current?.(marker.id);
        });
        const label = new CSS2DObject(button);
        label.position.copy(latLngToVector(marker.lat, marker.lng, 1.05));
        label.userData.id = marker.id;
        labelGroup.add(label);
      });
    };
    api.current.rebuild = rebuild;
    api.current.onFrame = () => {
      clouds.rotation.y += 0.00025;
      const origin = camera.position.clone().normalize();
      markerGroup.children.forEach((marker) => {
        const facing = marker.position.clone().normalize().dot(origin) > 0.08;
        marker.visible = facing;
        marker.scale.setScalar(marker.userData.id === selectedRef.current ? 1.8 : 1);
      });
      labelGroup.children.forEach((label) => {
        const facing = label.position.clone().normalize().dot(origin) > 0.1;
        label.element.style.opacity = facing ? "1" : "0";
        label.element.style.pointerEvents = facing ? "auto" : "none";
        label.element.classList.toggle("is-selected", label.userData.id === selectedRef.current);
      });
    };
    rebuild();
    camera.position.copy(latLngToVector(8, -90, 2.55));
    api.current.controls?.update();

    return () => {
      renderer.domElement.removeEventListener("pointerdown", onDown);
      renderer.domElement.removeEventListener("pointerup", onUp);
      scene.remove(earth, clouds, air, markerGroup, labelGroup);
      earth.geometry.dispose();
      clouds.geometry.dispose();
      air.geometry.dispose();
      material.map?.dispose();
      material.dispose();
      cloudMaterial.map?.dispose();
      cloudMaterial.dispose();
      air.material.dispose();
      markerGeometry.dispose();
      markerMaterial.dispose();
      api.current.onFrame = null;
      api.current.rebuild = null;
    };
  }, [api]);

  useEffect(() => {
    api.current.rebuild?.();
  }, [api, markers]);

  useEffect(() => {
    if (!selectedId) return;
    const marker = markersRef.current.find((item) => item.id === selectedId);
    if (marker) api.current.flyTo?.(latLngToVector(marker.lat, marker.lng, 1.75));
  }, [api, selectedId]);

  return <div ref={mountRef} className="earth-view" />;
});
