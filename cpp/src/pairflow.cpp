#include "nscover/solver.hpp"
#include "nscover/maxflow.hpp"
#include <algorithm>
#include <numeric>
#include <queue>
#include <stdexcept>

namespace nscover {
namespace {
constexpr int start_group = -1, end_group = -2;

// Internal state is deliberately local to one solve; no global mutable caches.
class PairFlow {
public:
    PairFlow(const Instance& instance, const Timeline& timeline, const std::vector<int>& tails)
        : inst(instance), tl(timeline) {
        const int n = inst.n;
        std::size_t count = 2 * static_cast<std::size_t>(n);
        for (const auto& c : tl.components) { base.push_back(checked_index(count)); count += 2 * c.vertices.size(); }
        size = checked_index(count); hub = size;
        group.assign(size, start_group); vertex.resize(size);
        for (int v = 0; v < n; ++v) { vertex[v] = vertex[n + v] = v; group[n + v] = end_group; }
        for (const auto& c : tl.components)
            for (int i = 0; i < checked_index(c.vertices.size()); ++i)
                for (int side = 0; side < 2; ++side) {
                    int p = port(c.index, i, side); group[p] = c.index; vertex[p] = c.vertices[i];
                }
        prev.assign(size, -1); next.assign(size, -1);
        for (int v = 0; v < n; ++v) {
            int tail = v;
            for (int c : tl.appear_comp[v]) {
                int i = tl.components[c].local(v), head = port(c, i, 0);
                prev[head] = tail; next[tail] = head; tail = port(c, i, 1);
            }
            prev[n + v] = tail; next[tail] = n + v;
        }
        const auto counts = walk_counts(inst, tl, tails);
        flow.assign(size, 0); x.assign(size, 0); d.assign(size, 0);
        for (int v = 0; v < n; ++v) {
            x[v] = inst.start[v] / 2;
            flow[n + v] = (counts.final[v] - tl.total[v] % 2) / 2;
            x[n + v] = -flow[n + v];
        }
        for (const auto& c : tl.components) {
            std::vector<int> orientation;
            for (int e : c.edges) orientation.push_back(tails[e] == inst.edges[e].u ? inst.edges[e].v : inst.edges[e].u);
            heads.push_back(std::move(orientation));
            for (int i = 0; i < checked_index(c.vertices.size()); ++i) {
                int p = port(c.index, i, 0);
                Count alpha = (counts.before[c.index][i] - c.parity_in(i)) / 2;
                flow[p] = alpha; x[p] = -alpha;
            }
        }
        for (const auto& c : tl.components)
            for (int i = 0; i < checked_index(c.vertices.size()); ++i) {
                int p = port(c.index, i, 1); x[p] = flow[next[p]];
            }
        for (const auto& c : tl.components) {
            bool empty = true;
            for (int i = 0; i < checked_index(c.vertices.size()); ++i) empty = empty && x[port(c.index, i, 0)] == 0;
            if (c.even && empty) {
                ++dead;
                int in = port(c.index, 0, 0), out = port(c.index, 0, 1);
                x[in] = -1; x[out] = 1; d[in] = 1; d[out] = -1; positive.push_back(in);
            }
        }
        adjacency.resize(tl.components.size()); reach.resize(tl.components.size());
        norms.resize(tl.components.size());
        for (int c = 0; c < checked_index(tl.components.size()); ++c) refresh(c);
        parent.assign(static_cast<std::size_t>(size) + 1, -2); kind.assign(parent.size(), 0);
        touched.assign(tl.components.size(), false);
        check_boundary();
    }

