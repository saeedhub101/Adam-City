using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

namespace MiddleEastWorld {
 [Serializable] public class FeatureSet<T>{ public T[] features; }
 [Serializable] public class BuildingRecord{public string id,name,material;public float height;public int levels;public double[][] ring;}
 [Serializable] public class StreetRecord{public string name,highway;public double[][] points;}

 public static class LocalProjection{
  const double R=6378137.0;
  public static Vector3 XY(double lon,double lat,double lon0,double lat0){
   return new Vector3((float)((lon-lon0)*Math.PI/180*R*Math.Cos(lat0*Math.PI/180)),0,(float)((lat-lat0)*Math.PI/180*R));
  }
 }
 public class ThirdPersonWalker:MonoBehaviour{
  public float walkSpeed=4.3f,runSpeed=7.2f,gravity=-22,turnSpeed=520;CharacterController cc;float vy;Camera cam;
  void Awake(){cc=GetComponent<CharacterController>()??gameObject.AddComponent<CharacterController>();cam=Camera.main;}
  void Update(){float x=Input.GetAxisRaw("Horizontal"),z=Input.GetAxisRaw("Vertical");Vector3 f=cam?Vector3.ProjectOnPlane(cam.transform.forward,Vector3.up).normalized:transform.forward;Vector3 r=cam?Vector3.ProjectOnPlane(cam.transform.right,Vector3.up).normalized:transform.right;Vector3 d=Vector3.ClampMagnitude(f*z+r*x,1);if(d.sqrMagnitude>.001f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(d),turnSpeed*Time.deltaTime);if(cc.isGrounded&&vy<0)vy=-2;vy+=gravity*Time.deltaTime;cc.Move((d*(Input.GetKey(KeyCode.LeftShift)?runSpeed:walkSpeed)+Vector3.up*vy)*Time.deltaTime);}
 }
 public class StreetNameLabel:MonoBehaviour{
  public string value;Camera cam;TextMesh tm;
  void Awake(){cam=Camera.main;tm=gameObject.AddComponent<TextMesh>();tm.text=value;tm.anchor=TextAnchor.MiddleCenter;tm.alignment=TextAlignment.Center;tm.fontSize=44;tm.characterSize=.2f;}
  void LateUpdate(){if(!cam)cam=Camera.main;if(cam)transform.rotation=Quaternion.LookRotation(transform.position-cam.transform.position);}
 }
 public class RegionWorldLoader:MonoBehaviour{
  public string region="Jordan";public double originLon=35.91,originLat=31.95;public int buildingLimit=60000,streetLimit=15000;public float streetWidth=4;public bool names=true;
  IEnumerator Start(){if(region=="Palestine"){originLon=35.20;originLat=31.90;}string folder=Path.Combine(Application.streamingAssetsPath,"MiddleEastWorld/"+region+"/");yield return LoadBuildings(folder+"buildings.runtime.json");yield return LoadStreets(folder+"streets.runtime.json");}
  IEnumerator TextAt(string path,Action<string> done){string uri=path;if(!uri.Contains("://"))uri="file://"+uri;using(var q=UnityWebRequest.Get(uri)){yield return q.SendWebRequest();if(q.result!=UnityWebRequest.Result.Success){Debug.LogError("Missing generated region file: "+path+"; run middle east/UnityGame/tools/prepare_unity_data.py and copy BuildData to StreamingAssets/MiddleEastWorld/"+region);done(null);}else done(q.downloadHandler.text);}}
  IEnumerator LoadBuildings(string path){string json=null;yield return TextAt(path,s=>json=s);if(string.IsNullOrEmpty(json))yield break;var data=JsonUtility.FromJson<FeatureSet<BuildingRecord>>(json);if(data==null||data.features==null)yield break;var root=new GameObject("OSM Buildings "+region);int n=0;foreach(var b in data.features){if(n>=buildingLimit)break;if(b.ring==null||b.ring.Length<4)continue;var pts=new List<Vector2>();foreach(var q in b.ring){var p=LocalProjection.XY(q[0],q[1],originLon,originLat);pts.Add(new Vector2(p.x,p.z));}if(pts.Count>3&&(pts[0]-pts[pts.Count-1]).sqrMagnitude<.01f)pts.RemoveAt(pts.Count-1);var mesh=MakeExtrusion(pts,Mathf.Max(2.5f,b.height));if(mesh==null)continue;var go=new GameObject(string.IsNullOrEmpty(b.name)?"Building "+b.id:b.name);go.transform.SetParent(root.transform,false);go.AddComponent<MeshFilter>().sharedMesh=mesh;var mr=go.AddComponent<MeshRenderer>();mr.sharedMaterial=MaterialFor(b.material);go.AddComponent<MeshCollider>().sharedMesh=mesh;n++;if(n%300==0)yield return null;}Debug.Log("Built "+n+" building meshes for "+region);}
  Mesh MakeExtrusion(List<Vector2> p,float h){int n=p.Count;if(n<3)return null;var v=new Vector3[n*2];for(int i=0;i<n;i++){v[i]=new Vector3(p[i].x,0,p[i].y);v[n+i]=new Vector3(p[i].x,h,p[i].y);}var t=new List<int>();for(int i=1;i<n-1;i++){t.AddRange(new[]{0,i+1,i,n,n+i,n+i+1});}for(int i=0;i<n;i++){int j=(i+1)%n;t.AddRange(new[]{i,j,j+n,i,j+n,i+n});}var m=new Mesh();if(v.Length>65000)m.indexFormat=UnityEngine.Rendering.IndexFormat.UInt32;m.vertices=v;m.triangles=t.ToArray();m.RecalculateNormals();m.RecalculateBounds();return m;}
  Material MaterialFor(string hint){var m=new Material(Shader.Find("Standard"));m.color=hint.ToLower().Contains("stone")?new Color(.70f,.62f,.49f):new Color(.77f,.72f,.63f);m.SetFloat("_Glossiness",.2f);return m;}
  IEnumerator LoadStreets(string path){string json=null;yield return TextAt(path,s=>json=s);if(string.IsNullOrEmpty(json))yield break;var data=JsonUtility.FromJson<FeatureSet<StreetRecord>>(json);if(data==null||data.features==null)yield break;var root=new GameObject("OSM Streets "+region);int n=0;foreach(var s in data.features){if(n>=streetLimit)break;if(s.points==null||s.points.Length<2)continue;var go=new GameObject(string.IsNullOrEmpty(s.name)?"Street":s.name);go.transform.SetParent(root.transform,false);var lr=go.AddComponent<LineRenderer>();lr.useWorldSpace=false;lr.positionCount=s.points.Length;for(int i=0;i<s.points.Length;i++)lr.SetPosition(i,LocalProjection.XY(s.points[i][0],s.points[i][1],originLon,originLat)+Vector3.up*.04f);lr.widthMultiplier=streetWidth;lr.material=new Material(Shader.Find("Sprites/Default"));lr.startColor=lr.endColor=new Color(.19f,.19f,.18f);if(names&&!string.IsNullOrEmpty(s.name)){var label=new GameObject("Street label "+s.name);label.transform.SetParent(root.transform,false);label.transform.position=lr.GetPosition(s.points.Length/2)+Vector3.up*2;label.AddComponent<StreetNameLabel>().value=s.name;}n++;if(n%250==0)yield return null;}Debug.Log("Loaded "+n+" street lines for "+region);}
 }
}
