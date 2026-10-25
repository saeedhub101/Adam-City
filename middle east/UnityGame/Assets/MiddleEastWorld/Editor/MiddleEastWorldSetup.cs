#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MiddleEastWorld;

public static class MiddleEastWorldSetup
{
    [MenuItem("MiddleEastWorld/Create Demo Scene")]
    public static void CreateDemoScene()
    {
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Local ground placeholder — replace with prepared terrain";
        ground.transform.localScale = new Vector3(80, 1, 80);
        var player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "Player";
        player.transform.position = new Vector3(0, 1.2f, 0);
        player.AddComponent<ThirdPersonWalker>();
        var cam = Camera.main;
        if (cam)
        {
            cam.transform.position = new Vector3(0, 5, -8);
            cam.transform.LookAt(player.transform);
            var follow = cam.gameObject.AddComponent<SimpleFollowCamera>();
            follow.target = player.transform;
        }
        EditorSceneManager.SaveScene(scene, "Assets/MiddleEastWorld/Scenes/MiddleEastDemo.unity");
        AssetDatabase.SaveAssets();
        Debug.Log("Demo scene created. This is a setup scene, not a completed city build.");
    }
}

public sealed class SimpleFollowCamera : MonoBehaviour
{
    public Transform target;
    public Vector3 offset = new Vector3(0, 5, -8);
    void LateUpdate()
    {
        if (!target) return;
        transform.position = Vector3.Lerp(transform.position, target.position + offset, Time.deltaTime * 5f);
        transform.LookAt(target.position + Vector3.up * 1.2f);
    }
}
#endif
