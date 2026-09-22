"""Hand calculations, independent route oracles, and symmetry/regression checks.

Run from the halfline_trp folder: python -m unittest discover -s tests -v
All tests are standalone; the old simulator is not needed for the fixtures.
"""

import itertools
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

from halfline_trp import Config, Request, claimed_halfline_bound, make_servers, parameters, schedule, simulate, trip_targets
from offline import exact_offline
from workloads import PATTERNS, generate_requests, read_requests, write_requests


def exhaustive_offline(requests, m):
    """Independent tiny-instance oracle: enumerate assignments and every order."""
    optimum = math.inf
    for assignment in itertools.product(range(m), repeat=len(requests)):
        total = 0.0
        for server in range(m):
            assigned = [i for i, owner in enumerate(assignment) if owner == server]
            best = math.inf
            for order in itertools.permutations(assigned):
                time, position, cost = 0.0, 0.0, 0.0
                for i in order:
                    request = requests[i]
                    time = max(request.release, time + abs(position - request.position))
                    cost += time
                    position = request.position
                best = min(best, cost)
            total += best
        optimum = min(optimum, total)
    return optimum


class HalfLineTests(unittest.TestCase):
    def test_exact_local_count_and_no_negative_server(self):
        for m in [1,2,3,4,5,10]:
            config = Config(17,m)
            servers = make_servers(config)
            self.assertEqual(len(servers),m)
            self.assertEqual([s.id for s in servers],list(range(1,m+1)))
            self.assertTrue(all(s.count == m for s in servers))
            run = simulate([Request(0,100,17)],config)
            self.assertEqual(run.metrics()['corresponding_even_full_line_k'],2*m)
            for legs in run.trajectories.values():
                self.assertTrue(all(0 <= leg.x0 <= 17 and 0 <= leg.x1 <= 17 for leg in legs))

    def test_single_server_round_targets_and_timings(self):
        config = Config(100,1)
        server = make_servers(config)[0]
        q = 2 + math.sqrt(3)
        self.assertAlmostEqual(trip_targets(server,1)[0],q/2)
        self.assertAlmostEqual(trip_targets(server,2)[0],q*(q-1)/2)
        legs = list(itertools.islice(schedule(server,config),4))
        self.assertAlmostEqual(legs[1].t1,q)
        self.assertAlmostEqual(legs[3].t1,q*q)

    def test_partial_trip_targets_and_distances(self):
        config = Config(100,3)
        inner,middle,outer = make_servers(config)
        alpha,beta = parameters(3)
        self.assertAlmostEqual(alpha,1/6)
        self.assertAlmostEqual(beta,5/12)
        self.assertEqual(trip_targets(inner,1),trip_targets(inner,2))
        self.assertAlmostEqual(trip_targets(inner,3)[0],2*beta)
        self.assertEqual(trip_targets(middle,2),(4*beta,2*beta))
        legs = list(itertools.islice(schedule(outer,config),4))
        self.assertAlmostEqual(legs[2].t1-legs[2].t0,1+alpha)
        self.assertAlmostEqual(legs[3].t1-legs[3].t0,2*alpha)

    def test_parameter_count_is_never_halved(self):
        self.assertEqual(parameters(2),(2/7,5/7))
        self.assertEqual(parameters(3),(1/6,5/12))
        for m in range(2,20):
            a,b = parameters(m)
            self.assertAlmostEqual(a+(m-1)*b,1)
        self.assertAlmostEqual(claimed_halfline_bound(1),2+math.sqrt(3))
        self.assertAlmostEqual(claimed_halfline_bound(2),15/7)
        self.assertEqual(claimed_halfline_bound(3),2)

    def test_fractional_locations_and_duplicate_requests(self):
        for m in [1,2,3]:
            run = simulate([Request(0,0,0.37),Request(1,0,0.37)],Config(10,m))
            self.assertAlmostEqual(run.completions[0].time,0.37)
            self.assertEqual(run.completions[0].time,run.completions[1].time)
            self.assertAlmostEqual(run.metrics()['total_completion_time'],0.74)

    def test_releases_at_turn_and_just_after(self):
        peak = 1+math.sqrt(3)/2
        requests = [Request(0,peak,peak),Request(1,peak+1e-7,peak)]
        run = simulate(requests,Config(10,1))
        self.assertAlmostEqual(run.completions[0].time,peak)
        self.assertAlmostEqual(run.completions[1].time,3*peak)
        self.assertFalse(run.metrics()['paper_bound_check_applicable'])

    def test_fractional_roundoff_does_not_miss_integer_release(self):
        run = simulate([Request(0,5,4)],Config(10,3))
        self.assertEqual(run.completions[0].time,5)

    def test_origin_zero_and_tiny_positive_distance(self):
        run = simulate([Request(0,0,0),Request(1,0,1e-12)],Config(10,1))
        self.assertEqual(run.completions[0].time,0)
        self.assertAlmostEqual(run.completions[1].time,1e-12,delta=1e-24)
        self.assertEqual(run.metrics()['zero_lower_bound_requests'],1)
        self.assertAlmostEqual(run.metrics()['online_over_lower_bound'],1)

    def test_length_is_endpoint_not_full_line_diameter(self):
        run = simulate([Request(0,0,9)],Config(length=10,repairpersons=3))
        self.assertTrue(run.completions)
        with self.assertRaises(ValueError):
            simulate([Request(0,0,10.01)],Config(10,3))

    def test_endpoint_wait_has_original_timetable(self):
        run = simulate([Request(0,2,1)],Config(length=1,repairpersons=1))
        self.assertEqual(run.completions[0].time,2)
        self.assertTrue(any(leg.phase=='endpoint_wait' for leg in run.trajectories[1]))
        self.assertAlmostEqual(run.distance_by_server[1],1)

    def test_nonbinary_turn_projection_hits_endpoint_exactly(self):
        run=simulate([Request(0,3,10)],Config(10,1))
        expected=(2+math.sqrt(3))**2+10
        self.assertAlmostEqual(run.completions[0].time,expected)
        self.assertEqual(run.trajectories[1][-1].x1,10)

    def test_continuous_patrol_starts_before_first_release(self):
        run = simulate([Request(0,1,1.001)],Config(10,3))
        self.assertAlmostEqual(run.completions[0].time,1.001+1/3)
        self.assertLess(run.metrics()['online_over_lower_bound'],2)

    def test_horizon_extends_beyond_last_release(self):
        run = simulate([Request(0,1,0)],Config(10,1))
        self.assertAlmostEqual(run.completions[0].time,2+math.sqrt(3))
        self.assertGreater(run.evaluated_horizon,1)

    def test_original_full_line_regression(self):
        fixture = json.loads(Path(__file__).with_name('full_line_regression.json').read_text())
        for case in fixture['cases']:
            requests = [Request(**row) for row in case['requests']]
            run = simulate(requests,Config(case['length'],case['m']))
            for completion,expected in zip(run.completions,case['completion_times']):
                self.assertAlmostEqual(completion.time,expected,places=8)
            for server,expected in zip(run.servers,case['half_distances']):
                self.assertAlmostEqual(run.distance_by_server[server.id],expected,places=8)

    def test_speed_continuity_boundaries_and_service_locations(self):
        requests = generate_requests(60,13,100,20)
        run = simulate(requests,Config(13,4))
        for legs in run.trajectories.values():
            for leg in legs:
                self.assertGreater(leg.t1,leg.t0)
                self.assertLessEqual(abs(leg.x1-leg.x0),leg.t1-leg.t0+1e-10)
                self.assertTrue(0 <= leg.x0 <= 13 and 0 <= leg.x1 <= 13)
            for before,after in zip(legs,legs[1:]):
                self.assertAlmostEqual(before.t1,after.t0)
                self.assertAlmostEqual(before.x1,after.x0)
        for completion in run.completions:
            self.assertGreaterEqual(completion.time,completion.request.lower_bound)
            matching = [leg for leg in run.trajectories[completion.server]
                        if leg.t0-1e-10 <= completion.time <= leg.t1+1e-10]
            self.assertTrue(any(abs(leg.position_at(completion.time)-completion.request.position)<1e-8
                                for leg in matching))

    def test_future_request_does_not_change_existing_service(self):
        prefix = [Request(0,0,0.4),Request(1,1,0.3)]
        config = Config(100,3)
        first = simulate(prefix,config)
        extended = simulate(prefix+[Request(2,1000,100)],config)
        self.assertEqual([c.time for c in first.completions],[c.time for c in extended.completions[:2]])

    def test_reflection_preserves_all_visit_times(self):
        # Reflect only inside this test's mathematical evaluator. The production
        # half-line API still rejects every negative request position.
        requests = generate_requests(35,20,40,12)
        run = simulate(requests,Config(20,3))
        for completion in run.completions:
            target = -completion.request.position
            best = math.inf
            for legs in run.trajectories.values():
                for leg in legs:
                    x0,x1 = -leg.x0,-leg.x1
                    visit = math.inf
                    if x0==x1==target:
                        visit=max(leg.t0,completion.request.release)
                    elif x0!=x1 and min(x0,x1)-1e-10<=target<=max(x0,x1)+1e-10:
                        visit=leg.t0+(target-x0)/(x1-x0)*(leg.t1-leg.t0)
                    if completion.request.release-1e-10 <= visit <= leg.t1+1e-10:
                        best=min(best,max(visit,completion.request.release))
            self.assertAlmostEqual(best,completion.time,places=8)

    def test_all_patterns_are_valid_seeded_half_line_inputs(self):
        for pattern in PATTERNS:
            requests = generate_requests(100,17,50,8,pattern)
            self.assertEqual(requests,generate_requests(100,17,50,8,pattern))
            self.assertTrue(all(0<=r.position<=17 and 0<=r.release<=50 for r in requests))
            self.assertTrue(all(float(r.release).is_integer() for r in requests))
            if pattern=='early': self.assertTrue(all(r.release==0 for r in requests))
            if pattern=='near_origin': self.assertTrue(all(r.position<=0.05*17 for r in requests))
            if pattern=='near_endpoint': self.assertTrue(all(r.position>=0.95*17 for r in requests))
            if pattern=='endpoints': self.assertTrue(all(r.position in [0,17] for r in requests))

    def test_csv_roundtrip_and_negative_input_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'requests.csv'
            requests=[Request(9,3,0.1),Request(2,1,7)]
            write_requests(path,requests)
            self.assertEqual(read_requests(path),requests)
            path.write_text('id,release_time,position\n0,1,-0.1\n')
            with self.assertRaises(ValueError): read_requests(path)

    def test_no_trace_preserves_all_costs(self):
        requests=generate_requests(100,100,100)
        config=Config(100,3)
        traced=simulate(requests,config)
        compact=simulate(requests,config,record_trajectories=False)
        self.assertEqual(traced.completions,compact.completions)
        self.assertEqual(traced.metrics(),compact.metrics())
        self.assertTrue(all(not legs for legs in compact.trajectories.values()))

    def test_empty_zero_cost_and_invalid_configurations(self):
        for requests in [[],[Request(0,0,0)]]:
            metrics=simulate(requests).metrics()
            self.assertEqual(metrics['total_completion_time'],0)
            self.assertIsNone(metrics['online_over_lower_bound'])
        for m in [0,-1,1.5,True]:
            with self.assertRaises(ValueError): Config(10,m)
        for length in [0,-1,math.nan,math.inf]:
            with self.assertRaises(ValueError): Config(length,1)
        with self.assertRaises(ValueError): Request(0,0,-1e-12)
        with self.assertRaises(ValueError): Request(0,-1,1)
        with self.assertRaises(ValueError): simulate([Request(0,0,1),Request(0,2,1)])


