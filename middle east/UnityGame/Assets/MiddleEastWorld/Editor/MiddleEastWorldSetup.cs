#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MiddleEastWorld;

public static class MiddleEastWorldSetup
{
    [MenuItem("MiddleEastWorld/Create Playable Open World Scene")]
    public static void CreatePlayableScene()
    {
        EnsureFolder("Assets/MiddleEastWorld/Scenes");
        EnsureFolder("Assets/StreamingAssets");
        EnsureFolder("Assets/StreamingAssets/MiddleEastWorld");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        var sun = new GameObject("Sun — Middle East daylight");
        var light = sun.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.15f;
        sun.transform.rotation = Quaternion.Euler(48f, -32f, 0f);
        RenderSettings.ambientLight = new Color(.53f,.51f,.47f);
        RenderSettings.fog = true;
        RenderSettings.fogColor = new Color(.70f,.68f,.63f);
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogStartDistance = 180f;
        RenderSettings.fogEndDistance = 1100f;

        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Temporary terrain base — OSM world streams over this";
        ground.transform.position = new Vector3(0,-.12f,0);
        ground.transform.localScale = new Vector3(2000,1,2000);
        var groundMat = new Material(Shader.Find("Standard"));
        groundMat.color = new Color(.55f,.49f,.38f);
        groundMat.SetFloat("_Glossiness",.05f);
        ground.GetComponent<Renderer>().sharedMaterial = groundMat;

        var player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "Player";
        player.transform.position = new Vector3(0,1.1f,0);
        Object.DestroyImmediate(player.GetComponent<CapsuleCollider>());
        player.AddComponent<CharacterController>();
        var walker = player.AddComponent<ThirdPersonWalker>();
        walker.walkSpeed=4.3f;
        walker.runSpeed=7.2f;

        var cameraObject = new GameObject("Player Camera");
        cameraObject.tag = "MainCamera";
        var camera = cameraObject.AddComponent<Camera>();
        camera.fieldOfView=68;
        camera.nearClipPlane=.08f;
        camera.farClipPlane=1800;
        cameraObject.AddComponent<AudioListener>();
        cameraObject.transform.position = new Vector3(0,5,-8);
        cameraObject.transform.LookAt(player.transform.position+Vector3.up);
        var follow = cameraObject.AddComponent<SimpleFollowCamera>();
        follow.target=player.transform;
        follow.offset=new Vector3(0,5.2f,-7.5f);

        var world = new GameObject("Open World — Jordan / Palestine");
        var streamer = world.AddComponent<OpenWorldStreamer>();
        streamer.player=player.transform;
        streamer.region="Jordan";
        streamer.tileRadius=2;
        streamer.streetLabels=true;

        EditorSceneManager.SaveScene(scene, "Assets/MiddleEastWorld/Scenes/MiddleEastOpenWorld.unity");
        AssetDatabase.SaveAssets();
        Debug.Log("Playable scene created. Copy generated BuildData/Jordan and BuildData/Palestine into Assets/StreamingAssets/MiddleEastWorld/ before running.");
    }

    static void EnsureFolder(string path)
    {
        if(AssetDatabase.IsValidFolder(path))return;
        string parent=Path.GetDirectoryName(path).Replace("\\","/");
        string name=Path.GetFileName(path);
        if(!AssetDatabase.IsValidFolder(parent))EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent,name);
    }
}

public sealed class SimpleFollowCamera : MonoBehaviour
{
    public Transform target;
    public Vector3 offset = new Vector3(0,5.2f,-7.5f);
    public float sensitivity=2.2f;
    public float minPitch=-12f,maxPitch=65f;
    float yaw,pitch=18f;
    void LateUpdate()
    {
        if(!target)return;
        if(Input.GetMouseButton(1)){yaw+=Input.GetAxis("Mouse X")*sensitivity*4f;pitch-=Input.GetAxis("Mouse Y")*sensitivity*3f;pitch=Mathf.Clamp(pitch,minPitch,maxPitch);}
        Quaternion rotation=Quaternion.Euler(pitch,yaw,0);
        Vector3 desired=target.position+rotation*offset;
        transform.position=Vector3.Lerp(transform.position,desired,Time.deltaTime*10f);
        transform.LookAt(target.position+Vector3.up*1.15f);
    }
}
#endif
