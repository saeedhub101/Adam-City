/* Robinsons Place Manila facade-detail overlay for Adam-City.
 * Uses the exact OSM mall boundary (way/48894714) and authoritative OpenFreeMap-derived
 * building polygons inside it. It adds only thin facade details; it does not replace,
 * translate, resize, or recolor the authoritative OpenFreeMap building meshes.
 */
import * as THREE from 'three';

(async function initRobinsonsFacadeDetails(){
  const checkbox = document.getElementById('robinsons-enhancement');
  const status = document.getElementById('status');
  const errorBox = document.getElementById('error');
  if (!checkbox) return;

  const MAP_ID = 'robinsons-place-facade-details';
  const mallBoundaryUrl = new URL('../../../ermita/maps/generated/ermita-features.geojson', import.meta.url).href;
  const buildingDetailsUrl = new URL('../../../ermita/maps/generated/ermita-building-footprints.geojson', import.meta.url).href;
  let map = null, loading = false, ready = false, model = null;
  let renderer = null, camera = null, scene = null, anchor = null;
  let meterScale = 1, projectedMeterScale = 1;

  const fail = (err) => {
    loading = false;
    if (errorBox) {
      errorBox.style.display = 'block';
      errorBox.textContent = 'Robinsons Place facade overlay: ' + (err?.message || String(err));
    }
    if (status) status.textContent = 'تعذر تجهيز تفاصيل واجهة Robinsons Place Manila.';
  };
  const num = (value) => {
    if (value === null || value === undefined || value === '') return NaN;
    const n = Number(String(value).replace(/\s*m$/i, ''));
    return Number.isFinite(n) ? n : NaN;
  };
  const tagsOf = (feature) => feature?.properties?.tags || {};
  const idOf = (feature) => {
    const p = feature?.properties || {};
    return p.osm_feature_id || (p.type && p.id !== undefined ? p.type + '/' + p.id : '');
  };
  const isPolygon = (g) => g && (g.type === 'Polygon' || g.type === 'MultiPolygon');
  const ringsOf = (g) => g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  const outerRingsOf = (g) => ringsOf(g).map(poly => poly?.[0]).filter(ring => Array.isArray(ring) && ring.length >= 4);

  function insideRing(point, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      const crosses = ((yi > point[1]) !== (yj > point[1])) &&
        (point[0] < (xj - xi) * (point[1] - yi) / ((yj - yi) || 1e-15) + xi);
      if (crosses) inside = !inside;
    }
    return inside;
  }
  function pointInPolygon(point, polygonCoordinates) {
    if (!polygonCoordinates?.length || !insideRing(point, polygonCoordinates[0])) return false;
    for (let i = 1; i < polygonCoordinates.length; i++) {
      if (insideRing(point, polygonCoordinates[i])) return false;
    }
    return true;
  }
  function pointInGeometry(point, geometry) {
    if (!isPolygon(geometry)) return false;
    if (geometry.type === 'Polygon') return pointInPolygon(point, geometry.coordinates);
    return geometry.coordinates.some(poly => pointInPolygon(point, poly));
  }
  function polygonCentroid(ring) {
    let area2 = 0, cx = 0, cy = 0;
    for (let i = 0; i < ring.length - 1; i++) {
      const [x1, y1] = ring[i], [x2, y2] = ring[i + 1];
      const cross = x1 * y2 - x2 * y1;
      area2 += cross;
      cx += (x1 + x2) * cross;
      cy += (y1 + y2) * cross;
    }
    if (Math.abs(area2) > 1e-9) return [cx / (3 * area2), cy / (3 * area2)];
    const pts = ring.slice(0, -1);
    return [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];
  }
  function mercatorXY(lon, lat) {
    const R = 6378137;
    const safeLat = Math.max(-85.05112878, Math.min(85.05112878, lat));
    return [R * lon * Math.PI / 180, R * Math.log(Math.tan(Math.PI / 4 + safeLat * Math.PI / 360))];
  }
  function polygonAreaMeters(ring) {
    const p = ring.map(([lon, lat]) => mercatorXY(lon, lat));
    let area = 0;
    for (let i = 0; i < p.length - 1; i++) area += p[i][0] * p[i + 1][1] - p[i + 1][0] * p[i][1];
    return Math.abs(area) / 2;
  }
  function addQuad(target, a, b, c, d) {
    target.push(...a, ...b, ...c, ...a, ...c, ...d);
  }
  function addWallQuad(target, a, b, z0, z1, nx, ny, offset) {
    const ax = a[0] + nx * offset, ay = a[1] + ny * offset;
    const bx = b[0] + nx * offset, by = b[1] + ny * offset;
    addQuad(target, [ax, ay, z0], [bx, by, z0], [bx, by, z1], [ax, ay, z1]);
  }
  function meshFromPositions(positions, material) {
    if (!positions.length) return null;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.computeVertexNormals();
    return new THREE.Mesh(geometry, material);
  }
  function simplifyRing(ring) {
    const pts = ring.slice(0, -1).map(([lon, lat]) => mercatorXY(lon, lat));
    if (pts.length < 3) return [];
    const out = [];
    for (let i = 0; i < pts.length; i++) {
      const prev = pts[(i + pts.length - 1) % pts.length];
      const cur = pts[i], next = pts[(i + 1) % pts.length];
      const ax = cur[0] - prev[0], ay = cur[1] - prev[1];
      const bx = next[0] - cur[0], by = next[1] - cur[1];
      const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
      if (la < 1.1 || lb < 1.1) continue;
      const cross = Math.abs(ax * by - ay * bx) / Math.max(la * lb, 1e-9);
      if (cross < 0.035 && (ax * bx + ay * by) > 0) continue;
      out.push(cur);
    }
    return out.length >= 3 ? out : pts;
  }
  function createFacadeGeometry(features, originXY) {
    const glassPositions = [], framePositions = [], bandPositions = [], pierPositions = [];
    let detailedBuildings = 0, windows = 0;
    for (const feature of features) {
      const geometry = feature.geometry;
      const tags = tagsOf(feature);
      const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
      const explicitHeight = num(feature.properties?.basemap_render_height ?? feature.properties?.basemap_properties?.render_height ?? feature.properties?.adam_height_m ?? feature.properties?.render_height ?? feature.properties?.height ?? tags.height ?? tags['building:height']);
      const explicitLevels = num(tags['building:levels'] ?? tags.levels ?? feature.properties?.building_levels ?? feature.properties?.basemap_properties?.building_levels);
      if (!Number.isFinite(explicitHeight) && !Number.isFinite(explicitLevels)) continue;
      const rings = polygons.map(poly => poly[0]).filter(r => r?.length >= 4);
      if (!rings.length) continue;
      const height = Number.isFinite(explicitHeight) && explicitHeight > 2
        ? explicitHeight
        : Math.max(3.2, explicitLevels * 3.35);
      const levels = Math.max(1, Math.min(45, Math.round(Number.isFinite(explicitLevels) && explicitLevels > 0 ? explicitLevels : height / 3.35)));
      const minHeight = Math.max(0, num(feature.properties?.basemap_render_min_height ?? feature.properties?.basemap_properties?.render_min_height ?? tags.min_height ?? (num(tags['building:min_level']) * 3.2)) || 0);
      const floorHeight = Math.max(2.6, Math.min(5.2, (height - minHeight) / levels));
      let addedForFeature = false;

      for (const rawRing of rings) {
        const ring = simplifyRing(rawRing).map(([x, y]) => [x - originXY[0], y - originXY[1]]);
        if (ring.length < 3) continue;
        let area2 = 0;
        for (let i = 0; i < ring.length; i++) {
          const a = ring[i], b = ring[(i + 1) % ring.length];
          area2 += a[0] * b[1] - b[0] * a[1];
        }
        const ccw = area2 > 0;
        for (let i = 0; i < ring.length; i++) {
          const a = ring[i], b = ring[(i + 1) % ring.length];
          const dx = b[0] - a[0], dy = b[1] - a[1];
          const length = Math.hypot(dx, dy);
          if (length < 2.6) continue;
          const nx = ccw ? dy / length : -dy / length;
          const ny = ccw ? -dx / length : dx / length;
          const bays = Math.max(1, Math.min(80, Math.floor(length / 3.4)));
          const bayWidth = length / bays;
          const wallBase = minHeight;
          const top = Math.max(wallBase + floorHeight, height);

          for (let floor = 0; floor < levels; floor++) {
            const zFloor = wallBase + floor * floorHeight;
            const zTop = Math.min(top, zFloor + floorHeight);
            if (zTop - zFloor < 1.8) continue;
            // Continuous thin slab line, set just outside the source footprint.
            addWallQuad(bandPositions, a, b, zFloor + 0.12, zFloor + 0.22, nx, ny, 0.10);
            const windowHeight = Math.min(1.85, floorHeight * 0.58);
            const sill = Math.max(0.62, floorHeight * 0.18);
            const z0 = zFloor + sill;
            const z1 = Math.min(zTop - 0.22, z0 + windowHeight);
            if (z1 <= z0 + 0.3) continue;
            for (let bay = 0; bay < bays; bay++) {
              const t0 = (bay + 0.19) / bays, t1 = (bay + 0.81) / bays;
              const p0 = [a[0] + dx * t0, a[1] + dy * t0];
              const p1 = [a[0] + dx * t1, a[1] + dy * t1];
              addWallQuad(glassPositions, p0, p1, z0, z1, nx, ny, 0.17);
              windows++;
              // Fine perimeter frame around each glass panel.
              const frameWidth = Math.min(0.055, bayWidth * 0.035);
              addWallQuad(framePositions, p0, p1, z0, z0 + frameWidth, nx, ny, 0.205);
              addWallQuad(framePositions, p0, p1, z1 - frameWidth, z1, nx, ny, 0.205);
              const left0 = [p0[0] - dx / length * frameWidth, p0[1] - dy / length * frameWidth];
              const left1 = [p0[0] + dx / length * frameWidth, p0[1] + dy / length * frameWidth];
              const right0 = [p1[0] - dx / length * frameWidth, p1[1] - dy / length * frameWidth];
              const right1 = [p1[0] + dx / length * frameWidth, p1[1] + dy / length * frameWidth];
              addWallQuad(framePositions, left0, left1, z0, z1, nx, ny, 0.207);
              addWallQuad(framePositions, right0, right1, z0, z1, nx, ny, 0.207);
            }
            // Vertical facade piers every fourth bay create a more believable podium/tower rhythm.
            for (let bay = 0; bay <= bays; bay += 4) {
              const t = bay / bays;
              const p0 = [a[0] + dx * Math.max(0, t - 0.018), a[1] + dy * Math.max(0, t - 0.018)];
              const p1 = [a[0] + dx * Math.min(1, t + 0.018), a[1] + dy * Math.min(1, t + 0.018)];
              addWallQuad(pierPositions, p0, p1, zFloor + 0.05, zTop - 0.04, nx, ny, 0.125);
            }
          }
          // Roof parapet/rim detail, not a replacement roof or a change to the silhouette.
          addWallQuad(bandPositions, a, b, top - 0.18, top - 0.06, nx, ny, 0.12);
          addedForFeature = true;
        }
      }
      if (addedForFeature) detailedBuildings++;
    }
    const materials = {
      glass: new THREE.MeshStandardMaterial({color: 0x426579, roughness: 0.23, metalness: 0.24, side: THREE.DoubleSide}),
      frame: new THREE.MeshStandardMaterial({color: 0xb9c1c4, roughness: 0.48, metalness: 0.28, side: THREE.DoubleSide}),
      bands: new THREE.MeshStandardMaterial({color: 0xd0c8b9, roughness: 0.78, metalness: 0.02, side: THREE.DoubleSide}),
      piers: new THREE.MeshStandardMaterial({color: 0xe0d8c9, roughness: 0.83, metalness: 0.01, side: THREE.DoubleSide})
    };
    const group = new THREE.Group();
    for (const [positions, material] of [
      [bandPositions, materials.bands],
      [pierPositions, materials.piers],
      [glassPositions, materials.glass],
      [framePositions, materials.frame]
    ]) {
      const mesh = meshFromPositions(positions, material);
      if (mesh) { mesh.frustumCulled = false; group.add(mesh); }
    }
    return {group, detailedBuildings, windows};
  }

  function addRobinsonsSign(group, features, originXY) {
    // Realistic storefront sign panel: branded red fascia with a white Robinsons wordmark.
    // It is an overlay only; no source building geometry is moved or replaced.
    let best = null;
    for (const feature of features) {
      const g = feature.geometry;
      const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
      for (const poly of polys) {
        const ring = poly[0];
        if (!ring || ring.length < 4) continue;
        for (let i = 0; i < ring.length - 1; i++) {
          const a0 = mercatorXY(ring[i][0], ring[i][1]);
          const b0 = mercatorXY(ring[i+1][0], ring[i+1][1]);
          const len = Math.hypot(b0[0]-a0[0], b0[1]-a0[1]);
          if (!best || len > best.len) best = {a:a0,b:b0,len};
        }
      }
    }
    if (!best || best.len < 12 || typeof document === 'undefined') return;
    const dx = (best.b[0]-best.a[0])/best.len, dy=(best.b[1]-best.a[1])/best.len;
    const nx = dy, ny = -dx;
    const width = Math.min(25, best.len*0.66), height = 2.2;
    const midX=(best.a[0]+best.b[0])/2-originXY[0], midY=(best.a[1]+best.b[1])/2-originXY[1];
    const cx=midX+nx*0.34, cy=midY+ny*0.34, z0=3.3, z1=z0+height;
    const half=width/2;
    const pts=[
      [cx-dx*half,cy-dy*half,z0],[cx+dx*half,cy+dy*half,z0],
      [cx+dx*half,cy+dy*half,z1],[cx-dx*half,cy-dy*half,z1]
    ];
    const canvas=document.createElement('canvas'); canvas.width=1024; canvas.height=256;
    const ctx=canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle='#bd1727'; ctx.fillRect(0,0,1024,256);
    ctx.fillStyle='#f8f4ec'; ctx.fillRect(0,0,1024,12);
    ctx.fillRect(0,244,1024,12);
    // A compact white mall mark and the recognizable Robinsons wordmark treatment.
    ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(105,128,63,0,Math.PI*2); ctx.fill();
    ctx.fillStyle='#bd1727'; ctx.font='bold 100px Arial, sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText('R',105,129);
    ctx.fillStyle='#fff'; ctx.textAlign='left'; ctx.font='700 91px Arial, sans-serif'; ctx.fillText('ROBINSONS',195,116);
    ctx.font='600 36px Arial, sans-serif'; ctx.letterSpacing='9px'; ctx.fillText('PLACE MANILA',201,190);
    const texture=new THREE.CanvasTexture(canvas); texture.colorSpace=THREE.SRGBColorSpace; texture.anisotropy=4;
    const material=new THREE.MeshStandardMaterial({map:texture,roughness:0.62,metalness:0.02,side:THREE.DoubleSide});
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.Float32BufferAttribute([...pts[0],...pts[1],...pts[2],...pts[0],...pts[2],...pts[3]],3));
    geometry.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,1,1,0,0,1,1,0,1],2));
    geometry.computeVertexNormals();
    const sign=new THREE.Mesh(geometry,material); sign.frustumCulled=false; group.add(sign);
  }

  async function ensureLayer() {
    if (ready || loading) return;
    loading = true;
    try {
      map = window.adamCityMap;
      if (!map || !map.isStyleLoaded()) throw new Error('الخريطة لم تجهز بعد؛ أعد تفعيل الخيار بعد تحميلها.');
      if (map.getLayer(MAP_ID)) map.removeLayer(MAP_ID);

      const [mallResponse, buildingResponse] = await Promise.all([
        fetch(mallBoundaryUrl, {cache: 'no-cache'}),
        fetch(buildingDetailsUrl, {cache: 'no-cache'})
      ]);
      if (!mallResponse.ok) throw new Error('Mall boundary HTTP ' + mallResponse.status);
      if (!buildingResponse.ok) throw new Error('Building details HTTP ' + buildingResponse.status);
      const [mallData, buildingData] = await Promise.all([mallResponse.json(), buildingResponse.json()]);
      const mall = (mallData.features || []).find(f =>
        isPolygon(f.geometry) &&
        (idOf(f) === 'way/48894714' ||
         (String(tagsOf(f).name || '').toLowerCase() === 'robinsons manila' && tagsOf(f).shop === 'mall'))
      );
      if (!mall) throw new Error('لم أجد مضلع Robinsons Manila (OSM way/48894714) في ermita-features.geojson.');
      const mallRings = ringsOf(mall.geometry);
      const outer = mallRings[0]?.[0];
      if (!outer || outer.length < 4) throw new Error('حدود Robinsons Manila لا تحتوي على مضلع صالح.');
      const center = polygonCentroid(outer);
      const originXY = mercatorXY(center[0], center[1]);
      const selected = (buildingData.features || []).filter(f => {
        if (!isPolygon(f.geometry)) return false;
        const tags = tagsOf(f);
        const p = f.properties || {};
        if (!(Number.isFinite(num(p.basemap_render_height ?? p.basemap_properties?.render_height ?? p.adam_height_m ?? p.render_height ?? p.height ?? tags.height)) || Number.isFinite(num(tags['building:levels'] ?? p.building_levels)))) return false;
        const polygonRings = outerRingsOf(f.geometry);
        if (!polygonRings.length) return false;
        const ring = polygonRings[0];
        const centerPoint = polygonCentroid(ring);
        return pointInGeometry(centerPoint, mall.geometry) && polygonAreaMeters(ring) >= 28;
      });
      if (!selected.length) throw new Error('لم أجد بصمات مبانٍ داخل حدود Robinsons Manila؛ لم يتم إنشاء هندسة بديلة.');
      const built = createFacadeGeometry(selected, originXY);
      addRobinsonsSign(built.group, selected, originXY);
      if (!built.detailedBuildings || !built.group.children.length) {
        throw new Error('لم تتوفر ارتفاعات أو مستويات مصدرية كافية لإنشاء تفاصيل الواجهات؛ لم يتم تغيير المباني الأصلية.');
      }
      const anchorLat = center[1];
      anchor = maplibregl.MercatorCoordinate.fromLngLat({lng: center[0], lat: center[1]}, 0);
      meterScale = anchor.meterInMercatorCoordinateUnits();
      projectedMeterScale = meterScale * Math.cos(anchorLat * Math.PI / 180);
      model = built.group;
      model.visible = !!checkbox.checked;

      const layer = {
        id: MAP_ID,
        type: 'custom',
        renderingMode: '3d',
        onAdd(mapInstance, gl) {
          renderer = new THREE.WebGLRenderer({canvas: mapInstance.getCanvas(), context: gl, antialias: true});
          renderer.autoClear = false;
          camera = new THREE.Camera();
          scene = new THREE.Scene();
          scene.add(new THREE.AmbientLight(0xffffff, 1.9));
          const keyLight = new THREE.DirectionalLight(0xffffff, 1.65);
          keyLight.position.set(-35, -45, 90).normalize();
          scene.add(keyLight);
          scene.add(model);
        },
        render(gl, args) {
          if (!renderer || !model || !model.visible) return;
          const mainMatrix = args?.defaultProjectionData?.mainMatrix;
          if (!mainMatrix) return;
          const values = Object.values(mainMatrix);
          if (values.length !== 16 || values.some(v => !Number.isFinite(Number(v)))) return;
          const projection = new THREE.Matrix4().fromArray(values.map(Number));
          const transform = new THREE.Matrix4().makeTranslation(anchor.x, anchor.y, anchor.z)
            .scale(new THREE.Vector3(projectedMeterScale, -projectedMeterScale, meterScale));
          camera.projectionMatrix.copy(projection).multiply(transform);
          camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
          renderer.resetState();
          renderer.render(scene, camera);
          renderer.resetState();
        }
      };
      map.addLayer(layer);
      if (map.getLayer(MAP_ID)) map.moveLayer(MAP_ID);
      ready = true;
      loading = false;
      if (status) status.textContent = 'Robinsons Place Manila: تفاصيل واجهات مضافة إلى ' + built.detailedBuildings +
        ' مبنى/جزء، ونوافذ إجرائية=' + built.windows + '. هندسة المصدر الأصلية محفوظة.';
      map.triggerRepaint();
    } catch (err) {
      fail(err);
    }
  }

  checkbox.addEventListener('change', async () => {
    if (checkbox.checked) {
      if (!ready) await ensureLayer();
      else if (model && map) { model.visible = true; map.triggerRepaint(); }
    } else if (model && map) {
      model.visible = false;
      map.triggerRepaint();
      if (status) status.textContent = 'تم إخفاء تفاصيل Robinsons Place Manila؛ المباني الأصلية لم تتغير.';
    }
  });
})();