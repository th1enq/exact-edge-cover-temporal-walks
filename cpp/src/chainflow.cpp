#include "nscover/chainflow.hpp"
#include "nscover/maxflow.hpp"
#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace nscover {
std::optional<PrefixCaps> prefix_caps(const Instance& inst, const Timeline& tl) {
    PrefixCaps caps(inst.n);
    for (int v = 0; v < inst.n; ++v)
        for (int j = 0; j < checked_index(tl.degree[v].size()); ++j)
            caps[v].push_back(checked_add(tl.before[v][j], tl.degree[v][j]) / 2);
    if (inst.end) {
        Count sum = 0;
        for (Count z : *inst.end) sum = checked_add(sum, z);
        if (sum != inst.walk_count()) return std::nullopt;
        for (int v = 0; v < inst.n; ++v) {
            Count diff = tl.total[v] - (*inst.end)[v];
            if (diff < 0 || diff % 2 != 0 || (tl.degree[v].empty() && diff != 0)) return std::nullopt;
            for (auto& cap : caps[v]) cap = std::min(cap, diff / 2);
        }
    }
    return caps;
}

namespace {
// Slack c_v(j) - B_v(j) over the slots of one vertex: suffix add, first slot
// at or after a position whose slack is zero.
class SlackTree {
public:
    explicit SlackTree(const std::vector<Count>& caps) : size_(checked_index(caps.size())) {
        int width = 1;
        while (width < size_) width *= 2;
        min_.assign(2 * static_cast<std::size_t>(width), std::numeric_limits<Count>::max());
        add_.assign(min_.size(), 0); width_ = width;
        for (int j = 0; j < size_; ++j) min_[width + j] = caps[j];
        for (int k = width - 1; k >= 1; --k) min_[k] = std::min(min_[2 * k], min_[2 * k + 1]);
    }
    void add_suffix(int from, Count delta) { add(1, 0, width_, from, delta); }
    // First j >= from with slack 0, or -1 when every such slot has slack.
    int first_tight(int from) const { return find(1, 0, width_, from, 0); }
    Count minimum() const { return min_[1]; }
    Count at(int j) const {
        Count value = min_[width_ + j];
        for (int k = (width_ + j) / 2; k >= 1; k /= 2) value += add_[k];
        return value;
    }
private:
    int size_, width_ = 1;
    std::vector<Count> min_, add_;
    void add(int k, int lo, int hi, int from, Count delta) {
        // Padding leaves beyond size_ keep their sentinel and are never updated.
        if (hi <= from || lo >= size_) return;
        if (from <= lo && hi <= size_) { min_[k] += delta; add_[k] += delta; return; }
        int mid = (lo + hi) / 2;
        add(2 * k, lo, mid, from, delta); add(2 * k + 1, mid, hi, from, delta);
        min_[k] = std::min(min_[2 * k], min_[2 * k + 1]) + add_[k];
    }
    int find(int k, int lo, int hi, int from, Count above) const {
        if (hi <= from || lo >= size_ || min_[k] + above > 0) return -1;
        if (hi - lo == 1) return lo;
        int mid = (lo + hi) / 2; above += add_[k];
        int left = find(2 * k, lo, mid, from, above);
        return left >= 0 ? left : find(2 * k + 1, mid, hi, from, above);
    }
};

// Which endpoint of every edge takes the tail, together with the per-vertex slack
// of the prefix bounds. An edge with side -1 is not oriented yet.
struct Orientation {
    const Instance& inst;
    const Timeline& tl;
    const PrefixCaps& caps;
    std::vector<SlackTree> slack;
    std::vector<std::vector<std::vector<int>>> at;
    std::vector<int> side, position, remaining;
    std::vector<Count> count;

