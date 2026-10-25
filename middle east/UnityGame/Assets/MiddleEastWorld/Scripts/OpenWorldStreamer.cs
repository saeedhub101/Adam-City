using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

namespace MiddleEastWorld
{
    [Serializable] public class ChunkManifest { public string region; public double tile_degrees; public ChunkLayer buildings; public ChunkLayer streets; public ChunkLayer[] unused; public ChunkManifestLayers layers; }
    [Serializable] public class ChunkManifestLayers { public ChunkLayer buildings; public ChunkLayer streets; }
    [Serializable] public class ChunkLayer { public int features; public ChunkInfo[] chunks; }
    [Serializable] public class ChunkInfo { public string tile; public string file; public int features; public long bytes; }
    [Serializable] public class ChunkFeatures<T> { public T[] features; }
    [Serializable] public class RuntimeBuilding { public string id,name,material; public float height; public int levels; public double[][] ring; }
    [Serializable] public class RuntimeStreet { public string name,highway; public double[][] points; }

    public sealed class OpenWorldStreamer : MonoBehaviour
    {
        [Header("Region")]
        public string region = "Jordan";
        public Transform player;
        public double originLon = 35.91, originLat = 31.95;
        [Header("World streaming")]
        [Range(1,5)] public int tileRadius = 2;
        public float tileDegrees = 0.02f;
        public int maxBuildingsPerChunk = 10000;
        public bool streetLabels = true;
        readonly HashSet<string> loaded = new HashSet<string>();
        readonly Dictionary<string,ChunkInfo> buildingIndex = new Dictionary<string,ChunkInfo>();
        readonly Dictionary<string,ChunkInfo> streetIndex = new Dictionary<string,ChunkInfo>();
        string basePath;
        bool ready;
        GameObject buildingsRoot, streetsRoot;
        GUIStyle guiStyle;
        double lon0, lat0;

        void Start()
        {
            SetRegion(region);
            if (!player) { var p=GameObject.Find("Player"); if(p) player=p.transform; }
            basePath=Path.Combine(Application.streamingAssetsPath,"MiddleEastWorld/"+region+"/");
            StartCoroutine(LoadManifest());
        }

        public void SetRegion(string value)
        {
            region=value=="Palestine"?"Palestine":"Jordan";
            originLon=region=="Jordan"?35.91:35.20;
            originLat=region=="Jordan"?31.95:31.90;
            lon0=originLon;lat0=originLat;
        }

        IEnumerator ReadText(string path, Action<string> callback)
        {
            string uri=path;
            if(!uri.Contains("://")) uri="file://"+uri;
            using(var req=UnityWebRequest.Get(uri))
            {
                yield return req.SendWebRequest();
                callback(req.result==UnityWebRequest.Result.Success?req.downloadHandler.text:null);
            }
        }

        IEnumerator LoadManifest()
        {
            string json=null;
            yield return ReadText(basePath+"manifest.json",s=>json=s);
            if(string.IsNullOrEmpty(json))
            {
                Debug.LogError("Missing MiddleEastWorld/"+region+"/manifest.json. Generate chunks with tools/prepare_unity_data.py and copy BuildData into Assets/StreamingAssets/MiddleEastWorld/.");
                yield break;
            }
            var manifest=JsonUtility.FromJson<ChunkManifest>(json);
            if(manifest==null || manifest.layers==null) { Debug.LogError("Invalid region manifest: "+region); yield break; }
            Index(manifest.layers.buildings,buildingIndex);
            Index(manifest.layers.streets,streetIndex);
            buildingsRoot=new GameObject("Streamed Buildings — "+region);
            streetsRoot=new GameObject("Streamed Streets — "+region);
            ready=true;
            Debug.Log("World streamer ready: "+region+"; "+buildingIndex.Count+" building chunks; "+streetIndex.Count+" street chunks.");
            RefreshTiles();
        }

        void Index(ChunkLayer layer,Dictionary<string,ChunkInfo> index)
        {
            if(layer==null||layer.chunks==null)return;
            foreach(var c in layer.chunks) if(c!=null&&!string.IsNullOrEmpty(c.tile)) index[c.tile]=c;
        }

        void Update()
        {
            if(ready && player && Time.frameCount%20==0) RefreshTiles();
        }

