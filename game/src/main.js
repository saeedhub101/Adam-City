import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import './style.css';

const canvas = document.querySelector('#world');
const settings = document.querySelector('#settings');
const qualitySelect = document.querySelector('#quality');
const startButton = document.querySelector('#start');
const hud = document.querySelector('#hud');
const statusText = document.querySelector('#status-text');
const hint = document.querySelector('#hint');
const errorBox = document.querySelector('#error');
const referencePanel = document.querySelector('#local-reference');
document.querySelector('#close-reference')?.addEventListener('click', () => { if (referencePanel) referencePanel.hidden = true; });
const buildingList = document.querySelector('#building-photo-list');
const buildingCount = document.querySelector('#building-photo-count');

function renderBuildingPhotoLinks(buildings) {
  if (!buildingList) return;
  buildingList.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const way of buildings) {
    const tags = way.tags || {};
    const points = way.geometry || [];
    if (!points.length) continue;
    const lat = points.reduce((sum, point) => sum + point.lat, 0) / points.length;
    const lon = points.reduce((sum, point) => sum + point.lon, 0) / points.length;
    const label = tags.name || tags['addr:housenumber'] || ('مبنى OSM #' + way.id);
    const item = document.createElement('a');
    item.className = 'building-photo-item';
    item.href = tags.mapillary
      ? 'https://www.mapillary.com/app/?pKey=' + encodeURIComponent(tags.mapillary)
      : 'https://www.mapillary.com/app/?lat=' + lat.toFixed(6) + '&lng=' + lon.toFixed(6) + '&z=18';
    item.target = '_blank';
    item.rel = 'noreferrer';
    const title = document.createElement('strong');
    title.textContent = label;
    const detail = document.createElement('span');
    detail.textContent = tags.mapillary
      ? 'صورة مرتبطة بهذا المبنى في بيانات الخريطة'
      : 'افتح صور الشارع قرب موقع المبنى';
    item.append(title, detail);
    if (tags.image || tags.wikimedia_commons) {
      const source = document.createElement('span');
      source.className = 'building-photo-source';
      source.textContent = tags.image ? 'رابط صورة مضاف في OpenStreetMap' : 'مرجع Wikimedia Commons مضاف في OpenStreetMap';
      item.append(source);
      if (tags.image) item.href = tags.image.startsWith('http') ? tags.image : 'https://' + tags.image;
      else if (tags.wikimedia_commons) item.href = 'https://commons.wikimedia.org/wiki/' + encodeURIComponent(tags.wikimedia_commons).replace(/%3A/g, ':').replace(/%2F/g, '/');
    }
    fragment.append(item);
  }
  buildingList.append(fragment);
  if (buildingCount) buildingCount.textContent = buildings.length + ' مبنى';
}

const QUALITY = {
  low:    { pixelRatio: 0.85, shadows: false, shadowSize: 512, far: 360, buildings: 45, antialias: false },
  medium: { pixelRatio: 1.0,  shadows: true,  shadowSize: 1024, far: 600, buildings: 80, antialias: true },
  high:   { pixelRatio: 1.5,  shadows: true,  shadowSize: 2048, far: 900, buildings: 125, antialias: true },
  ultra:  { pixelRatio: 2.0,  shadows: true,  shadowSize: 4096, far: 1300, buildings: 175, antialias: true }
};

let renderer, scene, camera, player, mixer = null;
let running = false;
let yaw = 0;
let pitch = -0.13;
let velocityY = 0;
let onGround = true;
let elapsed = 0;
const clock = new THREE.Clock();
const keys = new Set();
const obstacles = [];
const WORLD_SIZE = 1200;
const PLAYER_HEIGHT = 1.72;
const playerRoot = new THREE.Group();
const cameraTarget = new THREE.Vector3();
const desiredCamera = new THREE.Vector3();
const forward = new THREE.Vector3();
const right = new THREE.Vector3();
const move = new THREE.Vector3();
const raycaster = new THREE.Raycaster();

