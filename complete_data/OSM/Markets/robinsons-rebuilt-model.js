/* Independent Robinsons Place Manila rebuild.
 * A new standalone 3D mall volume is generated from the mapped mall boundary.
 * It does not use existing building meshes as geometry and never edits source layers.
 * Visual reconstruction is procedural; refine against full survey/photo coverage when available.
 */
import * as THREE from 'three';

(async function(){
 const toggle=document.getElementById('robinsons-enhancement');
 const status=document.getElementById('status'), error=document.getElementById('error');
 if(!toggle) return;
 const ID='robinsons-rebuilt-model';
 const boundaryURL=new URL('../../../ermita/maps/generated/ermita-features.geojson',import.meta.url).href;
 let map=null,ready=false,loading=false,model=null,renderer=null,camera=null,scene=null,anchor=null,scale=1,projectedScale=1;
 const say=t=>{if(status)status.textContent=t;};
 function merc(lon,lat){const R=6378137,la=Math.max(-85.05112878,Math.min(85.05112878,lat));return [R*lon*Math.PI/180,R*Math.log(Math.tan(Math.PI/4+la*Math.PI/360))];}
 function centroid(r){let a=0,x=0,y=0;for(let i=0;i<r.length-1;i++){const p=r[i],q=r[i+1],c=p[0]*q[1]-q[0]*p[1];a+=c;x+=(p[0]+q[0])*c;y+=(p[1]+q[1])*c;}if(Math.abs(a)>1e-9)return [x/(3*a),y/(3*a)];return r[0];}
 function polygonList(g){return g.type==='Polygon'?[g.coordinates]:g.coordinates;}
 function makeMesh(pos,mat){if(!pos.length)return null;const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.computeVertexNormals();const m=new THREE.Mesh(g,mat);m.frustumCulled=false;return m;}
 function quad(a,b,c,d,out){out.push(...a,...b,...c,...a,...c,...d);}
 function signTexture(){
  const c=document.createElement('canvas');c.width=1600;c.height=300;const x=c.getContext('2d');
  x.fillStyle='#b51228';x.fillRect(0,0,c.width,c.height);x.fillStyle='#f8f4e9';x.fillRect(0,0,12,c.height);x.fillRect(c.width-12,0,12,c.height);
  x.fillStyle='#a90e22';x.fillRect(22,22,252,256);x.strokeStyle='#fff';x.lineWidth=30;x.lineCap='round';x.lineJoin='round';x.beginPath();x.moveTo(88,224);x.bezierCurveTo(112,172,128,110,130,70);x.bezierCurveTo(135,32,220,38,214,87);x.bezierCurveTo(211,120,170,137,130,137);x.bezierCurveTo(160,164,190,196,222,230);x.stroke();
  x.fillStyle='#fff';x.textBaseline='middle';x.font='bold 104px Georgia,serif';x.fillText('ROBINSONS',310,112);x.font='bold 76px Georgia,serif';x.fillText('PLACE MANILA',316,216);
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;return t;
 }
 function build(ring,center){
  const origin=merc(center[0],center[1]),pts=ring.slice(0,-1).map(p=>{const q=merc(p[0],p[1]);return [q[0]-origin[0],q[1]-origin[1]];});
  if(pts.length<3)throw Error('حدود المول غير صالحة');
  const shape=new THREE.Shape();shape.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)shape.lineTo(pts[i][0],pts[i][1]);shape.closePath();
  const group=new THREE.Group();
  const concrete=new THREE.MeshStandardMaterial({color:0xd4d0c8,roughness:.84,metalness:.02});
  const cream=new THREE.MeshStandardMaterial({color:0xe7dfd0,roughness:.78});
  const glass=new THREE.MeshStandardMaterial({color:0x31596b,roughness:.22,metalness:.25,side:THREE.DoubleSide});
  const darkGlass=new THREE.MeshStandardMaterial({color:0x1d3540,roughness:.2,metalness:.35,side:THREE.DoubleSide});
  const red=new THREE.MeshStandardMaterial({color:0xb51228,roughness:.5});
  const trim=new THREE.MeshStandardMaterial({color:0xb8b6b0,roughness:.5,metalness:.2});
  // Main independent building mass; stepped volumes make the mall read as a single designed complex.
  const body=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:22,bevelEnabled:false,curveSegments:1}),concrete);body.position.z=0;group.add(body);
  const lower=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:5.2,bevelEnabled:false}),cream);lower.position.z=0.02;group.add(lower);
  // Facade bays, continuous slab lines, vertical piers and glazed shopfronts on the full perimeter.
  const windows=[],frames=[],bands=[],piers=[],storefront=[];
  for(let i=0;i<pts.length;i++){
   const a=pts[i],b=pts[(i+1)%pts.length],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);if(len<5)continue;
   // outward normal based on signed polygon area
   let area=0;for(let j=0;j<pts.length;j++){const p=pts[j],q=pts[(j+1)%pts.length];area+=p[0]*q[1]-q[0]*p[1];}
   const nx=area>0?dy/len:-dy/len,ny=area>0?-dx/len:dx/len;
   const bays=Math.max(1,Math.min(70,Math.floor(len/4.2))),bw=len/bays;
   const wall=(t0,t1,z0,z1,off,out)=>{const p=[a[0]+dx*t0+nx*off,a[1]+dy*t0+ny*off],q=[a[0]+dx*t1+nx*off,a[1]+dy*t1+ny*off];quad([p[0],p[1],z0],[q[0],q[1],z0],[q[0],q[1],z1],[p[0],p[1],z1],out);};
   // transparent retail level, repeated shopfronts
   for(let bay=0;bay<bays;bay++){const t0=(bay+.06)/bays,t1=(bay+.94)/bays;wall(t0,t1,.65,4.25,.24,storefront);wall(t0,t1,5.9,8.3,.16,windows);}
   for(const z of [5.25,8.65,12.05,15.45,18.85,21.95])wall(0,1,z,z+.18,.14,bands);
   for(let bay=0;bay<=bays;bay++){if(bay%3!==0)continue;const t=Math.min(.999,Math.max(.001,bay/bays));wall(t-.012,t+.012,5.4,21.8,.19,piers);}
   for(let floor=0;floor<4;floor++){const z=9+floor*3.25;for(let bay=0;bay<bays;bay++){const t0=(bay+.2)/bays,t1=(bay+.8)/bays;wall(t0,t1,z,z+1.75,.21,windows);wall(t0,t1,z-.06,z,.24,frames);wall(t0,t1,z+1.75,z+1.81,.24,frames);}}
  }
  for(const [p,m] of [[storefront,darkGlass],[windows,glass],[frames,trim],[bands,cream],[piers,cream]]){const mesh=makeMesh(p,m);if(mesh)group.add(mesh);}
  // Broad entrance canopy and red fascia on the longest mapped frontage.
  let best=null;for(let i=0;i<pts.length;i++){const a=pts[i],b=pts[(i+1)%pts.length],len=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!best||len>best.len)best={a,b,len};}
  if(best&&best.len>20){
   const dx=(best.b[0]-best.a[0])/best.len,dy=(best.b[1]-best.a[1])/best.len, nx=dy,ny=-dx, width=Math.min(best.len*.7,48),cx=(best.a[0]+best.b[0])/2,cy=(best.a[1]+best.b[1])/2;
   const sx=cx+nx*.36,sy=cy+ny*.36,half=width/2,z0=23.1,z1=27.9;
   const signGeo=new THREE.BufferGeometry();
   signGeo.setAttribute('position',new THREE.Float32BufferAttribute([
    sx-dx*half,sy-dy*half,z0, sx+dx*half,sy+dy*half,z0,
    sx+dx*half,sy+dy*half,z1, sx-dx*half,sy-dy*half,z1
   ],3));
   signGeo.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,1,1,0,1],2));signGeo.setIndex([0,1,2,0,2,3]);signGeo.computeVertexNormals();
   const signMat=new THREE.MeshStandardMaterial({map:signTexture(),roughness:.55,metalness:0,side:THREE.DoubleSide});
   const sign=new THREE.Mesh(signGeo,signMat);sign.frustumCulled=false;group.add(sign);
   const canopyGeo=new THREE.BoxGeometry(width*.72,3.2,.75);const canopy=new THREE.Mesh(canopyGeo,red);canopy.position.set(cx+nx*2.1,cy+ny*2.1,5.0);canopy.rotation.z=Math.atan2(dy,dx);group.add(canopy);
  }
  // Roof parapet and rooftop mechanical blocks give the silhouette a finished commercial-roof profile.
  const roof=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.8,bevelEnabled:false}),cream);roof.position.z=22;group.add(roof);
  const boxMat=new THREE.MeshStandardMaterial({color:0xb9b6ad,roughness:.9});
  const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  for(let i=0;i<6;i++){const w=Math.max(3,(maxX-minX)*(.035+(i%2)*.012)),d=Math.max(3,(maxY-minY)*.035),h=1.8+(i%3)*.8;const b=new THREE.Mesh(new THREE.BoxGeometry(w,d,h),boxMat);b.position.set(minX+(maxX-minX)*(0.18+i*.125),minY+(maxY-minY)*(.28+(i%2)*.35),22.8+h/2);group.add(b);}
  group.traverse(o=>{if(o.isMesh){o.frustumCulled=false;o.renderOrder=10;}});return group;
 }
 async function ensure(){
  if(ready||loading)return;loading=true;
  try{
   map=window.adamCityMap;if(!map||!map.isStyleLoaded())throw Error('الخريطة لم تجهز بعد');
   const res=await fetch(boundaryURL,{cache:'no-cache'});if(!res.ok)throw Error('حدود المول HTTP '+res.status);const data=await res.json();
   const features=data.features||[];
   const mall=features.find(f=>{const p=f.properties||{},t=p.tags||{},id=String(p.osm_feature_id||p.osm_id||p['@id']||(p.type&&p.id!==undefined?p.type+'/'+p.id:'')).toLowerCase(),names=[t.name,p.name,p.name_en,p['name:en'],p.label].filter(Boolean).join(' ').toLowerCase();return f.geometry&&(f.geometry.type==='Polygon'||f.geometry.type==='MultiPolygon')&&(id==='way/48894714'||id==='48894714'||(names.includes('robinsons')&&(names.includes('manila')||names.includes('place'))));});
   if(!mall)throw Error('لم يُعثر على حدود Robinsons Place Manila');
   const polys=polygonList(mall.geometry).sort((a,b)=>Math.abs(areaRing(b[0]))-Math.abs(areaRing(a[0])));const ring=polys[0]?.[0];if(!ring||ring.length<4)throw Error('مضلع المول غير صالح');
   const center=centroid(ring);model=build(ring,center);anchor=maplibregl.MercatorCoordinate.fromLngLat({lng:center[0],lat:center[1]},0);scale=anchor.meterInMercatorCoordinateUnits();projectedScale=scale*Math.cos(center[1]*Math.PI/180);model.visible=toggle.checked;
   map.addLayer({id:ID,type:'custom',renderingMode:'3d',onAdd(mapInstance,gl){renderer=new THREE.WebGLRenderer({canvas:mapInstance.getCanvas(),context:gl,antialias:true});renderer.autoClear=false;camera=new THREE.Camera();scene=new THREE.Scene();scene.add(new THREE.AmbientLight(0xffffff,2.1));const l=new THREE.DirectionalLight(0xffffff,2.0);l.position.set(-40,-60,100).normalize();scene.add(l);scene.add(model);},render(gl,args){if(!renderer||!model||!model.visible)return;const matrix=args?.defaultProjectionData?.mainMatrix;if(!matrix)return;const values=Object.values(matrix);if(values.length!==16||values.some(v=>!Number.isFinite(Number(v))))return;const projection=new THREE.Matrix4().fromArray(values.map(Number)),transform=new THREE.Matrix4().makeTranslation(anchor.x,anchor.y,anchor.z).scale(new THREE.Vector3(projectedScale,-projectedScale,scale));camera.projectionMatrix.copy(projection).multiply(transform);camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();renderer.resetState();renderer.render(scene,camera);renderer.resetState();}});
   map.moveLayer(ID);ready=true;loading=false;map.triggerRepaint();say('تم إنشاء نموذج Robinsons مستقل على الخريطة من حدود المول؛ فعّل/أخفِ الطبقة من مربع الاختيار.');
  }catch(e){loading=false;if(error){error.style.display='block';error.textContent='فشل نموذج Robinsons المستقل: '+(e?.message||e);}say('تعذر تحميل نموذج Robinsons المستقل.');}
 }
 function areaRing(r){let a=0;for(let i=0;i<r.length-1;i++)a+=r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1];return Math.abs(a);}
 toggle.addEventListener('change',async()=>{if(toggle.checked){if(!ready)await ensure();else if(model){model.visible=true;map.triggerRepaint();}}else if(model){model.visible=false;map.triggerRepaint();say('تم إخفاء نموذج Robinsons المستقل.');}});
})();
