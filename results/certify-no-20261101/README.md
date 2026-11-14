# NO certificates, 2026-11-01

**Headline: 343 / 435 labelled practice NO cases (78.85%) have independent certificates.**
For the separate 5,000-instance random FIX dataset, it is 3,402 / 3,427 NO cases
(99.27%). These fractions do not count theory-relative certificates as independent.

| Dataset | Instances examined | NO | Independent | Network-relative | Theory-relative | None | Independent / NO |
|---|---:|---:|---:|---:|---:|---:|---:|
| Soundness, mixed FIX/FREE | 20,000 | 9,166 | 9,048 | 0 | 118 | 0 | 98.71% |
| Soundness FIX subset | 10,000 | 6,823 | 6,776 | 0 | 47 | 0 | 99.31% |
| Soundness FREE subset | 10,000 | 2,343 | 2,272 | 0 | 71 | 0 | 96.97% |
| Practice NS-FREE | 999 labels; 435 NO instances solved | 435 | 343 | 0 | 92 | 0 | 78.85% |
| Random FIX coverage | 5,000 | 3,427 | 3,402 | 0 | 25 | 0 | 99.27% |

There were **zero certificates on ground-truth YES instances** in both random runs.
Every generated certificate verified, and every verified random certificate belonged
to an operational brute-force NO instance. The random runs are evidence, not an
exhaustive proof over all possible instances. The 564 labelled practice YES cases
were outside the requested coverage scope and were not solved/certified.

## What the categories mean

* **Independently verified:** a violated necessary arithmetic condition of actual
  walks. Trust the input, integer arithmetic, and the short conservation argument
  below. No pair-flow theory, orientation sufficiency theorem, or max-flow
  implementation must be trusted to check the conclusion.
* **Network-relative:** a deficient network cut without an independent walk-counting
  interpretation would require trusting the network reduction. There are zero such
  records: every chain failure translated to a prefix inequality. The script does
  not emit an unimplemented network-only certificate type.
* **Theory-relative:** the stored pair state is locally valid and its positive ports
  cannot reach a negative port. The verifier independently reconstructs connectivity,
  parity, waiting arcs and exchange arcs and checks closure. Concluding NO still
  requires the pair-flow characterization, M-convexity and exchange/augmentation
  theory. A successful check is **not** an independent NO proof.
* **None:** a labelled/oracle NO for which extraction returned no certificate.
  There were zero in the measured datasets. Skipped transit cases are unmeasured,
  not silently placed in this category.

## Independent counting certificates

Orient each traversed edge in its direction of traversal. If `D_v` is the total
incident-edge count and `B_v` is the number of departures, conservation gives
`end[v] = start[v] + D_v - 2*B_v`. Empty walks preserve the number of tokens.
A FIX certificate records either unequal start/end totals, or a vertex with
`start[v] + D_v - end[v] < 0`, odd balance, or nonzero balance at an isolated
vertex. These are the precise `prefix_caps is None` checks.

For example, a third party checks a vertex certificate by counting its incident
edges, computing that difference, and checking negativity, oddness, or the isolated
vertex condition. `counting()` implements only these arithmetic tests.

## Independent prefix cut certificates

For a vertex and time, write `G_v(t)` for its number of incident edges at or before
that time. Actual token counts cannot be negative after processing a snapshot, so
its departures through that prefix satisfy

```
B_v(t) <= floor((start[v] + G_v(t)) / 2).
```

In FIX also `B_v(t) <= h_v = (start[v] + D_v - end[v])/2` because total departures
are exactly `h_v`. Thus use the minimum of those two bounds in FIX. A prefix cut
selects one appearance time per vertex, or `null` for an empty prefix. Let `F` be
all edges whose time is within **both** endpoints' selected prefixes. Every edge
of `F` must depart from one selected prefix. Hence

```
len(F) <= sum_v bound(v, selected_time[v]).
```

The certificate exhibits the strict reverse inequality. `verify_certificate()`
recounts edges and recomputes bounds directly from plain instance fields. It needs
neither a flow nor a theorem that orientations can be turned into walks.

### Extraction and the saved raw minimum cut

