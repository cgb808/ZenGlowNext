#!/usr/bin/env python3
import argparse
import random
import yaml
from collections import defaultdict, deque
from typing import Tuple, Dict


class SwarmScheduler:
    def __init__(self, policy: dict):
        self.policy = policy
        self.alloc = policy["routing"]["allocation"]
        self.partitions = int(policy.get("partitions", {}).get("count", 32))
        self.least_recent = deque(range(self.partitions))
        self.last_used = {i: -1 for i in range(self.partitions)}
        self.t = 0

    def pick_partition(self, explorer: bool) -> int:
        # Explorer: pick least-recent first
        if explorer and self.least_recent:
            return self.least_recent.popleft()
        # Non-explorer: inverse-recency weighting
        scores = []
        for pid in range(self.partitions):
            age = self.t - self.last_used[pid]
            scores.append(max(1.0, age))
        total = sum(scores)
        r = random.random() * total
        cum = 0.0
        for pid, s in enumerate(scores):
            cum += s
            if r <= cum:
                return pid
        return self.partitions - 1

    def route_task(self) -> Tuple[str, int]:
        # 80/20 split default (star_ring primary vs mesh_explorer)
        r = random.random()
        explorer = r >= self.alloc.get("star_ring", 0.8)
        pid = self.pick_partition(explorer)
        self.last_used[pid] = self.t
        try:
            self.least_recent.remove(pid)
        except ValueError:
            pass
        return ("mesh_explorer" if explorer else "star_ring", pid)


def simulate(policy: dict, steps: int = 1000):
    sched = SwarmScheduler(policy)
    counts: Dict[str, int] = defaultdict(int)
    part_hits: Dict[int, int] = defaultdict(int)
    for i in range(steps):
        sched.t = i
        swarm, pid = sched.route_task()
        counts[swarm] += 1
        part_hits[pid] += 1
    return counts, part_hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="configs/swarm_policy.yaml")
    ap.add_argument("--steps", type=int, default=1000)
    args = ap.parse_args()

    with open(args.policy, "r") as f:
        policy = yaml.safe_load(f)
    counts, part_hits = simulate(policy, steps=args.steps)
    total = sum(counts.values())
    print("[swarm] allocation:")
    for k, v in counts.items():
        pct = (100.0 * v / total) if total else 0.0
        print(f"  {k}: {v} ({pct:.1f}%)")
    cold = sorted(part_hits.items(), key=lambda x: x[1])[:8]
    hot = sorted(part_hits.items(), key=lambda x: -x[1])[:8]
    print("[swarm] coldest partitions:", cold)
    print("[swarm] hottest partitions:", hot)


if __name__ == "__main__":
    main()
