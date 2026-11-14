# Independent finite M-convexity audit (2026-11-01)

The solver's Gamma and EVEN Gamma-prime families passed the finite exhaustive
checks below. The additional **fixed-g Gamma-prime family failed**. Fixing g is
different from fixing the internal balances of the reference-flow network.
These are experimental results, not a proof of the unbounded claims.

## Counts and negative result

| Family | Labelled graphs | Labelled sets | Representative pairs checked | Labelled pair equivalent | Failing labelled sets |
|---|---:|---:|---:|---:|---:|
| Gamma | 4,065 | 119,040 | 26,850,940,698 | 1,689,769,021,822 | 0 |
| EVEN Gamma-prime | 153 | 153 | 131,551,396 | 3,666,102,224 | 0 |
| fixed internal Gamma | 4,065 | 119,040 | same Gamma checks | same Gamma checks | 0 |
| fixed internal EVEN Gamma-prime | 153 | 153 | same Gamma-prime checks | same Gamma-prime checks | 0 |
| fixed-g Gamma | 4,065 | 4,058,252 | 865,040,790 | 55,917,072,358 | 0 |
| fixed-g EVEN Gamma-prime | 153 | 5,279 | 3,378,450 | 86,543,792 | **153** |
| NS-FREE Z simplex | n/a (5 dimensions) | 65 | 7,659,899 | n/a | 0 |

The representative sets number 2,328 / 17 / 70,036 / 355 for Gamma,
Gamma-prime, fixed-g Gamma, and fixed-g Gamma-prime respectively. "Labelled
pair equivalent" multiplies each representative's count by its graph orbit
size; it does not mean that repeated isomorphic pair computations were run.
Every nonempty tested set's exchange graph is connected, including the failing
fixed-g-prime slices. Connectivity alone is weaker than symmetric exchange.

All failures occur in the g=0 slice of fixed-g Gamma-prime: 17 representative
sets, representing 153 labelled sets. `failures.json` contains every one of
these representative-set witnesses and its multiplicity. The smallest saved
witness is printed verbatim below (indices are zero based):

```json
{"n":2,"m":2,"edges":[[0,1],[0,1]],"p_in":[0,0],"p_out":[0,0],"x":[-2,0,2,0],"y":[0,-1,0,1],"i":1,"fixed_g":[0,0]}
```

For i=1 the only negative-support candidates are j=0 and j=3. At j=0, the
exchanged vectors violate fixed g=0. At j=3, y+e_i-e_j is zero, which was
deleted. This failure persists in the unbounded fixed-g slice. All 17 saved
failure witnesses were also checked without any degree upper bound.
The original Gamma-prime has additional g values that allow an exchange here;
this example does not refute that solver family.

"Smallest" means first by (n,m,representative edge list,p_in,fixed_g,x,y,i),
using lexicographic vector order. Graph representatives minimize the edge
multiplicity vector over vertex permutations. The sole failing family has
smallest graph n=2,m=2, whose labelling is unique, so representative selection
does not affect the smallest graph. This is not minimization of port L1 norm.

## Exact scope and definitions

All connected, vertex-labelled, loopless multigraphs on 1 <= n <= 5 and
0 <= m <= 6 were enumerated as multiplicities on the unordered vertex pairs.
Edges are indistinguishable parallel copies; vertices are labelled 0,...,n-1.
There are 4,066 labelled graphs, in 111 vertex-relabelling classes. Every labelled
multiplicity vector is visited by the graph generator. The exchange computation
uses one representative of each class, all 2^n incoming parities, and exact orbit
multiplicities. Relabelling permutes coordinates and preserves the axiom and
degree boxes, so this covers all labelled graphs without repeating equivalent
computations. `graphs.json` records each representative and its multiplicity.

The edgeless singleton is connected by convention but never a Timeline component:
Timeline only creates appearances at incident edges. It was tested separately;
its raw rows are in `summary.json` under `supplemental_singleton`. The principal
Gamma counts therefore cover 4,065 actual component graphs.

