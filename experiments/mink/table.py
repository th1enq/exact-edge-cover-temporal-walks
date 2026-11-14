#!/usr/bin/env python3
"""Merge checked ddmin checkpoints and graph bounds."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'results/mink-20261030'
COLUMNS = ['city', 'n', 'm', 'given_k', 'static_LB', 'snapshot_LB', 'LB', 'UB', 'gap', 'converged', 'proven']


def main():
    rows = json.loads((OUT / 'lb.json').read_text())
    assert len(rows) == 25
    for row in rows:
        state = json.loads((OUT / 'state' / f"{row['city']}.json").read_text())
        assert state['witness'] == 'checked'
        for key in ['n', 'm', 'given_k']:
            assert state[key] == row[key]
        assert state['name'] == row['city']
        assert sum(state['start']) == state['best_k']
        row.update(UB=state['best_k'], converged=state['converged'])
        row['gap'] = row['UB'] - row['LB']
        assert row['gap'] >= 0
        row['proven'] = row['gap'] == 0
    (OUT / 'table.json').write_text(json.dumps(rows, indent=2) + '\n')
    lines = ['| ' + ' | '.join(COLUMNS) + ' |', '| ' + ' | '.join(['---'] * len(COLUMNS)) + ' |']
    for row in rows:
        lines.append('| ' + ' | '.join(str(row[k]).lower() if isinstance(row[k], bool) else str(row[k]) for k in COLUMNS) + ' |')
    (OUT / 'table.md').write_text('\n'.join(lines) + '\n')
    print(f"25 rows; converged={sum(r['converged'] for r in rows)}; proven={sum(r['proven'] for r in rows)}")


if __name__ == '__main__':
    main()
