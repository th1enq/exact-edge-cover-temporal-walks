#!/usr/bin/env python3
"""Recheck three converged witnesses and smallest-city local minimality."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/mink-20261030'


def solve(data):
    run = subprocess.run([str(ROOT / 'cpp/build/nscover_solve'), '--summary'],
                         input=json.dumps(data), text=True, capture_output=True,
                         timeout=45, check=True)
    return json.loads(run.stdout)


def main():
    rows = json.loads((OUT / 'table.json').read_text())
    converged = sorted((r for r in rows if r['converged']), key=lambda r: (r['m'], r['n'], r['city']))
    if not converged:
        raise RuntimeError('no converged city available')
    target = OUT / 'validation'
    target.mkdir(exist_ok=True)
    report = {'smallest_by': 'edge count m, then n, then city', 'required_witnesses': 3,
              'witnesses': [], 'single_removals': []}
    for row in converged[:3]:
        city = row['city']
        data = json.loads((OUT / 'inst' / f'{city}.json').read_text())
        state = json.loads((OUT / 'state' / f'{city}.json').read_text())
        data['start'] = state['start']
        path = target / f'{city}.json'
        path.write_text(json.dumps(data) + '\n')
        run = subprocess.run([str(ROOT / 'cpp/build/nscover_solve'), str(path), '--summary'],
                             capture_output=True, text=True, check=True, timeout=45)
        result = json.loads(run.stdout)
        assert result['status'] == 'YES' and result['witness'] == 'checked'
        report['witnesses'].append(dict(city=city, **result))
        print(f'{city}: YES, witness checked', flush=True)
    smallest = min(rows, key=lambda r: (r['m'], r['n'], r['city']))
    assert smallest['converged'], 'smallest city must have converged'
    data = json.loads((target / f"{smallest['city']}.json").read_text())
    report['local_minimality_city'] = smallest['city']
    # Tokens at the same vertex produce identical vectors: check once per
    # positive coordinate, and record the multiplicity covered by that check.
    for v, count in enumerate(data['start']):
        if not count:
            continue
        data['start'][v] -= 1
        result = solve(data)
        assert result['status'] != 'YES', (v, result)
        report['single_removals'].append(dict(vertex=v, multiplicity=count, **result))
        data['start'][v] += 1
    report['tokens_covered'] = sum(r['multiplicity'] for r in report['single_removals'])
    report['passed'] = len(report['witnesses']) == report['required_witnesses']
    (target / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"{smallest['city']}: all {len(report['single_removals'])} distinct single-removal vectors non-YES; {report['tokens_covered']} tokens covered", flush=True)
    if not report['passed']:
        raise SystemExit(f"Incomplete: only {len(converged)} converged cities; three required")


if __name__ == '__main__':
    main()