    Orientation(const Instance& instance, const Timeline& timeline, const PrefixCaps& bounds)
        : inst(instance), tl(timeline), caps(bounds), at(instance.n),
          side(instance.edges.size(), -1), position(instance.edges.size(), 0),
          remaining(instance.n, 0), count(instance.n, 0) {
        slack.reserve(inst.n);
        for (int v = 0; v < inst.n; ++v) {
            slack.emplace_back(caps[v]);
            at[v].resize(caps[v].size());
            remaining[v] = std::accumulate(tl.degree[v].begin(), tl.degree[v].end(), 0);
        }
    }
    int vertex(int e, int k) const { return k == 0 ? inst.edges[e].u : inst.edges[e].v; }
    void place(int e, int k) {
        int v = vertex(e, k), j = tl.slot[e][k];
        side[e] = k; position[e] = checked_index(at[v][j].size()); at[v][j].push_back(e);
        slack[v].add_suffix(j, -1); ++count[v];
    }
    void lift(int e) {
        int k = side[e], v = vertex(e, k), j = tl.slot[e][k];
        auto& list = at[v][j]; int last = list.back();
        list[position[e]] = last; position[last] = position[e]; list.pop_back();
        slack[v].add_suffix(j, 1); --count[v]; side[e] = -1;
    }
    // Greedy step for edges taken in time order: give the tail to an endpoint with
    // slack, preferring the one that has used less of its total allowance. False
    // when neither endpoint has slack, in which case the edge stays unoriented.
    bool greedy(int e) {
        int u = inst.edges[e].u, v = inst.edges[e].v;
        Count su = slack[u].at(tl.slot[e][0]), sv = slack[v].at(tl.slot[e][1]);
        long double urgency_u = static_cast<long double>(caps[u].back() - count[u]) / remaining[u];
        long double urgency_v = static_cast<long double>(caps[v].back() - count[v]) / remaining[v];
        --remaining[u]; --remaining[v];
        if (su <= 0 && sv <= 0) return false;
        place(e, sv <= 0 || (su > 0 && urgency_u >= urgency_v) ? 0 : 1);
        return true;
    }
};

// Breadth-first search for augmenting paths in the residual chain network. Adding
// a tail of w at slot s is possible iff no slot >= s is tight. Otherwise, with T the
// first tight slot >= s, removing any tail of w at a slot <= T restores it: flip
// that edge to its other endpoint and repeat. An entry is (w, s) together with the
// edge that would take its tail there. Several roots can share one search; the
// per-vertex pointer `explored` makes every tail be examined at most once.
class Router {
public:
    struct Entry { int vertex, slot, edge, side, from, level; };
    std::vector<Entry> entries;

    explicit Router(Orientation& orientation)
        : o_(orientation), seen_(o_.inst.edges.size(), 0), explored_(o_.inst.n, -1),
          explored_round_(o_.inst.n, 0) {}
    void begin() { ++round_; entries.clear(); }
    void root(int e) {
        seen_[e] = round_;
        for (int k = 0; k < 2; ++k) entries.push_back({o_.vertex(e, k), o_.tl.slot[e][k], e, k, -1, 0});
    }
    // Processes entry q; true when it can take its tail without displacing another.
    bool expand(int q) {
        const Entry entry = entries[q];
        int w = entry.vertex, tight = o_.slack[w].first_tight(entry.slot);
        if (tight < 0) return true;
        if (explored_round_[w] != round_) { explored_round_[w] = round_; explored_[w] = -1; }
        for (int j = explored_[w] + 1; j <= tight; ++j)
            for (int f : o_.at[w][j]) {
                if (seen_[f] == round_) continue;
                seen_[f] = round_;
                int k = 1 - o_.side[f];
                entries.push_back({o_.vertex(f, k), o_.tl.slot[f][k], f, k, q, entry.level + 1});
            }
        explored_[w] = std::max(explored_[w], tight);
        return false;
    }
private:
    Orientation& o_;
    std::vector<int> seen_, explored_, explored_round_;
    int round_ = 0;
};

std::vector<int> time_order(const Instance& inst) {
    std::vector<int> order(inst.edges.size());
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return inst.edges[a].time < inst.edges[b].time; });
    return order;
}

// Independent check of every prefix bound, then the tails of a complete orientation.
ChainResult finish(const Orientation& o) {
    for (int v = 0; v < o.inst.n; ++v) {
        Count running = 0;
        for (int j = 0; j < checked_index(o.caps[v].size()); ++j) {
            running += checked_index(o.at[v][j].size());
            if (running > o.caps[v][j]) throw std::logic_error("chain orientation exceeded a prefix bound");
        }
    }
    ChainResult result;
    result.complete = true; result.value = checked_index(o.inst.edges.size());
    for (int f = 0; f < checked_index(o.inst.edges.size()); ++f) result.tails.push_back(o.vertex(f, o.side[f]));
    return result;
}

