import math
import yaml
from scripts.swarm_simulator import SwarmScheduler, simulate


def test_allocation_approximately_matches_policy(tmp_path):
    policy = yaml.safe_load((tmp_path / 'policy.yaml').write_text(
        'routing:\n  allocation:\n    star_ring: 0.8\n    mesh_explorer: 0.2\npartitions:\n  count: 16\n'
    ) or (tmp_path / 'policy.yaml').read_text())
    counts, _ = simulate(policy, steps=5000)
    total = sum(counts.values())
    sr_pct = counts.get('star_ring', 0) / total
    me_pct = counts.get('mesh_explorer', 0) / total
    assert math.isclose(sr_pct, 0.8, rel_tol=0.15)
    assert math.isclose(me_pct, 0.2, rel_tol=0.15)


def test_least_recent_preference():
    policy = {
        'routing': {'allocation': {'star_ring': 0.0, 'mesh_explorer': 1.0}},
        'partitions': {'count': 10},
    }
    sched = SwarmScheduler(policy)
    # First 10 picks should sweep 0..9 without repeats due to least_recent
    seen = set()
    for i in range(10):
        sched.t = i
        _, pid = sched.route_task()
        seen.add(pid)
    assert seen == set(range(10))
