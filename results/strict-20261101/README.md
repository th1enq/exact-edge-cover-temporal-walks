# Strict temporal exact edge-cover study

The experiment uses the strict S model: one edge per token per timestamp,
each edge exactly once, waiting and empty walks allowed. FREE leaves endpoints
unconstrained; FIX prescribes all end counts. There are no loops.

| Class | Mode | N | Oracle YES | R1 YES | Gap | R1+parity gap |
|---|---|---:|---:|---:|---:|---:|
| general | FREE | 20000 | 9101 | 9690 | 589 | 460 |
| general | FIX | 20000 | 2513 | 5685 | 3172 | 61 |
| proper | FREE | 20000 | 11129 | 11996 | 867 | 540 |
| proper | FIX | 20000 | 3119 | 7218 | 4099 | 14 |
| forest | FREE | 20000 | 8767 | 9261 | 494 | 474 |
| forest | FIX | 20000 | 2869 | 6723 | 3854 | 61 |
| cycle | FREE | 20000 | 3513 | 3717 | 204 | 204 |
| cycle | FIX | 20000 | 509 | 2854 | 2345 | 144 |
| simple | FREE | 20000 | 11952 | 12704 | 752 | 534 |
| simple | FIX | 20000 | 3665 | 6550 | 2885 | 44 |

N counts generated instances, with replacement, in each class and mode; FREE
and FIX share the same graph and start vector. Oracle YES counts exact feasible
instances. R1 YES counts feasible integral lower-bound circulations. Gap counts
R1 YES and oracle NO. R1+parity gap counts false positives after the additional
necessary endpoint-parity test. These are generator-specific frequencies, not
uniform graph-class probabilities. Classes overlap.

Seed: 20261101. Runtime: 125.932 seconds.
Oracle/count DP versus independent labeled-token brute force: 5000
random decisions plus 1338 exhaustive decisions; zero mismatches.
R1 versus independently simulated labeled tokens allowed same-side gadget exits:
5000 random decisions; zero mismatches.
Oracle YES implies R1 YES violations: 0.
Every sampled graph is checked for its claimed class. Every exact YES is also
checked against endpoint parity.

## Sampling scope

n is uniform in 2..5 (3..5 for cycle); k is uniform in 0..4. Starts and FIX
ends independently place k labeled tokens at uniformly chosen vertices, so
count vectors are multinomial, not uniformly distributed. General graphs use
m uniform in 0..8 and independent unordered endpoint pairs with replacement,
then independent timestamps uniform in 0..3. Simple graphs sample globally
distinct unordered pairs without replacement, m uniform in 0..min(8,n choose 2),
then timestamps uniform in 0..3. Thus simple means no repeated pair even across
timestamps, a stronger restriction than snapshot simplicity.

Proper and forest generators select 1..4 candidate timestamps. At each time,
shuffle all unordered pairs and accept each eligible pair with probability 1/2,
subject to the matching/acyclic restriction and total m <= 8. Empty candidate
snapshots have no effect. The cycle generator chooses 1..4 candidate timestamps,
each with a randomly ordered simple cycle on 3..min(n,remaining edge budget)
vertices plus isolates; stop once m >= 6, ensuring m <= 8. Cycles are length
at least three, so two parallel edges are not sampled as a cycle. Across times,
pairs may repeat outside the simple class. No conditioning on feasibility is used.

## Small gap witnesses

The following witnesses are smallest under the recorded census ordering
(m,n,k,number of timestamps,edges,start,end), in the exhaustive domain
n=1..3, m=0..2, k=0..2; all canonical timestamp assignments and terminal compositions. Isomorphic vertices are not quotiented.

FIX: `{"edges": [{"time": 0, "u": 0, "v": 1}], "end": [0, 1], "num_vertices": 2, "start": [0, 1]}`

FREE: `{"edges": [{"time": 0, "u": 0, "v": 1}, {"time": 1, "u": 0, "v": 2}], "num_vertices": 3, "start": [1, 0, 0]}`

For FREE, one token begins at the center of two edges at successive
timestamps. A strict traversal of the first edge strands it at a leaf, while
R1 permits it to return to the center through the same edge gadget and use
the second edge. For FIX, a single edge with one token required to end at its
starting endpoint already exposes the same-side exit allowed by R1.

R1 is not exact even on proper graphs: both witnesses have matching snapshots.
Polynomial solvability of the proper class does not imply exactness of this
particular relaxation. The cited AAAI corollary is user-supplied context and was
not independently verified here.

## Construction and additional condition

Each edge gadget has a split arc with lower=upper=1 and four endpoint port
arcs. Each vertex has a wait arc from before to after each incident timestamp,
wait arcs between successive incident timestamps, and exact start supply.
The final arc has exact FIX demand or free capacity; isolated vertices have
direct waiting paths. k replaces infinity, since only k tokens circulate.
An integral lower-bound circulation is reduced to integral max flow with
super source/sink and an exact k-unit sink-to-source return arc.
Every strict traversal maps to a cross-side gadget traversal, giving necessity.
The count oracle tests all simultaneous orientations with departures bounded
by pre-snapshot token counts; this prevents reuse of snapshot arrivals.
The independent brute force assigns distinct labeled tokens to snapshot edges.