// Edges are oriented in time order, so every tail lies at or before the current
// slot of its vertex and later slots keep their full slack. A stuck edge starts a
// search; one that reaches no slack can never be routed, since the nodes that
// cannot reach the sink stay closed.
ChainResult solve_online(const Instance& inst, const Timeline& tl, const PrefixCaps& caps) {
    Orientation o(inst, tl, caps);
    Router router(o);
    ChainResult result;
    for (int e : time_order(inst)) {
        if (o.greedy(e)) continue;
        ++result.rounds;
        router.begin(); router.root(e);
        int found = -1;
        for (int q = 0; found < 0 && q < checked_index(router.entries.size()); ++q)
            if (router.expand(q)) found = q;
        if (found < 0) return result;
        for (int q = found; q >= 0; q = router.entries[q].from) {
            const auto& entry = router.entries[q];
            if (o.side[entry.edge] >= 0) o.lift(entry.edge);
            o.place(entry.edge, entry.side);
        }
    }
    auto done = finish(o); done.rounds = result.rounds;
    return done;
}

// Same greedy start, but the stuck edges are routed in phases: one search from all
// of them finds the shortest augmenting paths, and edge-disjoint ones are applied.
// A path computed before an earlier one of the same phase may no longer fit, so
// every application is checked against the prefix bounds and undone if it breaks
// one; the search ends only when no path exists from the unoriented edges.
ChainResult solve_phased(const Instance& inst, const Timeline& tl, const PrefixCaps& caps) {
    Orientation o(inst, tl, caps);
    Router router(o);
    ChainResult result;
    std::vector<int> open, used(inst.edges.size(), 0);
    for (int e : time_order(inst)) if (!o.greedy(e)) open.push_back(e);
    struct Move { int edge, from; };
    std::vector<int> path, touched;
    std::vector<Move> moves;
    while (!open.empty()) {
        ++result.rounds;
        router.begin();
        for (int e : open) router.root(e);
        std::vector<int> ends;
        for (int q = 0; q < checked_index(router.entries.size()); ++q) {
            if (!ends.empty() && router.entries[q].level > router.entries[ends[0]].level) break;
            if (router.expand(q)) ends.push_back(q);
        }
        if (ends.empty()) return result;
        int applied = 0;
        for (int end : ends) {
            path.clear();
            bool disjoint = true;
            for (int q = end; q >= 0; q = router.entries[q].from) {
                path.push_back(q); disjoint = disjoint && used[router.entries[q].edge] != result.rounds;
            }
            if (!disjoint) continue;
            moves.clear(); touched.clear();
            for (int q : path) {
                const auto& entry = router.entries[q];
                moves.push_back({entry.edge, o.side[entry.edge]});
                touched.push_back(entry.vertex);
                if (o.side[entry.edge] >= 0) { touched.push_back(o.vertex(entry.edge, o.side[entry.edge])); o.lift(entry.edge); }
                o.place(entry.edge, entry.side);
            }
            bool fits = true;
            for (int v : touched) fits = fits && o.slack[v].minimum() >= 0;
            if (fits) {
                for (const auto& move : moves) used[move.edge] = result.rounds;
                ++applied;
                continue;
            }
            for (auto move = moves.rbegin(); move != moves.rend(); ++move) {
                o.lift(move->edge);
                if (move->from >= 0) o.place(move->edge, move->from);
            }
        }
        if (applied == 0) throw std::logic_error("phase found paths but none could be applied");
        open.erase(std::remove_if(open.begin(), open.end(), [&](int e) { return o.side[e] >= 0; }), open.end());
    }
    auto done = finish(o); done.rounds = result.rounds;
    return done;
}
} // namespace


