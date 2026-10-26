using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

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
            // Jordan starts at the user's requested Tabarbour point. Keep chunk
            // coordinates relative to this origin so the player spawns in-place.
            originLon=region=="Jordan"?35.940358:35.20;
            originLat=region=="Jordan"?31.997579:31.90;
            lon0=originLon;lat0=originLat;
        }

        IEnumerator ReadText(string path, Action<string> callback)
        {
            // All runtime data must be a local file inside StreamingAssets.
            // No HTTP, hosted tiles, remote APIs, or external model URLs are permitted.
            string root = Path.GetFullPath(Application.streamingAssetsPath) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
            {
                Debug.LogError("Blocked non-local runtime data path: " + path);
                callback(null);
                yield break;
            }
            if (!File.Exists(full))
            {
                Debug.LogWarning("Missing repository-local runtime file: " + full);
                callback(null);
                yield break;
            }
            string text = null;
            try { text = File.ReadAllText(full); }
            catch (Exception e) { Debug.LogError("Could not read local runtime file: " + e.Message); }
            callback(text);
            yield return null;
        }

        IEnumerator LoadManifest()
        {
            string json=null;
            yield return ReadText(basePath+"manifest.json",s=>json=s);
            if(string.IsNullOrEmpty(json))
            {
                Debug.LogWarning("Missing optional OSM runtime manifest for "+region+". Existing local GLB tiles can still render; streamed OSM streets and fallback buildings are unavailable until repository BuildData is installed.");
                yield break;
            }
            var manifest=JsonUtility.FromJson<ChunkManifest>(json);
            if(manifest==null || manifest.layers==null) { Debug.LogError("Invalid region manifest: "+region); yield break; }
            // Deliberately do not index or render OSM footprints as extruded buildings.
            // Footprints and tags are not photogrammetry; displaying them as 3D buildings
            // would invent geometry/materials contrary to the project accuracy rules.
            Index(manifest.layers.streets,streetIndex);
            streetsRoot=new GameObject("Repository Streets — "+region);
            ready=true;
            Debug.Log("World streamer ready: "+region+"; "+buildingIndex.Count+" building chunks; "+streetIndex.Count+" street chunks.");
            RefreshTiles();
        }

        void Index(ChunkLayer layer,Dictionary<string,ChunkInfo> index)
        {
            if(layer==null||layer.chunks==null)return;
            foreach(var c in layer.chunks) if(c!=null&&!string.IsNullOrEmpty(c.tile)) index[c.tile]=c;
        }

        void RemoveBuildingChunksCoveredByExistingGlbTiles()
        {
            // The installed 5x5 GLB tile neighborhood is detailed geometry.
            // Suppress duplicate extruded OSM buildings in the overlapping 3x3
            // runtime cells while preserving OSM street rendering and distant fallback.
            int tx=(int)Math.Floor(originLon/tileDegrees);
            int ty=(int)Math.Floor(originLat/tileDegrees);
            for(int x=tx-1;x<=tx+1;x++)
                for(int y=ty-1;y<=ty+1;y++)
                    buildingIndex.Remove(x+"_"+y);
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
                        if(streetIndex.TryGetValue(key,out var s)) StartCoroutine(LoadStreetChunk(s));
                    }
                }
        }

        float playerOffsetX(){return player?player.position.x:0;}
        float playerOffsetZ(){return player?player.position.z:0;}

        IEnumerator LoadBuildingChunk(ChunkInfo chunk)
        {
            // Deliberately disabled: OSM outlines and estimated heights are not scanned
            // buildings. Only verified existing local GLB assets may supply building geometry.
            Debug.LogWarning("Skipped OSM extrusion for " + chunk.file + "; use verified local GLB building assets.");
            yield break;
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
