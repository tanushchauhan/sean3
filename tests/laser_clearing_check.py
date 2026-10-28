"""Exercise the installed Nav2 obstacle layer with disappearing LaserScan returns."""
import argparse
import array
import json
import math
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from lifecycle_msgs.srv import ChangeState
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


def check(root, name, infinite, valid, marking, split=False):
    folder=root/name;folder.mkdir()
    config=folder/'params.yaml'
    config.write_text('''/**:
  ros__parameters:
    use_sim_time: false
    global_frame: map
    robot_base_frame: base_link
    rolling_window: false
    width: 10
    height: 10
    origin_x: -5.0
    origin_y: -5.0
    resolution: 0.05
    robot_radius: 0.16
    track_unknown_space: false
    always_send_full_costmap: true
    update_frequency: 20.0
    publish_frequency: 20.0
    controller_frequency: 20.0
    progress_checker_plugin: progress_checker
    goal_checker_plugins: [goal_checker]
    controller_plugins: [FollowPath]
    progress_checker:
      plugin: nav2_controller::SimpleProgressChecker
    goal_checker:
      plugin: nav2_controller::SimpleGoalChecker
    FollowPath:
      plugin: nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController
    plugins: [obstacle_layer]
    obstacle_layer:
      plugin: nav2_costmap_2d::ObstacleLayer
      enabled: true
      footprint_clearing_enabled: false
      observation_sources: scan
      scan:
        topic: /clearing_test_scan
        data_type: LaserScan
        marking: true
        clearing: true
        min_obstacle_height: -2.0
        max_obstacle_height: 2.0
        inf_is_valid: '''+str(valid).lower()+'''
        obstacle_max_range: '''+str(marking)+'''
        raytrace_max_range: 3.5
''')
    if split:
        text=config.read_text().replace('observation_sources: scan','observation_sources: scan scan_clear')
        text=text.replace('        clearing: true','        clearing: false')
        text+='''
      scan_clear:
        topic: /clearing_test_scan
        data_type: LaserScan
        marking: false
        clearing: true
        inf_is_valid: true
        min_obstacle_height: -2.0
        max_obstacle_height: 2.0
        raytrace_max_range: 3.5
'''
        config.write_text(text)
    namespace='/'+name.replace('-','_')
    log=(folder/'costmap.log').open('w')
    process=subprocess.Popen(['ros2','run','nav2_controller','controller_server','--ros-args','--params-file',str(config)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    log.close()
    node=rclpy.create_node('laser_clearing_probe')
    latest={}
    static=StaticTransformBroadcaster(node)
    transforms=[]
    for parent,child,z in [('map','base_link',0),('base_link','laser',.2)]:
        t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child;t.header.stamp=node.get_clock().now().to_msg();t.transform.translation.z=float(z);t.transform.rotation.w=1.;transforms.append(t)
    static.sendTransform(transforms)
    pub=node.create_publisher(LaserScan,'/clearing_test_scan',qos_profile_sensor_data)
    def wait(pred,timeout,label):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=.02)
            if pred():return
            if process.poll() is not None:raise RuntimeError('Costmap exited: '+str(process.returncode))
        raise RuntimeError('Timeout: '+label)
    try:
        wait(lambda:any(n.endswith('/controller_server/change_state') for n,types in node.get_service_names_and_types()),20,'lifecycle discovery')
        service=next(n for n,types in node.get_service_names_and_types() if n.endswith('/controller_server/change_state'))
        client=node.create_client(ChangeState,service);wait(client.service_is_ready,10,'lifecycle ready')
        for transition in (1,3):
            request=ChangeState.Request();request.transition.id=transition;future=client.call_async(request);wait(future.done,15,'lifecycle transition');assert future.result().success
        wait(lambda:pub.get_subscription_count()>0,10,'laser subscription')
        wait(lambda:any('nav_msgs/msg/OccupancyGrid' in types for topic,types in node.get_topic_names_and_types()),10,'costmap grid discovery')
        topic=next(topic for topic,types in node.get_topic_names_and_types() if 'nav_msgs/msg/OccupancyGrid' in types)
        node.create_subscription(OccupancyGrid,topic,lambda msg:latest.update(grid=msg),1)
        def value(x,y):
            g=latest['grid'];ix=math.floor((x-g.info.origin.position.x)/g.info.resolution);iy=math.floor((y-g.info.origin.position.y)/g.info.resolution)
            return g.data[iy*g.info.width+ix]
        def emit(obstacle,seconds):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                scan=LaserScan();scan.header.frame_id='laser';scan.header.stamp=node.get_clock().now().to_msg();scan.angle_min=0.;scan.angle_max=2*math.pi;scan.angle_increment=2*math.pi/360;scan.range_min=.12;scan.range_max=3.5
                scan.ranges=array.array('f',[math.inf if infinite else 0.]*360)
                if obstacle:scan.ranges[0]=float(obstacle)
                pub.publish(scan)
                for _ in range(3):rclpy.spin_once(node,timeout_sec=.02)
        emit(True,1.5)
        wait(lambda:'grid'in latest,10,'costmap grid after first scan')
        # One finite ray marks its actual endpoint; tolerate float-to-cell rounding.
        marked=max(value(x,y) for x in (.975,1.,1.025) for y in (-.025,0,.025))
        assert marked==100,('Obstacle not marked',marked)
        emit(False,2.)
        remaining=max(value(x,y) for x in (.975,1.,1.025) for y in (-.025,0,.025))
        g=latest['grid'];lethal=[]
        for iy in range(g.info.height):
            for ix in range(g.info.width):
                if g.data[iy*g.info.width+ix]>=99:
                    x=g.info.origin.position.x+(ix+.5)*g.info.resolution;y=g.info.origin.position.y+(iy+.5)*g.info.resolution
                    lethal.append([x,y])
        emit(3.495,1.5)
        far_marked=max(value(x,y) for x in (3.47,3.495,3.52) for y in (-.025,0,.025))
        result=dict(split_sources=split,far_finite_return_marked=far_marked==100,name=name,inf_is_valid=valid,marking_range=marking,missing_return='positive infinity' if infinite else 'zero',marked=marked,remaining=remaining,lethal_cells=len(lethal),cleared=remaining==0,no_artificial_ring=len(lethal)==0)
        (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result
    finally:
        os_error=None
        if 'client' in locals() and process.poll() is None:
            for transition in (4,2):
                request=ChangeState.Request();request.transition.id=transition
                future=client.call_async(request)
                try:wait(future.done,5,'lifecycle cleanup')
                except RuntimeError:break
        try:
            import os
            os.killpg(process.pid,signal.SIGINT);process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait();os_error='forced kill'
        if 'result' in locals():
            result['process_exit_code']=process.returncode
            result['clean_shutdown']=process.returncode==0 and os_error is None
            (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
            if process.returncode!=0:os_error='costmap process exited '+str(process.returncode)
        node.destroy_node()
        if os_error:raise RuntimeError(os_error)


def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--profile');a=p.parse_args();a.output.mkdir();rclpy.init()
    try:
        results=[]
        for args in [('legacy-zero',False,False,3.5),('infinity-disabled',True,False,3.49),('infinity-full-marking',True,True,3.5),('infinity-clearing',True,True,3.49),('split-clearing',True,False,3.5,True)]:
            if a.profile is None or a.profile==args[0]:results.append(check(a.output,*args))
        if a.profile:return
        passed=(not results[0]['cleared'] and not results[1]['cleared'] and results[2]['cleared'] and not results[2]['no_artificial_ring'] and results[3]['cleared'] and results[3]['no_artificial_ring'] and results[4]['cleared'] and results[4]['no_artificial_ring'] and results[4]['far_finite_return_marked'])
        (a.output/'summary.json').write_text(json.dumps(dict(passed=passed,profiles=results),indent=2)+'\n');assert passed
    finally:rclpy.shutdown()


if __name__=='__main__':main()