        void RefreshTiles()
        {
            double lon=lon0+playerOffsetX()/ (111319.490793*Math.Cos(lat0*Math.PI/180));
            double lat=lat0+playerOffsetZ()/111319.490793;
            int tx=(int)Math.Floor(lon/tileDegrees), ty=(int)Math.Floor(lat/tileDegrees);
            for(int x=-tileRadius;x<=tileRadius;x++)
                for(int y=-tileRadius;y<=tileRadius;y++)
                {
                    string key=(tx+x)+"_"+(ty+y);
                    if(loaded.Add(key))
                    {
                        if(buildingIndex.TryGetValue(key,out var b)) StartCoroutine(LoadBuildingChunk(b));
                        if(streetIndex.TryGetValue(key,out var s)) StartCoroutine(LoadStreetChunk(s));
                    }
                }
        }

        float playerOffsetX(){return player?player.position.x:0;}
        float playerOffsetZ(){return player?player.position.z:0;}

        IEnumerator LoadBuildingChunk(ChunkInfo chunk)
        {
            string json=null; yield return ReadText(basePath+chunk.file,s=>json=s);
            if(string.IsNullOrEmpty(json)){Debug.LogWarning("Building chunk unavailable: "+chunk.file);yield break;}
            var data=JsonUtility.FromJson<ChunkFeatures<RuntimeBuilding>>(json);
            if(data==null||data.features==null)yield break;
            int count=0;
            foreach(var b in data.features)
            {
                if(count++>=maxBuildingsPerChunk)break;
                if(b.ring==null||b.ring.Length<4)continue;
                var points=new List<Vector2>(b.ring.Length);
                foreach(var q in b.ring){if(q==null||q.Length<2)continue;var p=Project(q[0],q[1]);points.Add(new Vector2(p.x,p.z));}
                if(points.Count>3&&(points[0]-points[points.Count-1]).sqrMagnitude<.01f)points.RemoveAt(points.Count-1);
                var mesh=Extrude(points,Mathf.Clamp(b.height,2.5f,250f));if(!mesh)continue;
                var go=new GameObject(string.IsNullOrEmpty(b.name)?"Building "+b.id:b.name);
                go.transform.SetParent(buildingsRoot.transform,false);
                go.AddComponent<MeshFilter>().sharedMesh=mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial=BuildingMaterial(b.material);
                var collider=go.AddComponent<MeshCollider>();collider.sharedMesh=mesh;
                if(count%250==0)yield return null;
            }
        }

        IEnumerator LoadStreetChunk(ChunkInfo chunk)
        {
            string json=null;yield return ReadText(basePath+chunk.file,s=>json=s);
            if(string.IsNullOrEmpty(json))yield break;
            var data=JsonUtility.FromJson<ChunkFeatures<RuntimeStreet>>(json);
            if(data==null||data.features==null)yield break;
            int n=0;
            foreach(var s in data.features)
            {
                if(s.points==null||s.points.Length<2)continue;
                var go=new GameObject(string.IsNullOrEmpty(s.name)?"Street":s.name);go.transform.SetParent(streetsRoot.transform,false);
                var lr=go.AddComponent<LineRenderer>();lr.useWorldSpace=false;lr.positionCount=s.points.Length;
                for(int i=0;i<s.points.Length;i++)lr.SetPosition(i,Project(s.points[i][0],s.points[i][1])+Vector3.up*.035f);
                lr.widthMultiplier=WidthFor(s.highway);lr.material=new Material(Shader.Find("Sprites/Default"));
                lr.startColor=lr.endColor=ColorForRoad(s.highway);
                if(streetLabels&&!string.IsNullOrEmpty(s.name))
                {
                    int mid=s.points.Length/2;var p=Project(s.points[mid][0],s.points[mid][1]);
                    var label=new GameObject("Street label — "+s.name);label.transform.SetParent(streetsRoot.transform,false);label.transform.position=p+Vector3.up*2.2f;
                    var tm=label.AddComponent<TextMesh>();tm.text=s.name;tm.anchor=TextAnchor.MiddleCenter;tm.alignment=TextAlignment.Center;tm.fontSize=36;tm.characterSize=.16f;tm.color=Color.white;
                    label.AddComponent<FaceCamera>();
                }
                if(++n%200==0)yield return null;
            }
        }

        Vector3 Project(double lon,double lat)
        {
            return new Vector3((float)((lon-lon0)*111319.490793*Math.Cos(lat0*Math.PI/180)),0,(float)((lat-lat0)*111319.490793));
        }

