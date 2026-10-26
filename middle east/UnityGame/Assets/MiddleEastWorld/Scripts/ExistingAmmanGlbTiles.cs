using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using System.Linq;
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
            // Read only files copied from this repository into StreamingAssets.
            // No URL or network tile source is permitted.
            string folder = Path.Combine(Application.streamingAssetsPath, "AmmanGLB");
            if (!Directory.Exists(folder))
            {
                Debug.LogWarning("No local Amman GLB tiles found in " + folder + ". Run MiddleEastWorld/Install Existing Tabarbour GLB Tiles in the Editor.");
                return;
            }

            var files = Directory.GetFiles(folder, "*.glb", SearchOption.TopDirectoryOnly)
                .OrderBy(p => p, StringComparer.Ordinal).ToArray();
            if (files.Length == 0)
            {
                Debug.LogWarning("No local GLB tiles found in " + folder);
                return;
            }

            Vector3 shift = GeoProjection.ToLocal(sourceOriginLon, sourceOriginLat, gameOriginLon, gameOriginLat);
            int loadedCount = 0;
            foreach (string file in files)
            {
                var importer = new GltfImport();
                bool ok = await importer.Load(new Uri(file).AbsoluteUri);
                if (!ok)
                {
                    Debug.LogWarning("Could not load local GLB tile: " + Path.GetFileName(file));
                    continue;
                }

                var tileRoot = new GameObject(Path.GetFileNameWithoutExtension(file));
                tileRoot.transform.SetParent(transform, false);
                tileRoot.transform.localPosition = shift;
                bool instantiated = await importer.InstantiateMainSceneAsync(tileRoot.transform);
                if (!instantiated)
                {
                    Destroy(tileRoot);
                    importer.Dispose();
                    Debug.LogWarning("Could not instantiate local GLB tile: " + Path.GetFileName(file));
                    continue;
                }
                imports.Add(importer);
                loadedCount++;
            }
            Debug.Log("Loaded " + loadedCount + " existing local Amman GLB tiles. No external runtime data was requested.");
        }
    }
}
