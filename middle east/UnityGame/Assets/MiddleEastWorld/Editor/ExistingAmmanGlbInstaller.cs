#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

[Serializable] public class AmmanGlbManifest { public AmmanGlbTile[] tiles; }
[Serializable] public class AmmanGlbTile { public string tile; public string file; }

public static class ExistingAmmanGlbInstaller
{
    public const double StartLon = 35.940358;
    public const double StartLat = 31.997579;
    const double TileDegrees = 0.01;
    const int Radius = 2;

    [MenuItem("MiddleEastWorld/Install Existing Tabarbour GLB Tiles")]
    public static void InstallNearbyTiles()
    {
        string projectRoot = Directory.GetParent(Application.dataPath).FullName;
        string source = Path.GetFullPath(Path.Combine(projectRoot, "..", "BuildGLB", "amman"));
        string manifestPath = Path.Combine(source, "manifest.json");
        if (!File.Exists(manifestPath))
        {
            EditorUtility.DisplayDialog("Existing GLB tiles not found",
                "Expected the existing repository assets at middle east/BuildGLB/amman/manifest.json. No new geographic data was downloaded.", "OK");
            return;
        }

        var manifest = JsonUtility.FromJson<AmmanGlbManifest>(File.ReadAllText(manifestPath));
        var byTile = new Dictionary<string, AmmanGlbTile>();
        if (manifest != null && manifest.tiles != null)
            foreach (var tile in manifest.tiles)
                if (tile != null && !string.IsNullOrEmpty(tile.tile) && !string.IsNullOrEmpty(tile.file))
                    byTile[tile.tile] = tile;

        int tx = (int)Math.Floor(StartLon / TileDegrees);
        int ty = (int)Math.Floor(StartLat / TileDegrees);
        string target = Path.Combine(Application.streamingAssetsPath, "AmmanGLB");
        Directory.CreateDirectory(target);
        int copied = 0;
        for (int x = tx - Radius; x <= tx + Radius; x++)
        for (int y = ty - Radius; y <= ty + Radius; y++)
        {
            string key = x + "_" + y;
            if (!byTile.TryGetValue(key, out var entry)) continue;
            string from = Path.Combine(source, entry.file);
            if (!File.Exists(from)) continue;
            string to = Path.Combine(target, entry.file);
            if (!File.Exists(to) || new FileInfo(from).Length != new FileInfo(to).Length)
            {
                File.Copy(from, to, true);
                copied++;
            }
        }
        AssetDatabase.Refresh();
        EditorUtility.DisplayDialog("Tabarbour GLB tiles ready",
            "Copied " + copied + " existing GLB tile file(s) from the repository. No external geographic data was fetched.", "OK");
    }
}
#endif