// Photographic PBR facade material from Poly Haven (CC0).
// The texture is tileable and loaded asynchronously so the scene can start immediately.
const facadeTexture = new THREE.TextureLoader().load(
  'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/plastered_wall/plastered_wall_diff_1k.jpg',
  (texture) => {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(2, 2);
  },
  undefined,
  (error) => console.warn('Facade texture unavailable; using fallback material.', error)
);
const facadeNormal = new THREE.TextureLoader().load(
  'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/plastered_wall/plastered_wall_nor_gl_1k.jpg',
  (texture) => {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(2, 2);
  },
  undefined,
  (error) => console.warn('Facade normal map unavailable; using fallback material.', error)
);

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

function initRenderer(qualityKey) {
  const q = QUALITY[qualityKey] ?? QUALITY.medium;
  if (renderer) {
    renderer.dispose();
    renderer.domElement.remove();
  }
  renderer = new THREE.WebGLRenderer({ canvas, antialias: q.antialias, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, q.pixelRatio));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = q.shadows;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  // Filmic exposure and physically-based output keep materials grounded instead of toy-like.
  renderer.toneMappingExposure = 0.92;
  renderer.setClearColor(0x9aa9b4);
  return q;
}

function addBuilding(x, z, w, d, h, seed, palette) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  const wallMat = new THREE.MeshStandardMaterial({
    color: palette[seed % palette.length], map: facadeTexture, normalMap: facadeNormal,
    normalScale: new THREE.Vector2(0.28, 0.28), roughness: 0.94, metalness: 0.0
  });
  const trimMat = new THREE.MeshStandardMaterial({ color: 0xe1d7c5, map: facadeTexture, roughness: 0.92 });
  const balconyMat = new THREE.MeshStandardMaterial({ color: 0x716d65, roughness: 0.72, metalness: 0.25 });
  const glassMat = new THREE.MeshPhysicalMaterial({ color: 0x263e4a, roughness: 0.32, metalness: 0.08, clearcoat: 0.18 });
  const box = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
  box.position.y = h / 2;
  box.castShadow = true;
  box.receiveShadow = true;
  group.add(box);

  const roof = new THREE.Mesh(
    new THREE.BoxGeometry(w + 0.16, 0.16, d + 0.16),
    new THREE.MeshStandardMaterial({ color: 0x9b958a, roughness: 0.92 })
  );
  roof.position.y = h + 0.08;
  roof.castShadow = true;
  group.add(roof);

  // Parapets, rooftop service rooms and deep limestone window surrounds.
  const limestone = new THREE.MeshStandardMaterial({ color: 0xd1c4ad, map: facadeTexture, roughness: 0.96 });
  const parapet = new THREE.Mesh(new THREE.BoxGeometry(w + 0.18, 0.42, 0.18), limestone);
  parapet.position.set(0, h + 0.25, d / 2 - 0.02);
  parapet.castShadow = true;
  group.add(parapet);
  const sideParapet = parapet.clone();
  sideParapet.rotation.y = Math.PI / 2;
  sideParapet.scale.set(d / (w + 0.18), 1, 1);
  sideParapet.position.set(w / 2 - 0.02, h + 0.25, 0);
  group.add(sideParapet);
  if (seed % 3 === 0) {
    const rooftopRoom = new THREE.Mesh(new THREE.BoxGeometry(w * 0.32, 1.4, d * 0.3), wallMat);
    rooftopRoom.position.set(-w * 0.22, h + 0.85, -d * 0.18);
    rooftopRoom.castShadow = true;
    group.add(rooftopRoom);
  }

  // Recessed-looking dark window strips add scale without excessive draw calls.
  const floors = Math.max(1, Math.floor(h / 3.1));
  const windows = glassMat;
  for (let floor = 0; floor < floors; floor++) {
    const wy = 1.05 + floor * 3.05;
    if (wy > h - 0.45) continue;
    const count = Math.max(1, Math.floor(w / 2.5));
    for (let i = 0; i < count; i++) {
      const wx = -w / 2 + (i + 0.5) * w / count;
      const ww = Math.min(1.15, w / count * 0.56);
      const win = new THREE.Mesh(new THREE.BoxGeometry(ww, 1.18, 0.055), windows);
      win.position.set(wx, wy, d / 2 + 0.018);
      group.add(win);
      const winBack = win.clone();
      winBack.position.z = -d / 2 - 0.018;
      group.add(winBack);
    }
  }
  scene.add(group);
  obstacles.push({ minX: x - w / 2 - 0.8, maxX: x + w / 2 + 0.8, minZ: z - d / 2 - 0.8, maxZ: z + d / 2 + 0.8 });
}