class OfflineTests(unittest.TestCase):
    def test_anticipation_and_same_local_count(self):
        self.assertEqual(exact_offline([Request(0,100,50)],Config(100,1)).total_completion_time,100)
        requests=[Request(i,10,i) for i in range(3)]
        self.assertEqual(sum(r.lower_bound for r in requests),30)
        self.assertEqual(exact_offline(requests,Config(10,1)).total_completion_time,33)
        self.assertEqual(exact_offline(requests,Config(10,2)).total_completion_time,31)
        self.assertEqual(exact_offline(requests,Config(10,3)).total_completion_time,30)

    def test_offline_against_exhaustive_oracle(self):
        for seed in range(5):
            rng=random.Random(seed)
            requests=[Request(i,rng.randint(0,10),rng.randint(0,8)) for i in range(5)]
            for m in [1,2,3]:
                self.assertEqual(exact_offline(requests,Config(10,m)).total_completion_time,
                                 exhaustive_offline(requests,m))

    def test_route_feasibility_and_incidental_service(self):
        requests=[Request(0,0,3),Request(1,5,1),Request(2,2,2),Request(3,1,1),Request(4,7,0)]
        config=Config(10,2)
        optimum=exact_offline(requests,config)
        lookup={r.id:r for r in requests}
        actual={r.id:math.inf for r in requests}
        finish=max(optimum.completion_times.values())
        for route in optimum.routes:
            time,position=0,0
            legs=[]
            for rid in route:
                request=lookup[rid]
                arrival=time+abs(position-request.position)
                service=max(arrival,request.release)
                legs.extend([(time,arrival,position,request.position),(arrival,service,request.position,request.position)])
                time,position=service,request.position
            legs.append((time,finish,position,position))
            for t0,t1,x0,x1 in legs:
                self.assertTrue(0<=x0<=config.length and 0<=x1<=config.length)
                for request in requests:
                    visit=math.inf
                    if x0==x1==request.position: visit=max(t0,request.release)
                    elif x0!=x1 and min(x0,x1)<=request.position<=max(x0,x1):
                        visit=t0+abs(request.position-x0)
                    if request.release<=visit<=t1: actual[request.id]=min(actual[request.id],visit)
        self.assertAlmostEqual(sum(actual.values()),optimum.total_completion_time)

    def test_offline_limits_and_domain_validation(self):
        with self.assertRaises(ValueError): exact_offline([Request(i,i,i) for i in range(11)],Config(20,1))
        with self.assertRaises(ValueError): exact_offline([Request(0,0,11)],Config(10,1))
        self.assertEqual(exact_offline([],Config(10,3)).total_completion_time,0)
        requests=[Request(i,100,i) for i in range(20)]
        self.assertEqual(exact_offline(requests,Config(20,20)).total_completion_time,2000)


if __name__=='__main__':
    unittest.main()
