using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using UnityEngine;
using GLTFast;

namespace MiddleEastWorld
{
    /// <summary>
    /// Loads the repository's existing GLB tiles around Tabarbour. GLB tile vertices
    /// use the Amman export origin (35.9, 31.91), so the root is shifted to the
    /// game's Tabarbour local origin (35.940358, 31.997579).
    /// </summary>
    public sealed class ExistingAmmanGlbTiles : MonoBehaviour
    {
        public double sourceOriginLon = 35.9;
        public double sourceOriginLat = 31.91;
        public double gameOriginLon = 35.940358;
        public double gameOriginLat = 31.997579;
        readonly List<GltfImport> imports = new List<GltfImport>();
        bool started;

        async void Start()
        {
            if (started) return;
            started = true;
            string folder = Path.Combine(Application.streamingAssetsPath, "AmmanGLB");
            if (!Directory.Exists(folder))
            {
                Debug.LogWarning("Existing Amman GLB tiles are not installed. In Unity, run MiddleEastWorld > Install Existing Tabarbour GLB Tiles.");
                return;
            }

            Vector3 offset = GeoProjection.ToLocal(sourceOriginLon, sourceOriginLat, gameOriginLon, gameOriginLat);
            var root = new GameObject("Existing GLB city tiles — Tabarbour");
            root.transform.position = offset;
            string[] files = Directory.GetFiles(folder, "*.glb");
            Array.Sort(files);
            foreach (string file in files)
            {
                var importer = new GltfImport();
                bool loaded;
                try { loaded = await importer.Load(new Uri(file).AbsoluteUri); }
                catch (Exception ex) { Debug.LogWarning("Could not load existing GLB " + Path.GetFileName(file) + ": " + ex.Message); continue; }
                if (!loaded)
                {
                    Debug.LogWarning("GLB import failed: " + Path.GetFileName(file));
                    continue;
                }
                var tileRoot = new GameObject(Path.GetFileNameWithoutExtension(file));
                tileRoot.transform.SetParent(root.transform, false);
                bool instantiated = await importer.InstantiateMainSceneAsync(tileRoot.transform);
                if (instantiated) imports.Add(importer);
                else
                {
                    Destroy(tileRoot);
                    Debug.LogWarning("GLB scene could not be instantiated: " + Path.GetFileName(file));
                }
            }
            Debug.Log("Loaded " + imports.Count + " existing Amman GLB tile(s) around Tabarbour.");
        }
    }
}
