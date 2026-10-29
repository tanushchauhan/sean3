using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;

public static class BuildProbe
{
    public static void Build()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
        var go = new GameObject("Compatibility probe");
        var behavior = go.AddComponent<BehaviorParameters>();
        behavior.BehaviorName = "CompatibilityProbe";
        behavior.BrainParameters.VectorObservationSize = 2;
        behavior.BrainParameters.ActionSpec = ActionSpec.MakeContinuous(1);
        var model = AssetDatabase.LoadAssetAtPath<Unity.Sentis.ModelAsset>("Assets/CompatibilityProbe.onnx");
        if (model != null) { behavior.Model = model; behavior.BehaviorType = BehaviorType.InferenceOnly; }
        go.AddComponent<ProbeAgent>().MaxStep = 100;
        go.AddComponent<DecisionRequester>().DecisionPeriod = 1;
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), "Assets/Probe.unity");
        var result = BuildPipeline.BuildPlayer(new[] { "Assets/Probe.unity" },
            Environment.GetEnvironmentVariable("SEAN_PROBE_PLAYER"), BuildTarget.StandaloneLinux64, BuildOptions.None);
        if (result.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
            throw new Exception("Compatibility probe build failed");
    }
}