For each component, every p_in in {0,1}^n is covered, with
p_out[v] = (p_in[v] + deg[v]) mod 2. These are exactly Timeline's attainable
parities: a one-snapshot instance with start=p_in realizes any such choice.
Independent p_out choices violate Timeline's identity and were not tested.
EVEN means **all degrees even AND all p_in zero**, hence all p_out zero.
Gamma-prime is tested only in that case, by removing the all-zero port vector.

Coordinates are `(-alpha[0],..., -alpha[n-1], beta[0],...,beta[n-1])`;
the solver's interleaved storage is a coordinate permutation. Every orientation
of every representative is explicitly enumerated, giving d=in-out, and
g[v]=(d[v]-p_out[v]+p_in[v])/2. All integer alpha,beta satisfying beta-alpha=g
and 0 <= alpha[v],beta[v] <= deg[v] are included, with duplicates removed.

The degree box is a deliberate finite test window, not an upper bound on the
unbounded sets. It includes **every minimal generator**: |g[v]| <= ceil(deg[v]/2),
and the smallest point for a given g has alpha=max(-g,0), beta=max(g,0).
Every other point adds t_v >= 0 to both alpha_v and beta_v. For g=0 after deleting
zero, each primitive nonzero diagonal ray point also fits the degree box because
every vertex of an actual component has degree >= 1. This justifies the chosen
window as covering all orientation balances and primitive rays. It does not
reduce the unbounded exchange axiom to a finite test. Larger boxes (including
deg+2) and arbitrarily large diagonal translations remain unverified.

The exact axiom checked is: for every ordered pair x,y and every i with x_i>y_i,
some j with x_j<y_j satisfies BOTH x-e_i+e_j in S and y+e_i-e_j in S.
The independent C++ checker first computes exact one-unit neighbours by finite
set membership, then quantifies all y using bitsets. No random pairs, convexity
theorem, solver orientation routine, or relaxation is used. Passing sets cover
|S|^2 ordered pairs (including x=y). A failing set stops at its first
lexicographic (x,y,i) witness; its reported count is the conservative ordered-pair
prefix through that witness. Counts of failures mean failing sets, not failing
exchange tuples. Every failing representative set is retained in `failures.json`.

## Fixed balances and connectivity

For the fixed **internal** balance hypothesis, choose the reference orientation
u->v for each listed edge (u<v), let d_R=in_R-out_R, and fix
sigma=(d_R-p_out+p_in)/2. Independently enumerate every 0/1 arc flow phi on the
reversed reference arcs, using boundary=in-out. The possible balances are
g=sigma+boundary(phi). The internal equation
beta-alpha-boundary(phi)=sigma is fixed at every internal vertex while port
coordinates vary. For EVERY graph/parity case the enumerated balance image was
asserted equal to the orientation-enumerated image. Thus `fixed_internal_Gamma`
and `fixed_internal_Gamma_prime` are exactly the previously checked sets; their
summary counts are aliases of those checks, not additional physical runs.
Arbitrary sigma values outside the component-derived family were not tested.

As a distinct, stronger restriction, `fixed_g` intersects Gamma with
beta-alpha=g for each individually realizable g; `fixed_g_prime` removes zero
from that slice when the component is EVEN. These are all tested, including
nonzero-g slices where removing zero has no effect. This interpretation must
not be substituted for the fixed-internal-node hypothesis.

The full graph of valid one-unit exchanges was constructed for every finite
set, and its number of connected components recorded in each raw JSON row.
`disconnected_sets` counts nonempty sets with more than one component. This
checks finite Gamma-prime connectivity; it does not prove connectivity for the
unbounded family. A separate "unique-min lemma" was not tested: no precise
statement of that lemma is specified by this experiment.

## Terminal simplex and solver runs

The NS-FREE terminal set is tested as {z in Z^n: z<=0, sum(z)=-T}, the sign used
at the solver's Z ports. All dimensions 1,...,5 and all forced totals T=0,...,12
are covered: 65 simplices and 7,659,899 ordered pairs, no failures. Each pair and
positive coordinate is explicitly checked by Python set membership. The total
range is finite; larger totals and dimensions were not enumerated.