ChainResult solve_chain(const Instance& inst, const Timeline& tl, const PrefixCaps& input,
                        Backend backend) {
    if (input.size() != static_cast<std::size_t>(inst.n)) throw std::invalid_argument("wrong cap rows");
    auto caps = input;
    for (int v = 0; v < inst.n; ++v) {
        if (caps[v].size() != tl.degree[v].size()) throw std::invalid_argument("wrong cap slots");
        for (Count c : caps[v]) if (c < 0) return {};
        // Equivalent suffix minimum since prefix tail counts cannot decrease.
        for (int j = checked_index(caps[v].size()) - 2; j >= 0; --j)
            caps[v][j] = std::min(caps[v][j], caps[v][j + 1]);
    }
    if (backend == Backend::Online) return solve_online(inst, tl, caps);
    if (backend == Backend::Phased) return solve_phased(inst, tl, caps);
    int m = checked_index(inst.edges.size());
    std::vector<int> base(inst.n);
    std::size_t nodes = 2 + inst.edges.size();
    for (int v = 0; v < inst.n; ++v) { base[v] = checked_index(nodes); nodes += caps[v].size(); }
    MaxFlow net(checked_index(nodes));
    std::vector<int> source_arc(m), choice_u(m), choice_v(m);
    std::vector<std::vector<int>> chain_arc(inst.n);
    for (int e = 0; e < m; ++e) {
        const auto& edge = inst.edges[e];
        source_arc[e] = net.add(0, 2 + e, 1);
        choice_u[e] = net.add(2 + e, base[edge.u] + tl.slot[e][0], 1);
        choice_v[e] = net.add(2 + e, base[edge.v] + tl.slot[e][1], 1);
    }
    for (int v = 0; v < inst.n; ++v)
        for (int j = 0; j < checked_index(caps[v].size()); ++j) {
            int target = j + 1 < checked_index(caps[v].size()) ? base[v] + j + 1 : 1;
            chain_arc[v].push_back(net.add(base[v] + j, target, caps[v][j]));
        }
    Count initial = 0;
    if (backend == Backend::GreedyDinic) {
        std::vector<int> order(m), remaining(inst.n, 0);
        std::iota(order.begin(), order.end(), 0);
        std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return inst.edges[a].time < inst.edges[b].time; });
        std::vector<Count> count(inst.n, 0);
        PrefixCaps tails_at(inst.n);
        for (int v = 0; v < inst.n; ++v) {
            tails_at[v].assign(caps[v].size(), 0);
            remaining[v] = std::accumulate(tl.degree[v].begin(), tl.degree[v].end(), 0);
        }
        for (int e : order) {
            const auto& edge = inst.edges[e];
            int u = edge.u, v = edge.v, ju = tl.slot[e][0], jv = tl.slot[e][1];
            Count su = caps[u][ju] - count[u], sv = caps[v][jv] - count[v];
            // Heuristic only: residual max-flow completes or rejects the assignment.
            long double urgency_u = static_cast<long double>(caps[u].back() - count[u]) / remaining[u];
            long double urgency_v = static_cast<long double>(caps[v].back() - count[v]) / remaining[v];
            --remaining[u]; --remaining[v];
            if (su <= 0 && sv <= 0) continue;
            bool at_u = sv <= 0 || (su > 0 && urgency_u >= urgency_v);
            int tail = at_u ? u : v, j = at_u ? ju : jv;
            ++count[tail]; ++tails_at[tail][j]; ++initial;
            net.push(source_arc[e], 1); net.push(at_u ? choice_u[e] : choice_v[e], 1);
        }
        for (int v = 0; v < inst.n; ++v) {
            Count running = 0;
            for (int j = 0; j < checked_index(caps[v].size()); ++j) {
                running += tails_at[v][j]; net.push(chain_arc[v][j], running);
            }
        }
    }
    ChainResult result;
    result.value = initial + net.flow(0, 1); result.complete = result.value == m;
    if (result.complete)
        for (int e = 0; e < m; ++e)
            result.tails.push_back(net.residual(choice_u[e]) == 0 ? inst.edges[e].u : inst.edges[e].v);
    return result;
}

WalkCounts walk_counts(const Instance& inst, const Timeline& tl, const std::vector<int>& tails) {
    if (tails.size() != inst.edges.size()) throw std::invalid_argument("wrong orientation size");
    WalkCounts result; result.final = inst.start;
    for (const auto& comp : tl.components) {
        std::vector<Count> counts;
        for (int v : comp.vertices) counts.push_back(result.final[v]);
        result.before.push_back(std::move(counts));
        for (int e : comp.edges) {
            const auto& edge = inst.edges[e];
            if (tails[e] != edge.u && tails[e] != edge.v) throw std::invalid_argument("tail is not an endpoint");
            int head = tails[e] == edge.u ? edge.v : edge.u;
            result.final[tails[e]] = checked_add(result.final[tails[e]], -1);
            result.final[head] = checked_add(result.final[head], 1);
        }
    }
    return result;
}
} // namespace nscover