Extraction uses the chain network with source 0, sink 1, edge node `2+e`, and slot
nodes starting at `2+m`, ordered by vertex then its increasing distinct incident
times. Arcs are source -> edge (capacity 1), edge -> its two endpoint slots
(capacity `m+1`), and each slot -> next slot, or sink for the last slot (capacity
its prefix bound). This is `chain-v1-endpoint-m+1` in the JSON. Endpoint capacities
`m+1` preserve feasibility because an edge receives at most one unit. All input
vertex/edge identifiers in certificates are zero-based.

`raw_cut` stores nodes reachable from the source in a maximum flow's residual
network; `flow_value` stores its value. A deficient cut cannot cross an endpoint
arc of capacity `m+1`. For each vertex choose its latest reachable slot. Prefix
capacities are nondecreasing, so replacing all its reachable slot intervals by
that one prefix costs no more than their outgoing boundary capacities. Every
reachable edge node then has both endpoints inside the selected prefixes. The
cut deficiency therefore implies the independent inequality above.

The verifier uses the translated inequality, not the raw cut or claimed flow
value. Those are extraction provenance, not trusted proof fields; checking their
minimality is unnecessary for the NO conclusion. SciPy, when already installed,
accelerates extraction; the existing pure Python flow is the fallback. No
third-party package is needed for verification and no dependency was added.

## Theory-relative state and closure

`x` stores signed pair boundaries, `flow` stores waiting pair counts indexed by
head port, `heads` stores an orientation of each snapshot component, and `d`
stores discrepancies `outflow-inflow-x`. Port order is start vertices, end
vertices, then component IN/OUT pairs in the independently reconstructed
snapshot ordering. The extra hub has index `len(x)`, corresponding to the solver's
NS-FREE hub. `reachable` contains port indices, including the hub when reached.

The checker validates nonnegative waiting flows, all boundary constraints,
component alpha/beta signs, orientation balances with forced parity, the
nonzero condition on even components, the discrepancy equation and a nonempty
positive set. It derives directed reachability inside components to rebuild
exchanges and constructs all waiting and FREE simplex arcs. It checks that the
stored set contains every positive discrepancy, contains no negative discrepancy,
and is closed under every derived arc. It never calls PairFlow's exchange code.
These are conditional state/closure checks; the theoretical implication of
infeasibility remains explicitly unverified.

## Files and reproduction

Run from the repository root, with normal Python (self-test assertions enabled):

```sh
python3 experiments/certify_no.py --self-test
python3 experiments/certify_no.py --coverage
python3 experiments/certify_no.py --verify results/certify-no-20261101/soundness.json
python3 experiments/certify_no.py --verify results/certify-no-20261101/practice.json
python3 experiments/certify_no.py --verify results/certify-no-20261101/random-fix.json
```

Self-test uses seed 20261101, 10,000 FIX and 10,000 FREE instances, `1 <= n <= 5`,
`0 <= m <= 7`, random multiedges, timestamps 0..3 and 0..5 starting tokens.
90% of FIX instances preserve start/end totals; the rest sample another total.
It checks every answer against `nscover.brute.brute_force`, which enumerates
operational token moves without pair-flow or chain theory, and compares the solver
answer too. It tests malformed counting/prefix certificates, invalid pair states,
and reachable sets that omit positives or contain negatives. Random coverage uses
the same distribution, FIX only, seed 20261102, with fresh brute-force labels.

`--verify` constructs plain objects from JSON; it imports no `nscover` module.
Replay was also tested with an import hook that rejects every `nscover` import.
Verifier checks stay enabled under Python optimization. The saved JSON includes
full instances and certificates, so readers can replay without the original data.
Practice metadata records all 999 input hashes and answer labels. Start counts
were capped at degree before solving, as requested; parallel edges are retained.
`summary.json` includes category and certificate-kind counts plus code hashes.

Optional transit coverage was skipped: the two historical transit census files
contain 141 NO rows, but no saved instance snapshots. The transit loader's
strict-time/deduplication defaults changed since the census. Reconstructing and
establishing exact identity was excluded from the cheap-only optional scope.
`transit.json` records the source files, historical counts, and explicit unmeasured
status. No transit certificate fraction is claimed.

All changes for this task are new files under `experiments/` and `results/`.
The solver, thesis, report, branches and external services were left alone.
