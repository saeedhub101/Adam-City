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
    const preferred = allEntries.filter(item => /_L16(?:_|\.)/.test(item.obj));
    const fallback = allEntries.filter(item => /_L15(?:_|\.)/.test(item.obj));
    const entries = (preferred.length ? preferred : fallback.length ? fallback : allEntries)
      .sort((a, b) => b.bytes - a.bytes);
    const selectedLod = preferred.length ? 16 : fallback.length ? 15 : null;
    if (!entries.length) throw new Error('لم يُعثر على ملفات OBJ وMTL صالحة في المنطقة المنزّلة');

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
          const objLoader = new OBJLoader();
          objLoader.setMaterials(materials);
          const object = await objLoader.loadAsync(objUrl.href);
          object.traverse(node => {
            if (node.isMesh) {
              node.castShadow = true;
              node.receiveShadow = true;
              const mats = Array.isArray(node.material) ? node.material : [node.material];
              mats.forEach(mat => { if (mat?.map) mat.map.colorSpace = THREE.SRGBColorSpace; });
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