const TABARBOUR = { lat: 31.9915, lon: 35.9445 };
// Real mapped pilot area around the Tabarbour / Lawyers' Roundabout area.
const TABARBOUR_BBOX = { south: 31.9855, west: 35.9370, north: 31.9980, east: 35.9520 };

function localPoint(lat, lon) {
  return {
    x: (lon - TABARBOUR.lon) * 111320 * Math.cos(TABARBOUR.lat * Math.PI / 180),
    z: -(lat - TABARBOUR.lat) * 111320
  };
}
function wayPoints(way) { return (way.geometry || []).map(p => localPoint(p.lat, p.lon)); }

function addOSMRoad(points, width, material, y = 0.035) {
  if (points.length < 2) return;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i], b = points[i + 1];
    const dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz);
    if (length < 0.5) continue;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, length), material);
    mesh.rotation.x = -Math.PI / 2;
    mesh.rotation.z = -Math.atan2(dz, dx) - Math.PI / 2;
    mesh.position.set((a.x + b.x) / 2, y, (a.z + b.z) / 2);
    scene.add(mesh);
  }
}

function addOSMBuilding(way, index) {
  const pts = wayPoints(way);
  if (pts.length < 4) return;
  if (Math.hypot(pts[0].x - pts[pts.length - 1].x, pts[0].z - pts[pts.length - 1].z) > 1.5) return;
  const ring = pts.slice(0, -1);
  if (ring.length < 3) return;
  const shape = new THREE.Shape();
  shape.moveTo(ring[0].x, -ring[0].z);
  for (let i = 1; i < ring.length; i++) shape.lineTo(ring[i].x, -ring[i].z);
  shape.closePath();
  const tags = way.tags || {};
  const rawHeight = Number.parseFloat(String(tags.height || '').replace(/m$/i, ''));
  const levels = Number.parseFloat(tags['building:levels'] || tags.levels || '');
  const height = Number.isFinite(rawHeight) && rawHeight > 2 ? THREE.MathUtils.clamp(rawHeight, 3, 55)
    : Number.isFinite(levels) && levels > 0 ? THREE.MathUtils.clamp(levels * 3.1, 3, 55) : 7.5;
  const colors = [0xcbbba3, 0xd7c8b1, 0xb8a88f, 0xd0c2ab, 0xbeb09a, 0xe0d2bd];
  const material = new THREE.MeshStandardMaterial({
    color: colors[index % colors.length], map: facadeTexture, normalMap: facadeNormal,
    normalScale: new THREE.Vector2(0.22, 0.22), roughness: 0.96
  });
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, curveSegments: 1 });
  geometry.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true; mesh.receiveShadow = true;
  mesh.name = 'OSM-building-' + (tags.name || way.id || index);
  scene.add(mesh);
  const xs = ring.map(p => p.x), zs = ring.map(p => p.z);
  obstacles.push({ minX: Math.min(...xs)-0.65, maxX: Math.max(...xs)+0.65, minZ: Math.min(...zs)-0.65, maxZ: Math.max(...zs)+0.65 });
  const roofShape = new THREE.Shape();
  roofShape.moveTo(ring[0].x, -ring[0].z);
  for (let i = 1; i < ring.length; i++) roofShape.lineTo(ring[i].x, -ring[i].z);
  roofShape.closePath();
  const roofGeo = new THREE.ShapeGeometry(roofShape);
  roofGeo.rotateX(-Math.PI / 2);
  const roof = new THREE.Mesh(roofGeo, new THREE.MeshStandardMaterial({ color: 0x9d9689, roughness: 1, side: THREE.DoubleSide }));
  roof.position.y = height; roof.receiveShadow = true; scene.add(roof);
}