        Mesh Extrude(List<Vector2> p,float h)
        {
            int n=p.Count;if(n<3)return null;
            var verts=new Vector3[n*2];
            for(int i=0;i<n;i++){verts[i]=new Vector3(p[i].x,0,p[i].y);verts[n+i]=new Vector3(p[i].x,h,p[i].y);}
            var tris=new List<int>();
            // Ear clipping for concave OSM footprints.
            var ids=new List<int>();for(int i=0;i<n;i++)ids.Add(i);
            bool ccw=SignedArea(p)>0;int guard=0;
            while(ids.Count>2&&guard++<n*n)
            {
                bool cut=false;
                for(int i=0;i<ids.Count;i++)
                {
                    int ia=ids[(i+ids.Count-1)%ids.Count],ib=ids[i],ic=ids[(i+1)%ids.Count];
                    if(Cross(p[ia],p[ib],p[ic])*(ccw?1:-1)<=0.00001f)continue;
                    bool contains=false;
                    foreach(int k in ids){if(k==ia||k==ib||k==ic)continue;if(InTriangle(p[k],p[ia],p[ib],p[ic])){contains=true;break;}}
                    if(contains)continue;
                    tris.Add(ia);tris.Add(ib);tris.Add(ic);
                    tris.Add(n+ic);tris.Add(n+ib);tris.Add(n+ia);
                    ids.RemoveAt(i);cut=true;break;
                }
                if(!cut)break;
            }
            for(int i=0;i<n;i++){int j=(i+1)%n;tris.Add(i);tris.Add(j);tris.Add(j+n);tris.Add(i);tris.Add(j+n);tris.Add(i+n);}
            var mesh=new Mesh();if(verts.Length>65000)mesh.indexFormat=UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices=verts;mesh.triangles=tris.ToArray();mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;
        }
        float SignedArea(List<Vector2> p){float a=0;for(int i=0,j=p.Count-1;i<p.Count;j=i++)a+=p[j].x*p[i].y-p[i].x*p[j].y;return a*.5f;}
        float Cross(Vector2 a,Vector2 b,Vector2 c){return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);}
        bool InTriangle(Vector2 p,Vector2 a,Vector2 b,Vector2 c){float x=Cross(a,b,p),y=Cross(b,c,p),z=Cross(c,a,p);return (x>=0&&y>=0&&z>=0)||(x<=0&&y<=0&&z<=0);}
        Material BuildingMaterial(string hint)
        {
            var m=new Material(Shader.Find("Standard"));string h=(hint??"").ToLowerInvariant();
            if(h.Contains("glass"))m.color=new Color(.38f,.52f,.58f);
            else if(h.Contains("brick"))m.color=new Color(.58f,.34f,.25f);
            else if(h.Contains("stone"))m.color=new Color(.68f,.61f,.49f);
            else m.color=new Color(.76f,.72f,.64f);
            m.SetFloat("_Glossiness",h.Contains("glass")?.62f:.22f);return m;
        }
        float WidthFor(string highway){switch((highway??"").ToLowerInvariant()){case "motorway":case "trunk":return 13;case "primary":return 9;case "secondary":return 7;case "tertiary":return 5;case "footway":case "path":return 1.3f;default:return 3.5f;}}
        Color ColorForRoad(string highway){string h=(highway??"").ToLowerInvariant();return h=="footway"||h=="path"?new Color(.62f,.55f,.43f):new Color(.20f,.20f,.19f);}
        void OnGUI()
        {
            if(guiStyle==null){guiStyle=new GUIStyle(GUI.skin.box);guiStyle.fontSize=16;guiStyle.alignment=TextAnchor.MiddleLeft;}
            GUI.Box(new Rect(12,12,270,74),"MIDDLE EAST OPEN WORLD\n"+region+"  |  WASD move · Shift run",guiStyle);
            if(GUI.Button(new Rect(12,92,130,34),"Load Jordan")&&region!="Jordan")SwitchRegion("Jordan");
            if(GUI.Button(new Rect(150,92,130,34),"Load Palestine")&&region!="Palestine")SwitchRegion("Palestine");
        }
        void SwitchRegion(string next)
        {
            StopAllCoroutines();if(buildingsRoot)Destroy(buildingsRoot);if(streetsRoot)Destroy(streetsRoot);
            loaded.Clear();buildingIndex.Clear();streetIndex.Clear();ready=false;SetRegion(next);
            basePath=Path.Combine(Application.streamingAssetsPath,"MiddleEastWorld/"+region+"/");
            StartCoroutine(LoadManifest());
        }
    }

    public sealed class FaceCamera : MonoBehaviour
    {
        void LateUpdate(){var c=Camera.main;if(c)transform.rotation=Quaternion.LookRotation(transform.position-c.transform.position);}
    }
}
