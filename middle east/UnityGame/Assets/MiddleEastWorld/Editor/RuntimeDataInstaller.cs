#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

public static class RuntimeDataInstaller
{
    [MenuItem("MiddleEastWorld/Install Generated Region Data")]
    public static void Install()
    {
        string project=Directory.GetParent(Application.dataPath).FullName;
        string source=Path.Combine(project,"BuildData");
        string target=Path.Combine(Application.dataPath,"StreamingAssets/MiddleEastWorld");
        if(!Directory.Exists(source))
        {
            EditorUtility.DisplayDialog("Region data not generated","BuildData was not found. Run tools/prepare_unity_data.py from the UnityGame folder first.","OK");
            return;
        }
        foreach(string region in new[]{"Jordan","Palestine"})
        {
            string from=Path.Combine(source,region);
            if(!Directory.Exists(from))continue;
            string to=Path.Combine(target,region);
            if(Directory.Exists(to))Directory.Delete(to,true);
            CopyDirectory(from,to);
        }
        AssetDatabase.Refresh();
        EditorUtility.DisplayDialog("Region data installed","Jordan and Palestine runtime chunks were copied into Assets/StreamingAssets/MiddleEastWorld.","OK");
    }

    static void CopyDirectory(string source,string target)
    {
        Directory.CreateDirectory(target);
        foreach(string file in Directory.GetFiles(source))
            File.Copy(file,Path.Combine(target,Path.GetFileName(file)),true);
        foreach(string dir in Directory.GetDirectories(source))
            CopyDirectory(dir,Path.Combine(target,Path.GetFileName(dir)));
    }
}
#endif