Endpoint parity requires degree(v) = start(v)+end(v) mod 2. For FREE this
means the sum of required end parities is at most k (and the remaining count
is even). R1 plus this condition still has false positives: see parity_failure
examples below, reproduced verbatim from the machine-readable results.
No condition tested closed all gaps, so no exactness CONJECTURE is proposed
and the conditional further 20,000-instance conjecture test does not apply.
No tighter plain-flow gadget was established. Simply using separate directed
cross arcs loses the shared exactly-one-use constraint on an undirected edge;
it is not an asserted replacement.

parity_failure/general/FREE: `{"edges": [{"time": 3, "u": 0, "v": 1}, {"time": 0, "u": 0, "v": 3}, {"time": 1, "u": 1, "v": 2}, {"time": 3, "u": 2, "v": 4}, {"time": 2, "u": 2, "v": 4}, {"time": 2, "u": 0, "v": 4}], "num_vertices": 5, "start": [0, 0, 1, 1, 0]}`

parity_failure/general/FIX: `{"edges": [{"time": 1, "u": 0, "v": 1}, {"time": 1, "u": 0, "v": 1}, {"time": 1, "u": 0, "v": 1}], "end": [1, 2], "num_vertices": 2, "start": [0, 3]}`

parity_failure/proper/FREE: `{"edges": [{"time": 0, "u": 1, "v": 2}, {"time": 1, "u": 0, "v": 1}], "num_vertices": 4, "start": [0, 1, 0, 2]}`

parity_failure/proper/FIX: `{"edges": [{"time": 0, "u": 0, "v": 1}, {"time": 0, "u": 2, "v": 4}, {"time": 1, "u": 2, "v": 3}, {"time": 1, "u": 1, "v": 4}, {"time": 2, "u": 1, "v": 2}, {"time": 2, "u": 3, "v": 4}, {"time": 3, "u": 3, "v": 4}, {"time": 3, "u": 0, "v": 1}], "end": [1, 0, 0, 1, 0], "num_vertices": 5, "start": [1, 0, 1, 0, 0]}`

parity_failure/forest/FREE: `{"edges": [{"time": 0, "u": 1, "v": 3}, {"time": 0, "u": 2, "v": 4}, {"time": 0, "u": 0, "v": 3}, {"time": 0, "u": 1, "v": 4}, {"time": 1, "u": 1, "v": 4}, {"time": 1, "u": 0, "v": 2}, {"time": 1, "u": 1, "v": 3}, {"time": 1, "u": 2, "v": 3}], "num_vertices": 5, "start": [1, 1, 1, 0, 1]}`

parity_failure/forest/FIX: `{"edges": [{"time": 1, "u": 1, "v": 2}, {"time": 1, "u": 0, "v": 2}, {"time": 2, "u": 0, "v": 1}, {"time": 3, "u": 1, "v": 2}, {"time": 3, "u": 0, "v": 2}], "end": [1, 1, 0], "num_vertices": 3, "start": [0, 0, 2]}`

parity_failure/cycle/FIX: `{"edges": [{"time": 0, "u": 2, "v": 1}, {"time": 0, "u": 1, "v": 0}, {"time": 0, "u": 0, "v": 2}, {"time": 1, "u": 1, "v": 0}, {"time": 1, "u": 0, "v": 2}, {"time": 1, "u": 2, "v": 1}], "end": [1, 0, 2], "num_vertices": 3, "start": [1, 2, 0]}`

parity_failure/cycle/FREE: `{"edges": [{"time": 0, "u": 2, "v": 0}, {"time": 0, "u": 0, "v": 1}, {"time": 0, "u": 1, "v": 3}, {"time": 0, "u": 3, "v": 2}, {"time": 1, "u": 3, "v": 0}, {"time": 1, "u": 0, "v": 1}, {"time": 1, "u": 1, "v": 4}, {"time": 1, "u": 4, "v": 3}], "num_vertices": 5, "start": [2, 1, 0, 1, 0]}`

parity_failure/simple/FREE: `{"edges": [{"time": 2, "u": 1, "v": 4}, {"time": 0, "u": 2, "v": 4}, {"time": 1, "u": 1, "v": 2}, {"time": 2, "u": 3, "v": 4}, {"time": 3, "u": 0, "v": 1}, {"time": 1, "u": 0, "v": 3}], "num_vertices": 5, "start": [0, 0, 1, 1, 1]}`

parity_failure/simple/FIX: `{"edges": [{"time": 1, "u": 0, "v": 2}, {"time": 1, "u": 1, "v": 2}, {"time": 2, "u": 0, "v": 1}], "end": [1, 1, 0], "num_vertices": 3, "start": [1, 1, 0]}`

## Limitations

No large instances, loops, nonintegral supplies, more than four tokens, or more
than eight edges were tested. Random sampling does not exhaust the listed
classes. FIX experiments use equal start/end totals; regression checks also
cover unequal totals. The small census exhausts only its stated bounds and
canonical time labels; no general minimality theorem is claimed. No other
flow relaxations or systematic search over extra conditions was performed.
No complexity theorem or external corollary was verified. no complexity claim is made.

Reproduce: `python3 experiments/strict/relax.py --self-test`.
This rewrites only study.json and README.md in the default results directory.
Individual instances can be checked with `--instance path/to/instance.json`.
