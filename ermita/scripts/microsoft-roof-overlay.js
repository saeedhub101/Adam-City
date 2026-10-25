/* Microsoft satellite-derived roof surfaces draped onto the existing Ermita/Malate GLB buildings.
   The GLBs remain the geometry source of truth; this adds only roof-face overlays.
   Microsoft footprints are approximate (2016–2020 imagery) and are used only where
   the polygon can be ray-projected onto an existing GLB roof. */
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'https://cdn.jsdelivr.net/npm/meshoptimizer@0.22.0/meshopt_decoder.module.js';

(async function () {
  const status = document.getElementById('status');
  const errorBox = document.getElementById('error');
  const map = await waitForMap();
  if (!map) return;

  const sourceUrl = new URL('ermita/maps/sources/microsoft-satellite-buildings/microsoft-philippines-satellite-footprints-malate.geojson', location.href).href;
  const root = 'complete_data/OSM/data/buildings/Ermita/';
  const checkbox = makeToggle();
  const parts = new Map();
  let sourceFeatures = null;
  let loading = false;
  let enabled = false;

  function waitForMap() {
    return new Promise(resolve => {
      let tries = 0;
      const poll = () => {
        const candidate = window.manilaMap || window.adamCityMap;
        if (candidate && candidate.isStyleLoaded()) return resolve(candidate);
        if (++tries > 900) {
          showError(new Error('انتهت مهلة انتظار الخريطة لتجهيز أسطح Microsoft.'));
          return resolve(null);
        }
        setTimeout(poll, 100);
      };
      poll();
    });
  }

  function makeToggle() {
    const label = document.createElement('label');
    label.style.cssText = 'display:flex;gap:8px;align-items:flex-start;margin:8px 0;padding:9px;border:1px solid #607987;border-radius:8px;background:#182b35;color:#f2f6f8;font-size:12px;line-height:1.45;cursor:pointer;';
    label.innerHTML = '<input id="microsoft-roof-overlay-toggle" type="checkbox" style="flex:0 0 auto;margin-top:2px;accent-color:#d6b58a;width:16px;height:16px"><span><b>Microsoft — أسطح مباني Malate فوق GLB</b><small style="display:block;color:#b9c8cf;font-size:10px">تراكب أسطح فقط؛ هندسة GLB الأصلية لا تتغير</small></span>';
    const panel = document.querySelector('.panel') || document.querySelector('aside');
    if (panel) panel.insertBefore(label, panel.firstChild);
    const input = label.querySelector('input');
    input.addEventListener('change', async () => {
      enabled = input.checked;
      input.disabled = true;
      try {
        if (enabled) await enableOverlays();
        else hideOverlays();
      } catch (e) {
        input.checked = false;
        enabled = false;
        showError(e);
      } finally {
        input.disabled = false;
      }
    });
    return input;
  }

  function showError(error) {
    const message = 'Microsoft roof overlay: ' + (error?.message || String(error));
    if (status) status.textContent = message;
    if (errorBox) {
      errorBox.style.display = 'block';
      errorBox.textContent = message;
    }
    console.error(message, error);
  }

  async function loadSource() {
    if (sourceFeatures) return sourceFeatures;
    const response = await fetch(sourceUrl);
    if (!response.ok) throw new Error('HTTP ' + response.status + ' عند تحميل footprints: ' + sourceUrl);
    const data = await response.json();
    if (!Array.isArray(data.features)) throw new Error('ملف Microsoft ليس FeatureCollection صالحًا.');
    sourceFeatures = data.features.filter(f => f && f.geometry && ['Polygon', 'MultiPolygon'].includes(f.geometry.type));
    if (!sourceFeatures.length) throw new Error('ملف Microsoft لا يحتوي مضلعات مبانٍ.');
    return sourceFeatures;
  }

  async function enableOverlays() {
    if (loading) return;
    loading = true;
    if (status) status.textContent = 'جارٍ إسقاط مضلعات Microsoft على أسطح GLB الأصلية…';
    try {
      const features = await loadSource();
      let total = 0;
      let matched = 0;
      for (let part = 1; part <= 4; part++) {
        let entry = parts.get(part);
        if (!entry) {
          entry = await buildPartOverlay(part, features);
          parts.set(part, entry);
        }
        entry.group.visible = true;
        total += entry.candidateCount;
        matched += entry.roofCount;
      }
      if (status) status.textContent = 'تم تطبيق أسطح Microsoft على GLB: ' + matched + ' سطحًا مطابقًا من ' + total + ' مضلعًا مرشحًا. لم تتغير ملفات GLB الأصلية.';
    } finally {
      loading = false;
    }
  }

  function hideOverlays() {
    for (const entry of parts.values()) {
      entry.group.visible = false;
    }
    if (status) status.textContent = 'تم إخفاء أسطح Microsoft؛ ملفات GLB الأصلية لم تتغير.';
  }

  async function buildPartOverlay(part, features) {
    const originUrl = new URL(root + 'part' + part + '/part' + part + '-origin.json', location.href).href;
    const modelUrl = new URL(root + 'Parts' + part + '.glb', location.href).href;
    const [originResponse, gltf] = await Promise.all([
      fetch(originUrl).then(r => { if (!r.ok) throw new Error('Origin part ' + part + ' HTTP ' + r.status); return r.json(); }),
      loadModel(modelUrl)
    ]);
    const projected = originResponse.origin_projected_m || {};
    const originWgs = originResponse.origin_wgs84 || {};
    const lon = Number(originWgs.longitude), lat = Number(originWgs.latitude);
    const ox = Number(projected.x), oy = Number(projected.y);
    if (![lon, lat, ox, oy].every(Number.isFinite)) throw new Error('إحداثيات origin غير صالحة للجزء ' + part);
    const anchor = maplibregl.MercatorCoordinate.fromLngLat({ lng: lon, lat }, 0);
    const meters = anchor.meterInMercatorCoordinateUnits();

    const model = gltf.scene;
    model.updateMatrixWorld(true);
    const meshes = [];
    const bounds = new THREE.Box3();
    model.traverse(object => {
      if (!object.isMesh || !object.geometry) return;
      object.updateWorldMatrix(true, false);
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      const box = new THREE.Box3().setFromObject(object);
      if (box.isEmpty()) return;
      bounds.union(box);
      meshes.push({ object, box });
    });
    if (!meshes.length || bounds.isEmpty()) throw new Error('لا توجد meshes قابلة للفحص في GLB الجزء ' + part);

    // Spatial grid keeps ray tests local rather than checking every mesh for every footprint.
    const cellSize = 40;
    const grid = new Map();
    const cellKey = (x, y) => Math.floor(x / cellSize) + ':' + Math.floor(y / cellSize);
    for (const mesh of meshes) {
      const minX = Math.floor(mesh.box.min.x / cellSize), maxX = Math.floor(mesh.box.max.x / cellSize);
      const minY = Math.floor(mesh.box.min.y / cellSize), maxY = Math.floor(mesh.box.max.y / cellSize);
      for (let gx = minX; gx <= maxX; gx++) for (let gy = minY; gy <= maxY; gy++) {
        const key = gx + ':' + gy;
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(mesh.object);
      }
    }
    const raycaster = new THREE.Raycaster();
    raycaster.near = 0;
    raycaster.far = 2000;

    function localPoint(coordinate) {
      const mc = maplibregl.MercatorCoordinate.fromLngLat({ lng: Number(coordinate[0]), lat: Number(coordinate[1]) }, 0);
      return new THREE.Vector2((mc.x - anchor.x) / meters, (anchor.y - mc.y) / meters);
    }
    function candidatesAt(x, y) {
      return grid.get(cellKey(x, y)) || [];
    }
    function roofHeight(x, y) {
      const candidates = candidatesAt(x, y);
      if (!candidates.length) return null;
      raycaster.set(new THREE.Vector3(x, y, Math.max(bounds.max.z + 500, 500)), new THREE.Vector3(0, 0, -1));
      const hits = raycaster.intersectObjects(candidates, false);
      return hits.length ? hits[0].point.z : null;
    }
    function polygonRingsToLocal(rings) {
      return rings.map(ring => ring.slice(0, -1).map(localPoint)).filter(ring => ring.length >= 3);
    }
    function addPolygon(group, rings, featureKey) {
      const localRings = polygonRingsToLocal(rings);
      if (!localRings.length) return false;
      const contour = localRings[0];
      const centroid = contour.reduce((a, p) => a.add(p), new THREE.Vector2()).multiplyScalar(1 / contour.length);
      if (centroid.x < bounds.min.x - 8 || centroid.x > bounds.max.x + 8 || centroid.y < bounds.min.y - 8 || centroid.y > bounds.max.y + 8) return false;
      const centerZ = roofHeight(centroid.x, centroid.y);
      if (centerZ === null) return false;

      const zValues = [];
      let hits = 0;
      for (const p of contour) {
        const z = roofHeight(p.x, p.y);
        if (z !== null) { zValues.push(z + 0.06); hits++; }
        else zValues.push(centerZ + 0.06);
      }
      if (hits < Math.max(2, Math.ceil(contour.length * 0.45))) return false;

      const triangles = THREE.ShapeUtils.triangulateShape(contour, []);
      if (!triangles.length) return false;
      const positions = [];
      for (let i = 0; i < contour.length; i++) positions.push(contour[i].x, contour[i].y, zValues[i]);
      const indices = [];
      for (const tri of triangles) indices.push(tri[0], tri[1], tri[2]);
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      const material = new THREE.MeshStandardMaterial({
        color: roofColor(featureKey, contour.length),
        roughness: 0.92,
        metalness: 0.02,
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = 'microsoft-roof-' + featureKey;
      mesh.frustumCulled = false;
      group.add(mesh);
      return true;
    }

    function addGeometry(group, geometry, featureKey) {
      if (geometry.type === 'Polygon') return addPolygon(group, geometry.coordinates, featureKey);
      if (geometry.type === 'MultiPolygon') {
        let any = false;
        geometry.coordinates.forEach((rings, i) => { if (addPolygon(group, rings, featureKey + '-' + i)) any = true; });
        return any;
      }
      return false;
    }

    const group = new THREE.Group();
    let candidatesCount = 0, roofCount = 0;
    for (let i = 0; i < features.length; i++) {
      const feature = features[i];
      const key = String(feature.id || feature.properties?.source_feature_id || ('feature-' + i)).replace(/[^a-zA-Z0-9_-]/g, '_');
      // Fast geographic prefilter against this part's projected GLB bounds.
      const rings = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
      const coords = rings.flat();
      if (!coords.length) continue;
      const xs = [], ys = [];
      for (const c of coords) {
        const p = localPoint(c);
        xs.push(p.x); ys.push(p.y);
      }
      if (Math.max(...xs) < bounds.min.x - 8 || Math.min(...xs) > bounds.max.x + 8 ||
          Math.max(...ys) < bounds.min.y - 8 || Math.min(...ys) > bounds.max.y + 8) continue;
      candidatesCount++;
      if (addGeometry(group, feature.geometry, key)) roofCount++;
    }

    const scene = new THREE.Scene();
    scene.add(new THREE.AmbientLight(0xffffff, 1.8));
    const light = new THREE.DirectionalLight(0xffffff, 1.0);
    light.position.set(-35, -45, 90).normalize();
    scene.add(light);
    scene.add(group);
    const layerId = 'microsoft-roof-surfaces-part-' + part;
    const layer = {
      id: layerId,
      type: 'custom',
      renderingMode: '3d',
      onAdd(mapInstance, gl) {
        this.renderer = new THREE.WebGLRenderer({ canvas: mapInstance.getCanvas(), context: gl, antialias: true });
        this.renderer.autoClear = false;
        this.camera = new THREE.Camera();
        this.scene = scene;
        this.anchor = anchor;
        this.meters = meters;
      },
      render(gl, args) {
        if (!this.renderer || !group.visible) return;
        const values = args?.defaultProjectionData?.mainMatrix || args?.modelViewProjectionMatrix ||
          ((Array.isArray(args) || ArrayBuffer.isView(args)) ? args : null);
        if (!values || values.length !== 16) return;
        const projection = new THREE.Matrix4().fromArray(Array.from(values, Number));
        const transform = new THREE.Matrix4().makeTranslation(this.anchor.x, this.anchor.y, this.anchor.z)
          .scale(new THREE.Vector3(this.meters, -this.meters, this.meters));
        this.camera.projectionMatrix.copy(projection).multiply(transform);
        this.camera.projectionMatrixInverse.copy(this.camera.projectionMatrix).invert();
        this.renderer.resetState();
        this.renderer.render(this.scene, this.camera);
        this.renderer.resetState();
      }
    };
    map.addLayer(layer);
    if (map.getLayer(layerId)) {
      map.moveLayer(layerId);
    }
    group.visible = enabled;\n    return { layerIds: [layerId], group, candidateCount: candidatesCount, roofCount };
  }

  function loadModel(url) {
    return new Promise((resolve, reject) => {
      const loader = new GLTFLoader();
      loader.setMeshoptDecoder(MeshoptDecoder);
      loader.load(url, gltf => resolve(gltf), undefined, err => reject(new Error('تعذر تحميل GLB ' + url + ': ' + (err?.message || err))));
    });
  }

  function roofColor(key, complexity) {
    // Restrained roofing palette; deterministic per feature, no random colors on each load.
    const palette = [0xaaa397, 0xb9b3a7, 0x989b98, 0xc1b8a8, 0x8e9694, 0xb0a99b];
    let hash = complexity | 0;
    for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0;
    return palette[(hash >>> 0) % palette.length];
  }
})();
