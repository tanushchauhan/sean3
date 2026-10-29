using UnityEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Sensors;

// An isolated protocol/trainer smoke test, not a Kuri navigation task.
public sealed class ProbeAgent : Agent
{
    float position, goal;
    int inferenceLimit, inferenceActions;
    float maxAction;
    public override void Initialize()
    {
        var args = System.Environment.GetCommandLineArgs();
        int index = System.Array.IndexOf(args, "-probe-inference-steps");
        if (index >= 0) inferenceLimit = int.Parse(args[index + 1]);
    }
    public override void OnEpisodeBegin()
    {
        position = 0;
        goal = Random.value < .5f ? -1 : 1;
    }
    public override void CollectObservations(VectorSensor sensor)
    {
        sensor.AddObservation(position);
        sensor.AddObservation(goal);
    }
    public override void OnActionReceived(ActionBuffers actions)
    {
        float action = actions.ContinuousActions[0];
        if (float.IsNaN(action) || float.IsInfinity(action)) throw new System.Exception("Nonfinite inference action");
        maxAction = Mathf.Max(maxAction, Mathf.Abs(action));
        position += Mathf.Clamp(actions.ContinuousActions[0], -1, 1) * .05f;
        AddReward(-Mathf.Abs(goal - position) * .01f);
        if (Mathf.Abs(goal - position) < .1f) { AddReward(1); EndEpisode(); }
        else if (Mathf.Abs(position) > 2) { AddReward(-1); EndEpisode(); }
        if (inferenceLimit > 0 && ++inferenceActions >= inferenceLimit)
        {
            bool valid = !Academy.Instance.IsCommunicatorOn && maxAction > 1e-6f;
            Debug.Log("PROBE_INFERENCE actions=" + inferenceActions + " max_abs_action=" + maxAction + " passed=" + valid);
            Application.Quit(valid ? 0 : 1);
        }
    }
}
