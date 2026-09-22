"""Search finite half-line grids for large per-request ratios; not a proof.

All probes can be simulated together because the confirmed continuous patrol
does not react to them. Every reported witness also works as a single-request
instance. The physical endpoint and all input positions stay in [0,L].
"""

import argparse
import csv
from pathlib import Path

from halfline_trp import Config, Request, make_servers, schedule, simulate
from workloads import write_requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repairpersons", nargs="+", type=int, default=[1,2,3,4])
    parser.add_argument("--length", type=float, default=100)
    parser.add_argument("--max-release", type=int, default=100)
    parser.add_argument("--spatial-step", type=float, default=1)
    parser.add_argument("--out", type=Path, default=Path("results/bound_audit"))
    args = parser.parse_args()
    try:
        from math import isfinite
        if args.max_release < 0 or not isfinite(args.spatial_step) or args.spatial_step <= 0:
            parser.error("Use a nonnegative max-release and positive finite spatial-step.")
        configs = [Config(args.length,m) for m in sorted(set(args.repairpersons))]
        args.out.mkdir(parents=True,exist_ok=True)
        rows=[]
        for config in configs:
            points={i*args.spatial_step for i in range(int(args.length/args.spatial_step)+1)}
            points.add(args.length)
            # Add both sides of each physical turning location to the regular
            # grid, making near-missed requests more likely to be represented.
            for server in make_servers(config):
                for leg in schedule(server,config):
                    for offset in [-1e-7,0,1e-7]:
                        if 0 <= leg.x1+offset <= args.length:
                            points.add(leg.x1+offset)
                    if leg.t1 >= 8*max(1,args.max_release,args.length):
                        break
            requests=[]
            for position in sorted(points):
                for release in range(args.max_release+1):
                    if max(position,release)>0:
                        requests.append(Request(len(requests),release,position))
            run=simulate(requests,config,record_trajectories=False)
            witness=max(run.completions,key=lambda c:c.time/c.request.lower_bound)
            single=simulate([witness.request],config,record_trajectories=False)
            if abs(single.completions[0].time-witness.time)>1e-8:
                raise ArithmeticError("Witness failed the independent single-request rerun.")
            metrics=run.metrics()
            rows.append({"repairpersons":config.repairpersons,"length":args.length,
                         "max_release":args.max_release,"spatial_step":args.spatial_step,
                         "turning_point_offset":1e-7,"tested_pairs":len(requests),
                         "worst_ratio":metrics['max_request_over_lower_bound'],
                         "witness_release":witness.request.release,"witness_position":witness.request.position,
                         "witness_completion":witness.time,
                         "paper_claimed_halfline_bound":metrics['paper_claimed_halfline_bound'],
                         "observed_violation":metrics['observed_bound_violation']})
            write_requests(args.out/f'witness_m{config.repairpersons}.csv',[witness.request])
            print(f"m={config.repairpersons}: max sampled ratio={metrics['max_request_over_lower_bound']:.9f} "
                  f"at release={witness.request.release}, position={witness.request.position:.9f}")
        with (args.out/'audit.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print('Finite diagnostic only; a non-violation does not establish a competitive bound.')
    except (ValueError,ArithmeticError,OSError) as error:
        parser.exit(2,f'Error: {error}\n')


if __name__=='__main__':
    main()