20,000 seeded random small temporal instances were run through solve_pairflow,
10,000 FIX and 10,000 FREE, using backend='python' with Python assertions active.
The sampler alternates generic random temporal multigraphs and duplicated-edge
even snapshots; see the exact generator and seed 20261101 in the driver.
n=2,...,5, up to four generic timestamps or five even snapshot blocks, arbitrary
small nonnegative starts, and random equal-total FIX ends were sampled. Some
FIX ends are independently sampled orientation endpoints when prefix counts
are nonnegative. These are randomized stress tests, not an exhaustive temporal
instance census or an optimality/correctness comparison against another solver.

The wrappers count calls and delegate to the unchanged original `augment` and
`_reorient`; no assertion is replaced or caught inside an augmentation. An outer
handler records any AssertionError and continues the census. There were **zero**
AssertionErrors. FIX: 2,926 successful augmentations, 825 _reorient calls;
FREE: 3,379 augmentations, 1,392 _reorient calls. Total: **6,305 augmentations**,
2,217 _reorient calls. FIX yielded 1,585 YES / 8,415 NO; FREE 5,508 YES / 4,492 NO.
Early NO cases execute no augmentations, which is why augmentation counts are
reported independently of instance counts. See `random.json` and `random.log`.

The other job concurrently changed pairflow.py to support NS-ENDSET after the
initial stress run. Its Gamma definitions and _reorient assertions were unchanged.
The complete 20,000-instance run was repeated against the current source, with
all six imported solver-module hashes checked before and after the run; these
were stable. The final run gave the identical counts above. The initial run is
preserved as `random-initial.json` / `random-initial.log` with its recorded source
hash. Across BOTH runs: **40,000 instances, 12,610 successful augmentations,
4,434 _reorient calls, zero AssertionErrors** (`solver-total.json`). The seed
was deliberately repeated, so these are 20,000 distinct sampled instances tested
against two source revisions, not 40,000 distinct instances. NS-ENDSET itself
was not sampled.

## Reproduction and validation

Run from the repository root, with existing Python 3 and g++; no dependencies
were installed. Each command below is separately limited to 240 seconds.

```sh
g++ -std=c++17 -O3 -Wall -Wextra experiments/gamma_exchange.cpp -o /tmp/gamma-exchange-fast
timeout 240s python3 experiments/gamma_mconvex.py audit prepare
timeout 240s python3 experiments/gamma_mconvex.py audit run --first 0 --last 45
timeout 240s python3 experiments/gamma_mconvex.py audit run --first 45 --last 77
timeout 240s python3 experiments/gamma_mconvex.py audit run --first 77 --last 89
timeout 240s python3 experiments/gamma_mconvex.py audit run --first 89 --last 100
timeout 240s python3 experiments/gamma_mconvex.py audit run --first 100 --last 111
timeout 240s python3 experiments/gamma_mconvex.py audit simplex
timeout 240s python3 experiments/gamma_mconvex.py audit random
timeout 240s python3 experiments/gamma_mconvex.py audit summarize
timeout 240s python3 experiments/gamma_mconvex.py audit verify
```

`run` writes a graph shard only after that graph finishes and uses a 220-second
batch budget. If a slower machine times out, rerun smaller first/last intervals;
last is exclusive. `summarize` rejects missing shards or missing parity rows.
All 506 sets for n<=3,m<=4 were independently rebuilt in Python and cross-checked
against the original `m_violation` function, including exact witness validation.
The additional direct check validated all 17 saved negative witnesses in the
unbounded fixed-g-prime family.
The legacy double-edge command also passed. Initial pair-by-pair prototype runs
hit their short timeouts; the final bitset implementation and graph shards
supersede those incomplete outputs. A premature summary correctly rejected
incomplete shards; the final summary was rerun after all shards completed.

Raw `graph-*.jsonl` rows, `graphs.json`, `summary.json`, `failures.json`,
`simplex.json`, `random.json`, `verification.json`, and logs provide the evidence.
`solver-total.json` counts both source-revision stress runs.
`manifest.json` records Python/compiler versions and source SHA-256 hashes.
No nscover, report, or thesis source was edited by this audit. The repository's
requested docs/WORKFLOW.md was absent. No external data or services were used.
