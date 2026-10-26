#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MiddleEastWorld;

[InitializeOnLoad]
public static class MiddleEastWorldBootstrap
{
    static MiddleEastWorldBootstrap()
    {
        EditorApplication.delayCall += EnsureStarterScene;
    }

    static void EnsureStarterScene()
    {
        const string scenePath = "Assets/MiddleEastWorld/Scenes/MiddleEastOpenWorld.unity";
        if (EditorApplication.isPlayingOrWillChangePlaymode) return;
        if (File.Exists(Path.Combine(Directory.GetCurrentDirectory(), scenePath))) return;
        MiddleEastWorldSetup.CreatePlayableScene();
        Debug.Log("Created the Tabarbour starter scene. Existing local Amman GLB tiles are installed from the repository and loaded offline; no external runtime source is used.");
    }
}

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

        // A collision-only safety floor keeps the player controllable while no verified
        // local orthophoto/terrain surface is available. It is invisible and is NOT presented
        // as terrain or a photorealistic world surface.
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Collision safety floor — invisible, not world terrain";
        ground.transform.position = new Vector3(0,-.12f,0);
        ground.transform.localScale = new Vector3(2000,1,2000);
        var groundRenderer = ground.GetComponent<Renderer>();
        if (groundRenderer) groundRenderer.enabled = false;

        var player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "Player";
        // Spawn at the requested Tabarbour / Cobra Pharmacy coordinates.
        // The streamer uses these coordinates as its local geographic origin.
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
        world.AddComponent<ExistingAmmanGlbTiles>();
        ExistingAmmanGlbInstaller.InstallNearbyTiles();
        streamer.player=player.transform;
        streamer.region="Jordan";
        streamer.originLon=35.940358;
        streamer.originLat=31.997579;
        streamer.tileRadius=2;
        streamer.tileDegrees=0.02f;
        streamer.streetLabels=true;

        const string starterScenePath = "Assets/MiddleEastWorld/Scenes/MiddleEastOpenWorld.unity";
        EditorSceneManager.SaveScene(scene, starterScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(starterScenePath, true) };
        AssetDatabase.SaveAssets();
        Debug.Log("Tabarbour scene created. Existing repository GLB tiles are enabled locally; no external runtime source is used. Their source geometry is OSM-derived, so do not describe them as photogrammetry.");
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
