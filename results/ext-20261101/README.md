# NS-ENDSET experiments, 2026-11-01

Reproduce from the repository root (Python standard library plus the existing
optional SciPy backend; no new dependencies):

```sh
python3 -m unittest discover -s tests -v
python3 experiments/endset_study.py A
python3 experiments/endset_study.py B
python3 experiments/endset_study.py C
python3 experiments/endset_study.py D
```

`python3 experiments/min_walks_small_S.py` also runs C. Each full experiment has
a 290-second watchdog. The recorded runs took 50.06, 49.43, 83.21, and 17.98
seconds respectively. B/C/D ran concurrently (A was rerun after the final hub
membership optimization), so timings can include CPU contention
and are illustrative, not controlled benchmarks. `pytest` is unavailable
(`No module named pytest`); the repository's documented unittest command passed
all 17 tests. `environment.json` records interpreter/backend information.

The new field follows the existing positional fields, including `name`, and is
omitted from JSON unless set. `end` and `end_set` are mutually exclusive. Empty
T is allowed: it permits only zero walks. Empty walks also must end in T.
`free_end()` explicitly removes either kind of end constraint.

The chain warm start uses exact lower/upper bounds on final tail counts
`(start[v] + degree[v])/2` outside T. Odd parity and stranded isolated tokens
are rejected. Proper subsets use lower-bound circulation with the existing
Python Dinic; the requested chain backend applies unchanged to NS-FREE,
NS-FIX, and T=V. The pair-flow hub exchanges only among T. Its end domain is
the subset simplex times singleton zeros outside T, so the existing M-convex
exchange argument applies; experiments are evidence, not a new proof.

## A: end-set agreement (`a.json`)

20,000 random instances, n=1..5, m=0..7 (no edges when n=1), timestamps 1..3,
k=0..3. The four modes full T, singleton T, empty T, and independent random
membership each contribute 5,000 cases. Solver counts: **6,986 YES / 13,014 NO**.
**Zero oracle disagreements**. Every YES witness was constructed and checked.
On all 20,000 underlying instances, T=V exactly matched the old NS-FREE
`Result`, including tails, flow count, and stats, not just feasibility.

## B: start monotonicity (`b.json`)

20,000 independently generated NS-FREE instances with the same bounds:
**13,256 YES / 6,744 NO**. All vertices of every YES instance were tested after
adding one token: **33,734 implications, zero violations**, and zero solver/oracle
disagreements for the bases or additions. Added vectors can have k=4.

For proper T, the absolute smallest counterexample has n=1, m=0, T=empty:
start (0) is YES and (1) is NO. If both edges and T must be nonempty, the
smallest is n=2, one edge (0,1,1), T={0}: start (0,1) is YES and adding at
vertex 1 gives (0,2), NO. One traversal moves only one of the two tokens.
These minimize (m,n,k); a nonempty edge set requires k>=1 and n>=2. The script
also searches the small cases exhaustively in canonical order (143 candidates
examined before finding the nonempty example). This assumes n>=1.

## C: minimum starts supported on S (`c.json`)

`min_walks(graph,S)` checks the complete product of degree-bounded ranges with
pair-flow and returns the smallest feasible sum or None. In **2,000 random
graphs** (n<=5, m<=5, times 1..3), sizes 1/2/3 occurred 667/667/666 times.
The independent operational oracle checked **23,389 vectors**, including vectors
above individual degree bounds: **zero disagreements**. Oracle vectors have
total <=m, which is exhaustive for the minimum: discard all empty walks from
any solution, leaving at most m nonempty walks. For m=0 the optimum is zero.

Timing samples are random multigraphs on six vertices with one timestamp.
Each cell below is enumeration seconds (excluding interpreter/import startup).
Each size/m pair uses one separate random graph; no repetitions or confidence
intervals. The enumeration tests every vector even after finding an optimum.

| m | size 1 | size 2 | size 3 |
|---:|---:|---:|---:|
| 10 | 0.0086 | 0.0421 | 0.0532 |
| 30 | 0.0044 | 0.0876 | 0.8471 |
| 100 | 0.0560 | 1.8814 | censored |
| 300 | 0.4140 | censored | censored |

Each censored cell exceeded a **12-second wall limit including process startup**;
the JSON `seconds_at_least` field refers to this wall limit, not pure enumeration
time. No answer or completed runtime is claimed for these cells. The largest
box contains 991,900 vectors. In general the number of solver calls is exactly
the product of (degree(v)+1) over S, at most (m+1)^|S|. Completed timings and
censored observations show the cost of this exhaustive implementation; they
do not establish an empirical asymptotic exponent.

## D: augmentation family (`d.json`)

Disjoint copies of the saved five-vertex, seven-edge gadget, shifting vertex
labels and timestamps per copy. Every copy has two starting tokens and a
walk-free even component in the initial chain orientation. All final solutions
were checked as operational walk covers; the one-copy gadget was also checked
by brute force. D counts **pair-flow** augmentations, excluding chain-flow work.

| m | 7 | 14 | 35 | 70 | 140 | 350 | 700 | 1400 | 2996 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D | 1 | 2 | 5 | 10 | 20 | 50 | 100 | 200 | 428 |

Thus D=m/7 on every tested member, with D equal to the initial dead-component
count. The largest solve took 15.26 seconds in the concurrent run. This family
uses parallel edges and is disconnected; no connected/simple family is claimed.

Random streams use seed 20261101 for A, +1 for B, +2 for C correctness,
and +3 for C scaling. `disagreements`, `violations`, and
`full_set_result_disagreements` contain full instances if a future run fails.
Missing repository `docs/WORKFLOW.md` was noted; no harness guidance was changed.
