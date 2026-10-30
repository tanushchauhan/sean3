"""Negative evidence/schema checks; no Unity trajectory is synthesized as live evidence."""
import copy
import itertools
import math
import unittest
from analyze_warehouse_encounters import analyze


def fixture():
    r=dict(schema=2,laserNoReturn='PositiveInfinity',layoutVersion=3,model='ColliderV1',contactModel='VelocityBodyV1',step=.02,deadline=45,desiredSpeed=.6,seeds=[7],layouts=['aisle'],modes=['parked'],complete=True,episodes=[])
    for mirror in (-1,1):
        e=dict(index=len(r['episodes']),seed=7,layout='aisle',mirror=mirror,mode='parked',setup=True,complete=True,error=None,
               robotStart=dict(x=-5,y=0,z=5),robotGoal=dict(x=-5,y=0,z=9),robotPlan=[{},{}],duration=.02,
               robotPersonContacts=0,personPersonContacts=0,personObjectContacts=0,robotObjectContacts=0,people=[],samples=[])
        for i in range(4):
            point=dict(x=-5+(-.65 if i%2==0 else .65)*mirror,y=0,z=5+(3.5 if i<2 else 5))
            goal=dict(point,z=5-(5 if i<2 else 3.5))
            e['people'].append(dict(avatar='test',start=point.copy(),goal=goal,plan=[point.copy(),goal.copy()],radius=.2,reachedSeconds=.02))
        for t in (0,.02):
            e['samples'].append(dict(time=t,robot=dict(x=-5,y=0,z=5),robotVelocity=dict(x=0,y=0,z=0),people=[p['start' if t==0 else 'goal'].copy() for p in e['people']],robotClearances=[2.6,3.6,4.6,5.6],personClearances=[math.dist((e['people'][i]['start']['x'],e['people'][i]['start']['z']),(e['people'][j]['start']['x'],e['people'][j]['start']['z']))-.4 for i,j in itertools.combinations(range(4),2)],goalDistances=[8.5 if t==0 else 0 for i in range(4)],yielding=False))
        r['episodes'].append(e)
    return r


def navigation_fixture():
    r=fixture();r['modes']=['nav2'];n=dict(passed=True,episodes=[])
    for e in r['episodes']:
        e['mode']='nav2';e['robotStart']['z']=1;e['samples'][0]['robot']['z']=1;e['samples'][-1]['robot']['z']=9
        n['episodes'].append(dict(index=e['index'],passed=True,status=4,published_people=4,fresh_sensors=True,plan_status=4,plan=[[1,5],[9,5]],goal_error=0,scan_statistics=dict(positive_infinity_samples=360,nan_samples=0,negative_infinity_samples=0,invalid_finite_samples=0)))
    return r,n


def orca_fixture():
    r=fixture()
    r.update(pedestrianController='orca',actuationModel='VelocityTargetsV1',model='ORCA-RVO2-v2.0.1',geometryModel='NavMeshBoundaryV1',
             orcaSourceRevision='5b7147d36d5cc6310c8e74c6955145c0fdc5fe06',controllerRobotRadius=.5,
             controllerObstacleCount=1,orcaSettings=dict(decisionPeriod=.1,neighborDistance=5,maxNeighbors=64,agentHorizon=2.5,obstacleHorizon=2.5))
    for e in r['episodes']:
        e.update(controllerFaulted=False,inferenceMilliseconds=[1])
        for i,s in enumerate(e['samples']):
            s.update(controllerEpisodeId='episode-'+str(e['index']),controllerSequence=i-1,
                     personTargetVelocities=[dict(x=0,y=0,z=0) for _ in range(4)],
                     personActualVelocities=[dict(x=0,y=0,z=0) for _ in range(4)])
    return r


