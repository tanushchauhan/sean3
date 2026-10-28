"""Drive the opt-in Warehouse fixture through actual Nav2 actions; preserve every result."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, OccupancyGrid
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from nav2_msgs.srv import ClearEntireCostmap
from lifecycle_msgs.srv import GetState
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from social_sim_ros.msg import AgentArray


def main():
    p=argparse.ArgumentParser(); p.add_argument('report',type=Path); a=p.parse_args()
    exchange=Path(str(a.report)+'.exchange'); output=a.report.with_name('warehouse-navigation.json')
    report={'episodes':[],'passed':False}
    rclpy.init(); node=rclpy.create_node('warehouse_encounter_navigation',parameter_overrides=[Parameter('use_sim_time',value=True)])
    latest,received={},{}
    def receive(k,msg): latest[k]=msg; received[k]=time.monotonic()
    for key,topic,cls in [('odom','/robot_odom',Odometry),('scan','/laser_raycast',LaserScan),('clock','/clock',Clock),('people','/social_sim/agents',AgentArray)]:
        node.create_subscription(cls,topic,lambda msg,k=key:receive(k,msg),qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid,'/map',lambda msg:receive('map',msg),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    client=ActionClient(node,NavigateToPose,'/navigate_to_pose'); planner=ActionClient(node,ComputePathToPose,'/compute_path_to_pose')
    process=None; active=None
    def save(): output.write_text(json.dumps(report,indent=2)+'\n')
    def wait(predicate,timeout,label):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=.05)
            if predicate(): return
        raise RuntimeError('Timeout: '+label)
    def fresh():
        if not all(time.monotonic()-received.get(k,0)<2 for k in ('odom','scan','clock','people')):return False
        t=latest['clock'].clock.sec+latest['clock'].clock.nanosec*1e-9
        return all(-.1<=t-(latest[k].header.stamp.sec+latest[k].header.stamp.nanosec*1e-9)<1 for k in ('odom','scan','people'))
    try:
        seen=set()
        while True:
            wait(lambda:(exchange/'request.json').exists(),2400,'fixture request')
            request=json.loads((exchange/'request.json').read_text())
            if request.get('complete'): break
            index=request['index']
            if index in seen:
                wait(lambda:json.loads((exchange/'request.json').read_text()).get('complete') or json.loads((exchange/'request.json').read_text())['index'] not in seen,180,'next episode')
                continue
            seen.add(index)
            if process is None:
                log=output.with_name('nav2.log').open('w')
                process=subprocess.Popen(['ros2','launch','social_sim_ros','nav2_kuri.launch.py','scene:=warehouse'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                log.close()
            wait(lambda:client.server_is_ready() and planner.server_is_ready() and fresh() and 'map' in latest,60,'Nav2 servers and fresh sensors')
            for name in ('/planner_server/get_state','/controller_server/get_state','/bt_navigator/get_state'):
                service=node.create_client(GetState,name);wait(service.service_is_ready,20,'lifecycle service')
                until=time.monotonic()+30
                while True:
                    state=service.call_async(GetState.Request());wait(state.done,5,'lifecycle state')
                    if state.result().current_state.id==3:break
                    if time.monotonic()>until:raise RuntimeError('Nav2 did not activate: '+name)
                    rclpy.spin_once(node,timeout_sec=.1)
                node.destroy_client(service)
            start=(request['robotStart']['z'],-request['robotStart']['x']); target=(request['robotGoal']['z'],-request['robotGoal']['x'])
            wait(lambda:math.dist((latest['odom'].pose.pose.position.x,latest['odom'].pose.pose.position.y),start)<.05 and len(latest['people'].agents)==4,15,'matching robot pose and four published pedestrians')
            episode={'index':index,'start':start,'goal':target,'passed':False,'published_people':len(latest['people'].agents)}
            report['episodes'].append(episode); save()
            for name in ('/local_costmap/clear_entirely_local_costmap','/global_costmap/clear_entirely_global_costmap'):
                service=node.create_client(ClearEntireCostmap,name);wait(service.service_is_ready,15,'costmap service')
                future=service.call_async(ClearEntireCostmap.Request());wait(future.done,10,'costmap clear');future.result();node.destroy_client(service)
            goal=NavigateToPose.Goal(); goal.pose=PoseStamped();goal.pose.header.frame_id='map';goal.pose.header.stamp=node.get_clock().now().to_msg()
            goal.pose.pose.position.x,goal.pose.pose.position.y=target
            yaw=math.atan2(target[1]-start[1],target[0]-start[0]);goal.pose.pose.orientation.z=math.sin(yaw/2);goal.pose.pose.orientation.w=math.cos(yaw/2)
            planned=ComputePathToPose.Goal();planned.goal=goal.pose;planned.start.header=goal.pose.header;planned.start.pose=latest['odom'].pose.pose;planned.use_start=True
            future=planner.send_goal_async(planned);wait(future.done,10,'plan accepted');handle=future.result()
            if not handle.accepted:raise RuntimeError('Planner rejected fixed route')
            future=handle.get_result_async();wait(future.done,20,'global plan');planned=future.result()
            episode['plan']=[[v.pose.position.x,v.pose.position.y] for v in planned.result.path.poses];episode['plan_status']=planned.status
            if planned.status!=4 or len(episode['plan'])<2:raise RuntimeError('No global plan')
            feedback=[]
            def on_feedback(msg):feedback.append({'remaining':msg.feedback.distance_remaining,'recoveries':msg.feedback.number_of_recoveries})
            future=client.send_goal_async(goal,feedback_callback=on_feedback);wait(future.done,10,'navigation accepted');active=future.result()
            if not active.accepted:raise RuntimeError('Nav2 rejected route')
            result=active.get_result_async();(exchange/f'go-{index}').write_text('go\n');started=time.monotonic(); stale=False; stale_samples=[]
            until=started+100
            while not result.done() and time.monotonic()<until and not (exchange/f'ended-{index}').exists():
                rclpy.spin_once(node,timeout_sec=.05)
                if not fresh():
                    stale=True
                    if len(stale_samples)<30:
                        t=latest['clock'].clock.sec+latest['clock'].clock.nanosec*1e-9
                        stale_samples.append(dict(wall_seconds=time.monotonic()-started,clock=t,
                            received_ages={k:time.monotonic()-received.get(k,0) for k in ('odom','scan','clock','people')},
                            stamp_ages={k:t-(latest[k].header.stamp.sec+latest[k].header.stamp.nanosec*1e-9) for k in ('odom','scan','people')}))
            if not result.done():
                canceled=active.cancel_goal_async();wait(canceled.done,10,'cancel');wait(result.done,10,'canceled result')
            status=result.result().status;pos=latest['odom'].pose.pose.position
            episode.update(status=status,final=[pos.x,pos.y],goal_error=math.dist((pos.x,pos.y),target),fresh_sensors=not stale and fresh(),stale_samples=stale_samples,wall_seconds=time.monotonic()-started,feedback=feedback)
            episode['passed']=status==4 and episode['goal_error']<=.4 and episode['fresh_sensors']
            (exchange/f'done-{index}').write_text(str(status)+'\n');active=None;save()
            print({k:v for k,v in episode.items() if k not in ('plan','feedback')},flush=True)
        report['passed']=all(e['passed'] for e in report['episodes']);save()
    except BaseException as e:
        report['error']=str(e);save();raise
    finally:
        if active is not None:
            try: future=active.cancel_goal_async();wait(future.done,5,'final cancellation')
            except Exception:pass
        if process is not None:
            os.killpg(process.pid,signal.SIGINT)
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait();report['forced_nav2_kill']=True
        save();node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
