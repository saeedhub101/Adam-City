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

        void Start()
        {
            // BuildGLB/amman is generated from OSM footprints and synthetic facade/window
            // geometry, not photogrammetry. Reject it under the photogrammetry-only policy.
            Debug.LogWarning("Amman OSM-generated GLB tiles are disabled. No synthetic building geometry will be loaded.");
        }
    }
}
