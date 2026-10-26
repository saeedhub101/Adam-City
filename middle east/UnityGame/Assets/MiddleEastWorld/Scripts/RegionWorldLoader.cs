using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

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
  IEnumerator TextAt(string path,Action<string> done){
   string root=Path.GetFullPath(Application.streamingAssetsPath)+Path.DirectorySeparatorChar;
   string full=Path.GetFullPath(path);
   if(!full.StartsWith(root,StringComparison.OrdinalIgnoreCase)){
    Debug.LogError("Blocked non-local runtime data path: "+path);
    done(null);yield break;
   }
   if(!File.Exists(full)){
    Debug.LogWarning("Missing repository-local runtime file: "+path);
    done(null);yield break;
   }
   string text=null;
   try{text=File.ReadAllText(full);}catch(Exception e){Debug.LogError("Could not read local runtime file: "+e.Message);}
   done(text);yield return null;
  }
  IEnumerator LoadBuildings(string path){
   // OSM footprints are map outlines, not photographed/photogrammetric buildings.
   // This fallback loader intentionally refuses to extrude them or invent facade materials.
   Debug.LogWarning("OSM building extrusion is disabled. Load only verified local GLB building assets with real source provenance.");
   yield break;
  }
  IEnumerator LoadStreets(string path){string json=null;yield return TextAt(path,s=>json=s);if(string.IsNullOrEmpty(json))yield break;var data=JsonUtility.FromJson<FeatureSet<StreetRecord>>(json);if(data==null||data.features==null)yield break;var root=new GameObject("OSM Streets "+region);int n=0;foreach(var s in data.features){if(n>=streetLimit)break;if(s.points==null||s.points.Length<2)continue;var go=new GameObject(string.IsNullOrEmpty(s.name)?"Street":s.name);go.transform.SetParent(root.transform,false);var lr=go.AddComponent<LineRenderer>();lr.useWorldSpace=false;lr.positionCount=s.points.Length;for(int i=0;i<s.points.Length;i++)lr.SetPosition(i,LocalProjection.XY(s.points[i][0],s.points[i][1],originLon,originLat)+Vector3.up*.04f);lr.widthMultiplier=streetWidth;lr.material=new Material(Shader.Find("Sprites/Default"));lr.startColor=lr.endColor=new Color(.19f,.19f,.18f);if(names&&!string.IsNullOrEmpty(s.name)){var label=new GameObject("Street label "+s.name);label.transform.SetParent(root.transform,false);label.transform.position=lr.GetPosition(s.points.Length/2)+Vector3.up*2;label.AddComponent<StreetNameLabel>().value=s.name;}n++;if(n%250==0)yield return null;}Debug.Log("Loaded "+n+" street lines for "+region);}
 }
}