class WarehouseAnalysisTests(unittest.TestCase):
    def test_stars_requires_forecast_provenance_and_ready_history(self):
        r=orca_fixture()
        r.update(pedestrianController='stars',model='STARS-MA-deterministic',starsCheckpointSha256='a'*64,
                 starsExtensionRevision='d72eb2295c3336f0674932796cf41b60636cde3e',starsObservationSteps=8,starsDecisionPeriod=.4)
        for e in r['episodes']:
            e['samples'][0].update(controllerHistoryReady=False,controllerSequence=-1)
            e['samples'][1].update(controllerHistoryReady=True,controllerSequence=7)
        self.assertTrue(analyze(r)['passed'])
        for mutate in [lambda r:r.update(starsCheckpointSha256='invalid'),lambda r:r.update(starsObservationSteps=3),
                       lambda r:r.update(starsDecisionPeriod=.1),lambda r:r.update(starsExtensionRevision='unknown'),
                       lambda r:r['episodes'][0]['samples'][1].update(controllerHistoryReady=False),
                       lambda r:r['episodes'][0]['samples'][0].update(controllerHistoryReady=True),
                       lambda r:r['episodes'][0].update(controllerFaulted=True)]:
            changed=copy.deepcopy(r);mutate(changed)
            with self.subTest(mutate=mutate):self.assertFalse(analyze(changed)['passed'])
    def test_orca_provenance_and_lifecycle_evidence(self):
        result=analyze(orca_fixture());self.assertTrue(result['passed'])
        self.assertEqual(result['pedestrian_controller'],'orca')
        self.assertEqual(result['episodes'][0]['inference_latency_ms']['maximum'],1)
    def test_orca_cannot_hide_wrong_model_geometry_or_worker_failure(self):
        mutations=[lambda r:r.update(model='ColliderV1'),lambda r:r.update(geometryModel=''),
                   lambda r:r.update(actuationModel='AnimatedRootMotionV1'),
                   lambda r:r.update(orcaSourceRevision='unknown'),lambda r:r.update(controllerObstacleCount=0),
                   lambda r:r['episodes'][0].update(controllerFaulted=True),
                   lambda r:r['episodes'][0].update(inferenceMilliseconds=[]),
                   lambda r:r['episodes'][0].update(inferenceMilliseconds=[float('nan')]),
                   lambda r:r['episodes'][0]['samples'][1].update(controllerEpisodeId='stale'),
                   lambda r:r['episodes'][0]['samples'][1].update(controllerSequence=-2),
                   lambda r:r['episodes'][0]['samples'][1].update(personActualVelocities=[])]
        for change in mutations:
            r=orca_fixture();change(r)
            with self.subTest(change=change):self.assertFalse(analyze(r)['passed'])
    def test_valid_navigation_evidence(self):
        r,n=navigation_fixture();self.assertTrue(analyze(r,n)['passed'])
    def test_missing_or_invalid_navigation_evidence(self):
        mutations=[lambda n:n.update(passed=False),lambda n:n.update(forced_nav2_kill=True),
                   lambda n:n['episodes'].pop(),lambda n:n['episodes'].append(copy.deepcopy(n['episodes'][0])),
                   lambda n:n['episodes'][0].update(status=5),lambda n:n['episodes'][0].update(published_people=0),
                   lambda n:n['episodes'][0].update(fresh_sensors=False),lambda n:n['episodes'][0].update(plan_status=5),
                   lambda n:n['episodes'][0].update(plan=[]),lambda n:n['episodes'][0].update(goal_error=.5),lambda n:n['episodes'][0]['scan_statistics'].update(positive_infinity_samples=0),
                   lambda n:n['episodes'][0]['scan_statistics'].update(nan_samples=1)]
        for change in mutations:
            r,n=navigation_fixture();change(n)
            with self.subTest(change=change):self.assertFalse(analyze(r,n)['passed'])
    def test_valid_schema(self): self.assertTrue(analyze(fixture())['passed'])
    def rejected(self, edit):
        r=fixture();edit(r);self.assertFalse(analyze(r)['passed'])
    def test_fixed_pose_cannot_be_replaced(self): self.rejected(lambda r:r['episodes'][0]['robotStart'].update(x=1000))
    def test_unity_float_step(self):
        r=fixture();r['step']=.019999999552965165;self.assertTrue(analyze(r)['passed'])
    def test_person_fell_through_floor(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['people'][0].update(y=-10))
    def test_robot_height_drift(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['robot'].update(y=.5))
    def test_legacy_empty_rays_not_qualified(self): self.rejected(lambda r:r.update(laserNoReturn='LegacyZero'))
    def test_missing_mirror(self): self.rejected(lambda r:r['episodes'].pop())
    def test_duplicate_episode(self): self.rejected(lambda r:r['episodes'].append(copy.deepcopy(r['episodes'][0])))
    def test_incomplete(self): self.rejected(lambda r:r.update(complete=False))
    def test_wrong_physics(self): self.rejected(lambda r:r.update(contactModel='Legacy'))
    def test_changed_speed(self): self.rejected(lambda r:r.update(desiredSpeed=1.3))
    def test_changed_deadline(self): self.rejected(lambda r:r.update(deadline=60))
    def test_contact(self): self.rejected(lambda r:r['episodes'][0].update(robotPersonContacts=1))
    def test_person_contact(self): self.rejected(lambda r:r['episodes'][0].update(personPersonContacts=2))
    def test_wall_contact(self): self.rejected(lambda r:r['episodes'][0].update(personObjectContacts=1))
    def test_missed_goal(self): self.rejected(lambda r:r['episodes'][0]['people'][0].update(reachedSeconds=-1))
    def test_sampling_gap(self): self.rejected(lambda r:r['episodes'][0]['samples'][1].update(time=.1))
    def test_nan(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['robot'].update(x=float('nan')))
    def test_wrong_start(self): self.rejected(lambda r:r['episodes'][0]['samples'][0]['robot'].update(x=.3))
    def test_fake_goal_metric(self): self.rejected(lambda r:r['episodes'][0]['people'][0]['goal'].update(z=3))
    def test_fake_pair_clearance(self): self.rejected(lambda r:r['episodes'][0]['samples'][0]['personClearances'].__setitem__(0,9))
    def test_parked_moved(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['robot'].update(z=.2))
    def test_nonfinite_clearance(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['robotClearances'].__setitem__(0,float('nan')))
    def test_bad_shape(self): self.rejected(lambda r:r['episodes'][0]['samples'][1]['people'].pop())
    def test_unknown_mode(self): self.rejected(lambda r:r.update(modes=['other']))


if __name__=='__main__':unittest.main()
