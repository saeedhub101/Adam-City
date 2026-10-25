using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Minimal, dependency-free Unity world runtime primitives. Add to a Unity 2022.3+ project.
/// GeoJSON preparation is handled by tools/prepare_unity_data.py.
/// </summary>
namespace MiddleEastWorld
{
    [Serializable] public class GeoFeatureCollection { public string type; public GeoFeature[] features; }
    [Serializable] public class GeoFeature { public string type; public GeoGeometry geometry; public GeoProperties properties; }
    [Serializable] public class GeoGeometry { public string type; public double[][][] coordinates; }
    [Serializable] public class GeoProperties
    {
        public string name; public string height; public string building; public string building_levels;
        public string levels; public string highway; public string surface; public string material;
        public string roof_material; public string roof_shape; public string addr_street; public string shop;
        public string amenity; public string historic; public string tourism;
    }

    public static class GeoProjection
    {
        // Equirectangular local tangent approximation, appropriate for regional chunks.
        public static Vector3 ToLocal(double lon, double lat, double originLon, double originLat)
        {
            const double R = 6378137.0;
            double x = (lon - originLon) * Math.PI / 180.0 * R * Math.Cos(originLat * Math.PI / 180.0);
            double z = (lat - originLat) * Math.PI / 180.0 * R;
            return new Vector3((float)x, 0, (float)z);
        }
    }

    public sealed class ThirdPersonWalker : MonoBehaviour
    {
        public float walkSpeed = 4.2f, runSpeed = 7.0f, turnSpeed = 540f, gravity = -22f;
        CharacterController controller; float verticalSpeed; Camera viewCamera;
        void Awake()
        {
            controller = GetComponent<CharacterController>() ?? gameObject.AddComponent<CharacterController>();
            viewCamera = Camera.main;
        }
        void Update()
        {
            float x = Input.GetAxisRaw("Horizontal"), z = Input.GetAxisRaw("Vertical");
            Vector3 forward = viewCamera ? Vector3.ProjectOnPlane(viewCamera.transform.forward, Vector3.up).normalized : transform.forward;
            Vector3 right = viewCamera ? Vector3.ProjectOnPlane(viewCamera.transform.right, Vector3.up).normalized : transform.right;
            Vector3 move = Vector3.ClampMagnitude(forward * z + right * x, 1f);
            if (move.sqrMagnitude > 0.001f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(move), turnSpeed * Time.deltaTime);
            if (controller.isGrounded && verticalSpeed < 0) verticalSpeed = -2f;
            verticalSpeed += gravity * Time.deltaTime;
            float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : walkSpeed;
            controller.Move((move * speed + Vector3.up * verticalSpeed) * Time.deltaTime);
        }
    }

    public sealed class StreetLabel : MonoBehaviour
    {
        public string streetName;
        public float visibleDistance = 90f;
        Camera cam; TextMesh textMesh;
        void Awake()
        {
            cam = Camera.main;
            textMesh = GetComponent<TextMesh>() ?? gameObject.AddComponent<TextMesh>();
            textMesh.text = streetName ?? "";
            textMesh.anchor = TextAnchor.MiddleCenter;
            textMesh.alignment = TextAlignment.Center;
            textMesh.fontSize = 48;
            textMesh.characterSize = 0.16f;
        }
        void LateUpdate()
        {
            if (!cam) cam = Camera.main;
            if (!cam) return;
            transform.rotation = Quaternion.LookRotation(transform.position - cam.transform.position);
            textMesh.gameObject.SetActive(Vector3.Distance(cam.transform.position, transform.position) <= visibleDistance);
        }
    }
}
