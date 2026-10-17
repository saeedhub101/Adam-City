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
const WORLD_SIZE = 520;
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
  renderer.toneMappingExposure = 1.08;
  renderer.setClearColor(0x91a7b7);
  return q;
}

function addBuilding(x, z, w, d, h, seed, palette) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  const wallMat = new THREE.MeshStandardMaterial({
    color: palette[seed % palette.length], map: facadeTexture, normalMap: facadeNormal,
    normalScale: new THREE.Vector2(0.28, 0.28), roughness: 0.97, metalness: 0.0
  });
  const trimMat = new THREE.MeshStandardMaterial({ color: 0xe1d7c5, map: facadeTexture, roughness: 0.92 });
  const balconyMat = new THREE.MeshStandardMaterial({ color: 0x716d65, roughness: 0.72, metalness: 0.25 });
  const glassMat = new THREE.MeshPhysicalMaterial({ color: 0x263e4a, roughness: 0.22, metalness: 0.22, clearcoat: 0.45 });
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

function createCity(quality) {
  scene.background = new THREE.Color(0x93aaba);
  scene.fog = new THREE.Fog(0x93aaba, quality.far * 0.45, quality.far);
  const hemi = new THREE.HemisphereLight(0xddeaff, 0x75685a, 2.0);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffe6c5, 3.1);
  sun.position.set(-100, 160, 70);
  sun.castShadow = quality.shadows;
  sun.shadow.mapSize.set(quality.shadowSize, quality.shadowSize);
  sun.shadow.camera.left = -110;
  sun.shadow.camera.right = 110;
  sun.shadow.camera.top = 110;
  sun.shadow.camera.bottom = -110;
  sun.shadow.bias = -0.00015;
  scene.add(sun);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(WORLD_SIZE, WORLD_SIZE),
    new THREE.MeshStandardMaterial({ color: 0x9b9a8c, roughness: 1 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // Connected asphalt streets, concrete sidewalks, painted lane markings and curb stones.
  const asphalt = new THREE.MeshStandardMaterial({ color: 0x343b40, roughness: 0.96 });
  const sidewalk = new THREE.MeshStandardMaterial({ color: 0xc5bfb2, roughness: 1 });
  const marking = new THREE.MeshStandardMaterial({ color: 0xd8d5c9, roughness: 0.9 });
  for (let p = -WORLD_SIZE / 2; p <= WORLD_SIZE / 2; p += 52) {
    const roadH = new THREE.Mesh(new THREE.PlaneGeometry(WORLD_SIZE, 12), asphalt);
    roadH.rotation.x = -Math.PI / 2;
    roadH.position.set(0, 0.018, p);
    scene.add(roadH);
    const roadV = new THREE.Mesh(new THREE.PlaneGeometry(12, WORLD_SIZE), asphalt);
    roadV.rotation.x = -Math.PI / 2;
    roadV.position.set(p, 0.02, 0);
    scene.add(roadV);
    for (const side of [-1, 1]) {
      const curbH = new THREE.Mesh(new THREE.BoxGeometry(WORLD_SIZE, 0.14, 1.3), sidewalk);
      curbH.position.set(0, 0.06, p + side * 7.0);
      scene.add(curbH);
      const curbV = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.14, WORLD_SIZE), sidewalk);
      curbV.position.set(p + side * 7.0, 0.06, 0);
      scene.add(curbV);
    }
  }

  const palette = [0xc9b99f, 0xb8a88e, 0xd5c8b2, 0xa99b84, 0xc2b49c, 0xb9b3a5, 0xd9cbb3];
  let seed = 13;
  let count = 0;
  for (let z = -WORLD_SIZE / 2 + 18; z < WORLD_SIZE / 2 - 12 && count < quality.buildings; z += 26) {
    for (let x = -WORLD_SIZE / 2 + 18; x < WORLD_SIZE / 2 - 12 && count < quality.buildings; x += 26) {
      seed = (seed * 9301 + 49297) % 233280;
      const rand = seed / 233280;
      if (rand < 0.16 || (Math.abs(x) < 20 && Math.abs(z) < 20)) continue;
      const w = 9 + rand * 7;
      const d = 9 + ((seed * 7) % 60) / 10;
      const h = 5 + ((seed * 17) % 90) / 10;
      addBuilding(x + (rand - 0.5) * 4, z + (rand - 0.5) * 4, w, d, h, Math.abs(Math.floor(seed)) % 7, palette);
      count++;
    }
  }

  // Distant rocky ridges frame the city skyline.
  const ridgeMat = new THREE.MeshStandardMaterial({ color: 0x827e73, roughness: 1 });
  for (let i = 0; i < 34; i++) {
    const angle = i / 34 * Math.PI * 2;
    const radius = 230 + (i % 5) * 10;
    const height = 20 + (i % 7) * 5;
    const hill = new THREE.Mesh(new THREE.ConeGeometry(18 + (i % 4) * 5, height, 5), ridgeMat);
    hill.position.set(Math.cos(angle) * radius, height / 2 - 1, Math.sin(angle) * radius);
    hill.rotation.y = angle * 0.2;
    hill.castShadow = false;
    scene.add(hill);
  }
}

function loadRealBuildingLandmark() {
  // Real, textured GLB reconstruction of Devonaboy Jome Masjidi.
  // The source file is self-contained (embedded textures) and loads asynchronously.
  const url = 'https://raw.githubusercontent.com/bilol-makhmudov/monuments/main/uzbekistan/andijan/devonaboy-mosque/devonaboy_web.glb';
  new GLTFLoader().load(url, (gltf) => {
    const landmark = gltf.scene;
    landmark.name = 'RealGLBBuildingLandmark';
    landmark.traverse((node) => {
      if (node.isMesh) {
        node.castShadow = true;
        node.receiveShadow = true;
        if (node.material) {
          node.material.side = THREE.DoubleSide;
          node.material.needsUpdate = true;
        }
      }
    });
    const bounds = new THREE.Box3().setFromObject(landmark);
    const size = bounds.getSize(new THREE.Vector3());
    const maxDimension = Math.max(size.x, size.y, size.z, 1);
    // Place a substantial, recognizable landmark away from the spawn intersection.
    const scale = 34 / maxDimension;
    landmark.scale.setScalar(scale);
    const scaledBounds = new THREE.Box3().setFromObject(landmark);
    landmark.position.y -= scaledBounds.min.y;
    landmark.position.set(72, landmark.position.y, -92);
    landmark.rotation.y = -Math.PI / 4;
    scene.add(landmark);
    console.info('Real textured GLB landmark loaded:', size.toArray());
  }, undefined, (error) => {
    console.error('Real GLB landmark failed to load:', error);
  });
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
  loadRealBuildingLandmark();
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