async function loadTabarbourMap() {
  const b = TABARBOUR_BBOX;
  const query = '[out:json][timeout:25];(way["building"](' + b.south + ',' + b.west + ',' + b.north + ',' + b.east +
    ');way["highway"](' + b.south + ',' + b.west + ',' + b.north + ',' + b.east + '););out body geom;';
  let data = null;
  // Prefer the versioned snapshot shipped with the game. It is refreshed by
  // .github/workflows/refresh-tabarbour-map.yml and does not require Overpass at runtime.
  try {
    const response = await fetch('/data/tabarbour-osm.json', { cache: 'no-store' });
    if (response.ok) {
      const parsed = await response.json();
      if (Array.isArray(parsed.elements) && parsed.elements.length) data = parsed;
    }
  } catch (error) {
    console.warn('Local Tabarbour map snapshot unavailable:', error);
  }
  // Network fallback is only for first setup or if the checked-in snapshot is missing.
  if (!data) {
    const endpoints = ['https://overpass.kumi.systems/api/interpreter?data=', 'https://overpass-api.de/api/interpreter?data='];
    for (const endpoint of endpoints) {
      try {
        const response = await fetch(endpoint + encodeURIComponent(query), { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error('OSM server HTTP ' + response.status);
        const parsed = await response.json();
        if (Array.isArray(parsed.elements) && parsed.elements.length) { data = parsed; break; }
      } catch (error) { console.warn('Tabarbour OSM endpoint failed:', endpoint, error); }
    }
  }
  if (!data) {
    statusText.textContent = 'OpenStreetMap data unavailable';
    showError('تعذر العثور على نسخة خريطة طبربور المحلية أو تحميل بياناتها أول مرة. شغّل Workflow تحديث خريطة طبربور في GitHub Actions ثم أعد تحميل اللعبة.');
    return;
  }
  // Merge the checked-in OSM snapshot with our own persistent map edits.
  // Keep custom edits in a separate file so refreshing OSM never overwrites them.
  let customData = { elements: [] };
  try {
    const customResponse = await fetch('/data/tabarbour-custom.json', { cache: 'no-store' });
    if (customResponse.ok) {
      const parsedCustom = await customResponse.json();
      if (Array.isArray(parsedCustom.elements)) customData = parsedCustom;
    }
  } catch (error) {
    console.warn('Custom Tabarbour map edits unavailable; loading OSM only:', error);
  }
  const customElements = customData.elements;
  const customIds = new Set(customElements.map(e => String(e.id)));
  const osmElements = data.elements.filter(e => !customIds.has(String(e.id)));
  const allElements = [...osmElements, ...customElements];
  const roads = allElements.filter(e => e.type === 'way' && e.tags?.highway);
  const buildings = allElements.filter(e => e.type === 'way' && e.tags?.building);
  const asphalt = new THREE.MeshStandardMaterial({ color: 0x34393c, roughness: 0.98 });
  const curb = new THREE.MeshStandardMaterial({ color: 0xd2cbbd, roughness: 1 });
  const roadWidth = tags => {
    const tagged = Number.parseFloat(tags.width || '');
    if (Number.isFinite(tagged)) return THREE.MathUtils.clamp(tagged, 2.5, 28);
    if (['motorway','trunk','primary'].includes(tags.highway)) return 11;
    if (['secondary','tertiary'].includes(tags.highway)) return 8;
    if (['residential','unclassified'].includes(tags.highway)) return 5.8;
    if (['service','living_street'].includes(tags.highway)) return 3.5;
    return 2.5;
  };
  for (const road of roads) {
    const points = wayPoints(road);
    if (points.length < 2) continue;
    const width = roadWidth(road.tags || {});
    addOSMRoad(points, width, asphalt, 0.026);
    if (width >= 5.5) addOSMRoad(points, 0.16, curb, 0.041);
  }
  buildings.forEach(addOSMBuilding);
  renderBuildingPhotoLinks(buildings);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1200, 1200), new THREE.MeshStandardMaterial({ color: 0xaaa395, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.03; ground.receiveShadow = true; scene.add(ground);
  playerRoot.position.set(0, 0, 0);
  statusText.textContent = 'طبربور · ' + buildings.length + ' مبنى مرسوم من الخريطة · ' + roads.length + ' شارع';
  console.info('Loaded real OSM Tabarbour data', { buildings: buildings.length, roads: roads.length });
}

function createCity(quality) {
  // Natural Amman daylight: neutral sky, warm sun, restrained atmospheric haze.
  const sky = new THREE.Color(0xaebdc7);
  scene.background = sky;
  scene.fog = new THREE.Fog(sky, quality.far * 0.72, quality.far * 1.65);
  scene.environment = null;
  scene.add(new THREE.HemisphereLight(0xe2e9ed, 0x62584b, 1.15));
  const sun = new THREE.DirectionalLight(0xfff0d9, 2.35);
  sun.position.set(-120, 180, 95);
  sun.castShadow = quality.shadows;
  sun.shadow.mapSize.set(quality.shadowSize, quality.shadowSize);
  sun.shadow.camera.left = -220; sun.shadow.camera.right = 220;
  sun.shadow.camera.top = 220; sun.shadow.camera.bottom = -220;
  sun.shadow.bias = -0.00012;
  sun.shadow.normalBias = 0.025;
  scene.add(sun);
  // Soft fill prevents pitch-black shaded facades while preserving sun direction.
  const fill = new THREE.DirectionalLight(0xc5d5e0, 0.32);
  fill.position.set(90, 45, -100);
  scene.add(fill);
  loadTabarbourMap();
}

function setupPlayer() {
  playerRoot.position.set(0, 0, 0);
  scene.add(playerRoot);
  const loader = new GLTFLoader();
  const modelUrl = 'https://raw.githubusercontent.com/saeedhub101/Saeed-Fortnite-/main/3/saeed.glb';
  statusText.textContent = 'Loading character…';
  loader.load(modelUrl, (gltf) => {
    player = gltf.scene;
    player.traverse((obj) => {
      if (obj.isMesh) {
        obj.castShadow = true;
        obj.receiveShadow = true;
        if (obj.morphTargetDictionary) {
          // Preserve shape keys for future facial animation; do not run imported clips.
          obj.morphTargetInfluences?.forEach((_, i) => {
            if (obj.morphTargetDictionary.eyeBlinkLeft === i || obj.morphTargetDictionary.eyeBlinkRight === i) {
              obj.morphTargetInfluences[i] = 0;
            }
          });
        }
      }
    });
    const bounds = new THREE.Box3().setFromObject(player);
    const size = bounds.getSize(new THREE.Vector3());
    const scale = PLAYER_HEIGHT / Math.max(size.y, 0.01);
    player.scale.setScalar(scale);
    const scaledBounds = new THREE.Box3().setFromObject(player);
    player.position.y -= scaledBounds.min.y;
    playerRoot.add(player);
    statusText.textContent = 'Character ready · new controls active';
  }, undefined, (err) => {
    console.error('Character load failed', err);
    statusText.textContent = 'Character could not load';
    showError('The city started, but the character model could not load. Check your internet connection and the raw GitHub asset URL.');
  });
}

function setupWorld(qualityKey) {
  const quality = initRenderer(qualityKey);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(62, window.innerWidth / window.innerHeight, 0.1, quality.far + 100);
  camera.position.set(0, 3.2, 7);
  obstacles.length = 0;
  createCity(quality);
  setupPlayer();
  renderer.setAnimationLoop(frame);
}

function enterGame() {
  settings.classList.add('hidden');
  hud.classList.remove('hidden');
  running = true;
  if (!renderer) setupWorld(qualitySelect.value);
  else renderer.setAnimationLoop(frame);
}

startButton.addEventListener('click', enterGame);
canvas.addEventListener('click', () => {
  if (running && document.pointerLockElement !== canvas) canvas.requestPointerLock?.();
});
document.addEventListener('pointerlockchange', () => {
  hint.textContent = document.pointerLockElement === canvas ? 'Mouse captured · Esc to release' : 'Click the scene to capture mouse';
});
document.addEventListener('mousemove', (event) => {
  if (document.pointerLockElement !== canvas || !running) return;
  yaw -= event.movementX * 0.0022;
  pitch = THREE.MathUtils.clamp(pitch - event.movementY * 0.0017, -0.9, 0.25);
});
document.addEventListener('keydown', (event) => {
  if (['Space','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.code)) event.preventDefault();
  keys.add(event.code);
  if (event.code === 'Space' && onGround && running) {
    velocityY = 6.5;
    onGround = false;
  }
});
document.addEventListener('keyup', (event) => keys.delete(event.code));
window.addEventListener('blur', () => keys.clear());
window.addEventListener('resize', () => {
  if (!renderer || !camera) return;
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function collides(x, z) {
  return obstacles.some((b) => x > b.minX && x < b.maxX && z > b.minZ && z < b.maxZ);
}

function frame() {
  const dt = Math.min(clock.getDelta(), 0.04);
  elapsed += dt;
  if (running) {
    forward.set(-Math.sin(yaw), 0, -Math.cos(yaw));
    right.set(Math.cos(yaw), 0, -Math.sin(yaw));
    move.set(0, 0, 0);
    if (keys.has('KeyW') || keys.has('ArrowUp')) move.add(forward);
    if (keys.has('KeyS') || keys.has('ArrowDown')) move.sub(forward);
    if (keys.has('KeyD') || keys.has('ArrowRight')) move.add(right);
    if (keys.has('KeyA') || keys.has('ArrowLeft')) move.sub(right);
    if (move.lengthSq() > 0) {
      move.normalize();
      const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 8.0 : 4.3;
      const nx = THREE.MathUtils.clamp(playerRoot.position.x + move.x * speed * dt, -WORLD_SIZE/2 + 3, WORLD_SIZE/2 - 3);
      const nz = THREE.MathUtils.clamp(playerRoot.position.z + move.z * speed * dt, -WORLD_SIZE/2 + 3, WORLD_SIZE/2 - 3);
      if (!collides(nx, playerRoot.position.z)) playerRoot.position.x = nx;
      if (!collides(playerRoot.position.x, nz)) playerRoot.position.z = nz;
      playerRoot.rotation.y = Math.atan2(move.x, move.z);
    }
    velocityY -= 17.5 * dt;
    playerRoot.position.y += velocityY * dt;
    if (playerRoot.position.y <= 0) {
      playerRoot.position.y = 0;
      velocityY = 0;
      onGround = true;
    }

    cameraTarget.copy(playerRoot.position).add(new THREE.Vector3(0, 1.35, 0));
    const distance = 5.2;
    desiredCamera.set(
      cameraTarget.x + Math.sin(yaw) * Math.cos(pitch) * distance,
      cameraTarget.y + 1.1 + Math.sin(-pitch) * distance,
      cameraTarget.z + Math.cos(yaw) * Math.cos(pitch) * distance
    );
    camera.position.lerp(desiredCamera, 1 - Math.exp(-8 * dt));
    camera.lookAt(cameraTarget);
  }
  renderer?.render(scene, camera);
}

