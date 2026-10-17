import * as THREE from 'three';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';

export async function loadHelsinkiPhotogrammetry(scene, statusText, showError) {
  statusText.textContent = 'جارٍ تحميل مجسّم هلسنكي الحقيقي وخاماته…';
  try {
    const response = await fetch('/models/helsinki/manifest.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('ملف فهرس مجسّم هلسنكي غير موجود ضمن هذا البناء');
    const manifest = await response.json();
    const allEntries = (manifest.tiles || []).flatMap(tile => tile.objects || [])
      .filter(item => item.obj && item.mtl);
    // The archive contains an adaptive LOD tree. Loading every level at once
    // overlays the same city repeatedly and can overwhelm the browser. L16 is
    // the 250 m-scale representation intended for a playable first region.
    const preferred = allEntries.filter(item => /_L15(?:_|\.)/.test(item.obj));
    const fallback = allEntries.filter(item => /_L16(?:_|\.)/.test(item.obj));
    const entries = (preferred.length ? preferred : fallback.length ? fallback : allEntries)
      .sort((a, b) => b.bytes - a.bytes);
    const selectedLod = preferred.length ? 15 : fallback.length ? 16 : null;
    if (!entries.length) throw new Error('لم يُعثر على ملفات OBJ وMTL صالحة في المنطقة المنزّلة');

    const firstObjUrl = new URL('/' + entries[0].obj.replace(/^\/+/, ''), window.location.origin);
    const firstObjResponse = await fetch(firstObjUrl.href);
    if (!firstObjResponse.ok) throw new Error('تعذّر قراءة أول ملف OBJ لهلسنكي');
    const firstObjText = await firstObjResponse.text();
    const firstVertex = firstObjText.match(/^v\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)/m);
    if (!firstVertex) throw new Error('ملف OBJ لا يحتوي على إحداثيات رؤوس صالحة');
    const sourceOrigin = [Number(firstVertex[1]), Number(firstVertex[2]), Number(firstVertex[3])];

    const root = new THREE.Group();
    root.name = 'Helsinki-2017-Photogrammetry';
    let loaded = 0;
    let failed = 0;
    const batchSize = 12;
    for (let start = 0; start < entries.length; start += batchSize) {
      const batch = entries.slice(start, start + batchSize);
      const results = await Promise.all(batch.map(async entry => {
        try {
          const objUrl = new URL('/' + entry.obj.replace(/^\/+/, ''), window.location.origin);
          const mtlUrl = new URL(entry.mtl, objUrl);
          const materials = await new MTLLoader().loadAsync(mtlUrl.href);
          materials.preload();
          const objText = entry.obj === entries[0].obj
            ? firstObjText
            : await fetch(objUrl.href).then(result => {
                if (!result.ok) throw new Error('HTTP ' + result.status + ' reading OBJ');
                return result.text();
              });
          // Rebase large projected GIS coordinates before OBJLoader stores them
          // as Float32 values; otherwise metre-scale details collapse at 6–25 million units.
          const localObjText = objText.replace(/^v\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)(.*)$/gm,
            (_line, x, y, z, tail) => 'v ' + (Number(x) - sourceOrigin[0]) + ' ' +
              (Number(y) - sourceOrigin[1]) + ' ' + (Number(z) - sourceOrigin[2]) + tail);
          const objLoader = new OBJLoader();
          objLoader.setMaterials(materials);
          const object = objLoader.parse(localObjText);
          object.name = entry.obj;
          object.traverse(node => {
            if (node.isMesh) {
              // Textured aerial imagery already contains scene lighting; avoid expensive city-wide shadow maps.
              node.castShadow = false;
              node.receiveShadow = false;
              const mats = Array.isArray(node.material) ? node.material : [node.material];
              mats.forEach(mat => {
                if (!mat) return;
                mat.side = THREE.DoubleSide;
                if (mat.map) mat.map.colorSpace = THREE.SRGBColorSpace;
                mat.needsUpdate = true;
              });
            }
          });
          return object;
        } catch (error) {
          failed++;
          console.warn('Could not load Helsinki mesh piece:', entry.obj, error);
          return null;
        }
      }));
      results.forEach(object => { if (object) root.add(object); });
      loaded += results.filter(Boolean).length;
      statusText.textContent = 'تحميل هلسنكي · ' + loaded + ' / ' + entries.length + ' قطعة';
    }
    if (!loaded) throw new Error('فشل تحميل كل قطع المجسّم أو خاماتها');
    root.rotation.x = -Math.PI / 2;
    root.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(root);
    const center = bounds.getCenter(new THREE.Vector3());
    root.position.set(-center.x, -bounds.min.y, -center.z);
    root.updateMatrixWorld(true);
    scene.add(root);
    const finalBounds = new THREE.Box3().setFromObject(root);
    const sampleObject = root.children.find(node => node.name.includes('Tile_+019_+043_L16_000.obj')) || root.children[0];
    const sampleBounds = sampleObject ? new THREE.Box3().setFromObject(sampleObject) : finalBounds;
    const sampleCenter = sampleBounds.getCenter(new THREE.Vector3());
    const ray = new THREE.Raycaster();
    ray.set(new THREE.Vector3(sampleCenter.x, finalBounds.max.y + 100, sampleCenter.z), new THREE.Vector3(0, -1, 0));
    const hits = ray.intersectObject(root, true);
    if (hits.length) {
      root.position.x -= hits[hits.length - 1].point.x;
      root.position.y -= hits[hits.length - 1].point.y;
      root.position.z -= hits[hits.length - 1].point.z;
      root.updateMatrixWorld(true);
    }
    root.userData.spawnPosition = { x: 0, y: 0, z: 0 };
    root.userData.spawnGroundY = 0;
    const textureCount = manifest.tiles.reduce((sum, tile) => sum + (tile.textureCount || 0), 0);
    statusText.textContent = 'هلسنكي، فنلندا · مجسّم مصوّر LOD ' + (selectedLod ?? 'متاح') + ' · ' + loaded + ' قطعة · ' + entries.length + ' خامة' + (failed ? ' · تعذّر تحميل ' + failed : '');
    console.info('Loaded official Helsinki photogrammetry mesh', {
      imageryYear: manifest.imageryYear, selectedLod, loadedObjects: loaded, selectedObjects: entries.length, failedObjects: failed,
      textureCount, license: manifest.license
    });
    return root;
  } catch (error) {
    console.error('Helsinki mesh could not be loaded:', error);
    statusText.textContent = 'تعذّر تحميل مجسّم هلسنكي';
    showError('لم يتم تحميل مجسّم هلسنكي الحقيقي. لن نستبدله بمدينة كرتونية أو شوارع وهمية. تحقق من اكتمال تنزيل ملفات OBJ وMTL والخامات في بناء اللعبة.');
    return null;
  }
}