    // One augmentation costs O(ports visited); only the final check scans all ports.
    bool augment() {
        std::queue<int> queue;
        for (int p : positive) if (d[p] > 0) { parent[p] = -1; visited.push_back(p); queue.push(p); }
        int target = -1;
        auto visit = [&](int a, int b, int type) {
            if (target >= 0 || parent[b] != -2) return;
            parent[b] = a; kind[b] = type; visited.push_back(b);
            if (b != hub && d[b] < 0) target = b;
            else queue.push(b);
        };
        while (!queue.empty() && target < 0) {
            int a = queue.front(); queue.pop();
            if (a == hub) {
                for (int v = 0; v < inst.n; ++v) visit(a, inst.n + v, 5);
                continue;
            }
            if (prev[a] >= 0) visit(a, prev[a], 1);
            if (next[a] >= 0 && flow[next[a]] > 0) visit(a, next[a], 2);
            int c = group[a];
            if (c >= 0) {
                const auto& comp = tl.components[c]; int side_i = (a - base[c]) % 2;
                if (side_i == 1 || x[a] < 0) {
                    int norm = norms[c];
                    int local = (a - base[c]) / 2;
                    for (int w : reachable(c, local)) for (int side_j = 0; side_j < 2; ++side_j) {
                        int b = port(c, w, side_j);
                        if (a == b || (side_j == 1 && x[b] <= 0)) continue;
                        if (comp.even && norm + (side_i == 0 ? -1 : 1) + (side_j == 0 ? 1 : -1) == 0) continue;
                        visit(a, b, 3);
                    }
                }
            }
            if (!inst.end && c == end_group && x[a] <= -1) visit(a, hub, 4);
        }
        if (target < 0) {
            reachable_ports.clear();
            for (int p : visited) if (p < size) reachable_ports.push_back(p);
            std::sort(reachable_ports.begin(), reachable_ports.end());
            return false;
        }
        std::vector<int> changed, components;
        int b = target;
        while (parent[b] >= 0) {
            int a = parent[b];
            for (int p : {a, b}) if (p < size) { changed.push_back(p); if (prev[p] >= 0) changed.push_back(prev[p]); }
            switch (kind[b]) {
                case 1: ++flow[a]; break;
                case 2: --flow[b]; break;
                case 3:
                    ++x[a]; --x[b];
                    if (!touched[group[a]]) { touched[group[a]] = true; components.push_back(group[a]); }
                    break;
                case 4: ++x[a]; break;
                case 5: --x[b]; break;
                default: throw std::logic_error("unknown exchange type");
            }
            b = a;
        }
        --d[b]; ++d[target]; changed.push_back(b); changed.push_back(target);
        for (int p : visited) parent[p] = -2;
        visited.clear();
        std::sort(components.begin(), components.end());
        for (int c : components) { touched[c] = false; reorient(c); refresh(c); }
        ++augmentations;
        if (augmentations > dead) throw std::logic_error("augmentation bound violated");
        // Other ports keep their flow, x and d, hence their boundary equation.
        for (int p : changed) check_port(p);
        return true;
    }

    bool unfinished() const { return std::any_of(positive.begin(), positive.end(), [this](int p) { return d[p] > 0; }); }
    std::vector<int> tails() const {
        std::vector<int> result(inst.edges.size());
        for (const auto& c : tl.components)
            for (int j = 0; j < checked_index(c.edges.size()); ++j) {
                int e = c.edges[j]; result[e] = heads[c.index][j] == inst.edges[e].u ? inst.edges[e].v : inst.edges[e].u;
            }
        return result;
    }
    int dead = 0, augmentations = 0;
    std::vector<int> reachable_ports;
private:
    const Instance& inst;
    const Timeline& tl;
    int size = 0, hub = 0;
    std::vector<int> base, group, vertex, prev, next;
    std::vector<Count> flow, x, d;
    std::vector<std::vector<int>> heads;
    // Ports with an initial positive discrepancy; d only decreases there.
    std::vector<int> positive;
    // Search state, reset after each augmentation through `visited`.
    std::vector<int> parent, kind, visited;
    std::vector<bool> touched;

    // Directed reachability inside a component depends only on its orientation,
    // so cached answers stay valid until refresh() after reorient().
    std::vector<std::vector<std::vector<int>>> adjacency, reach;
    // Sum of |x| over the ports of an even component, saturated at 3: only
    // whether an exchange (changing it by at most 2) reaches 0 matters.
    std::vector<int> norms;

    int port(int c, int local, int side) const { return base[c] + 2 * local + side; }
    void refresh(int c) {
        const auto& comp = tl.components[c];
        adjacency[c].clear(); reach[c].clear(); norms[c] = 0;
        if (comp.even) for (std::size_t j = 0; j < 2 * comp.vertices.size(); ++j) {
            Count value = x[base[c] + j];
            Count magnitude = value < 0 ? -value : value;
            norms[c] = std::min(3, norms[c] + static_cast<int>(std::min<Count>(3, magnitude)));
        }
    }
    const std::vector<int>& reachable(int c, int local) {
        const auto& comp = tl.components[c];
        int vertices = checked_index(comp.vertices.size());
        if (adjacency[c].empty()) {
            adjacency[c].resize(vertices); reach[c].resize(vertices);
            for (int j = 0; j < checked_index(comp.edges.size()); ++j) {
                const auto& e = inst.edges[comp.edges[j]]; int head = heads[c][j];
                int tail = head == e.u ? e.v : e.u;
                adjacency[c][comp.local(tail)].push_back(comp.local(head));
            }
        }
        auto& answer = reach[c][local];
        if (answer.empty()) {
            std::vector<bool> seen(vertices, false); std::vector<int> stack{local}; seen[local] = true;
            while (!stack.empty()) {
                int a = stack.back(); stack.pop_back();
                for (int b : adjacency[c][a]) if (!seen[b]) { seen[b] = true; stack.push_back(b); }
            }
            for (int w = 0; w < vertices; ++w) if (seen[w]) answer.push_back(w);
        }
        return answer;
    }
    void check_port(int p) const {
        if (flow[p] < 0) throw std::logic_error("negative waiting flow");
        Count boundary = next[p] < 0 ? 0 : flow[next[p]];
        if (prev[p] >= 0) boundary -= flow[p];
        if (boundary - x[p] != d[p]) throw std::logic_error("pair-flow boundary invariant failed");
    }
public:
    void check_boundary() const { for (int p = 0; p < size; ++p) check_port(p); }
private:
    void reorient(int c) {
        const auto& comp = tl.components[c]; std::vector<Count> indegree;
        bool zero = true;
        for (int i = 0; i < checked_index(comp.vertices.size()); ++i) {
            Count alpha = -x[port(c, i, 0)], beta = x[port(c, i, 1)];
            if (alpha < 0 || beta < 0) throw std::logic_error("exchange left nonnegative box");
            zero = zero && alpha == 0 && beta == 0;
            Count g = beta - alpha;
            // Local realisable g is bounded by the degree, even for huge counts.
            if (g < -static_cast<Count>(comp.degree[i]) || g > comp.degree[i])
                throw std::logic_error("exchange left local degree bounds");
            Count twice = comp.degree[i] + 2 * g + comp.parity_out(i) - comp.parity_in(i);
            if (twice % 2 != 0) throw std::logic_error("nonintegral indegree");
            indegree.push_back(twice / 2);
        }
        if (comp.even && zero) throw std::logic_error("exchange emptied an even component");
        std::vector<std::pair<int, int>> pairs;
        for (int e : comp.edges) pairs.emplace_back(inst.edges[e].u, inst.edges[e].v);
        auto orientation = orient_with_indegree(comp.vertices, pairs, indegree);
        if (!orientation) throw std::logic_error("exchange left realisable set");
        heads[c] = std::move(*orientation);
    }
};
} // namespace

Result solve_pairflow(const Instance& inst, Backend backend) {
    Timeline tl(inst); Result result;
    const auto caps = prefix_caps(inst, tl);
    if (!caps) { result.reason = "counting"; return result; }
    const auto root = solve_chain(inst, tl, *caps, backend); result.flows = 1;
    if (!root.complete) { result.reason = "chain network"; return result; }
    PairFlow state(inst, tl, root.tails); result.dead = state.dead;
    while (state.unfinished()) {
        if (!state.augment()) {
            result.augmentations = state.augmentations;
            result.reason = "no augmenting path";
            result.reachable_ports = std::move(state.reachable_ports); return result;
        }
    }
    state.check_boundary();
    result.status = Status::Yes; result.tails = state.tails(); result.augmentations = state.augmentations;
    return result;
}
} // namespace nscover
