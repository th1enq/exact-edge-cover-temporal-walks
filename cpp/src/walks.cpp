#include "nscover/walks.hpp"
#include <algorithm>
#include <limits>
#include <utility>

namespace nscover {
namespace {
std::vector<int> euler_circuit(int start, int vertices, const std::vector<std::pair<int, int>>& arcs) {
    std::vector<std::vector<int>> out(vertices);
    for (int a = 0; a < checked_index(arcs.size()); ++a) out[arcs[a].first].push_back(a);
    std::vector<std::pair<int, int>> stack{{start, -1}};
    std::vector<int> circuit;
    while (!stack.empty()) {
        auto top = stack.back();
        if (!out[top.first].empty()) {
            int arc = out[top.first].back(); out[top.first].pop_back();
            stack.emplace_back(arcs[arc].second, arc);
        } else {
            stack.pop_back(); if (top.second >= 0) circuit.push_back(top.second);
        }
    }
    std::reverse(circuit.begin(), circuit.end());
    if (circuit.size() != arcs.size()) throw InfeasibleOrientation("component orientation is not connected");
    return circuit;
}
} // namespace

std::vector<Walk> build_walks(const Instance& inst, const std::vector<int>& tails) {
    Timeline tl(inst);
    if (tails.size() != inst.edges.size()) throw InfeasibleOrientation("wrong orientation size");
    for (int e = 0; e < checked_index(tails.size()); ++e)
        if (tails[e] != inst.edges[e].u && tails[e] != inst.edges[e].v)
            throw InfeasibleOrientation("tail is not an endpoint");
    // Explicit witnesses necessarily take O(k+m) memory, including empty walks.
    checked_index(static_cast<std::size_t>(inst.walk_count()));
    std::vector<Walk> walks;
    std::vector<std::vector<int>> here(inst.n);
    for (int v = 0; v < inst.n; ++v) for (Count j = 0; j < inst.start[v]; ++j) {
        here[v].push_back(checked_index(walks.size())); walks.push_back({v, {}});
    }
    for (const auto& comp : tl.components) {
        int vertices = checked_index(comp.vertices.size()), real = checked_index(comp.edges.size());
        std::vector<std::pair<int, int>> arcs;
        std::vector<int> surplus(vertices, 0), givers, takers;
        for (int e : comp.edges) {
            const auto& edge = inst.edges[e];
            int tail = comp.local(tails[e]), head = comp.local(tails[e] == edge.u ? edge.v : edge.u);
            arcs.emplace_back(tail, head); ++surplus[tail]; --surplus[head];
        }
        for (int i = 0; i < vertices; ++i) {
            for (int j = 0; j < surplus[i]; ++j) givers.push_back(i);
            for (int j = 0; j < -surplus[i]; ++j) takers.push_back(i);
        }
        for (std::size_t j = 0; j < givers.size(); ++j) arcs.emplace_back(takers[j], givers[j]);
        std::vector<std::vector<int>> trails;
        if (!givers.empty()) {
            auto circuit = euler_circuit(takers.front(), vertices, arcs);
            auto cut = std::find_if(circuit.begin(), circuit.end(), [real](int a) { return a >= real; });
            std::rotate(circuit.begin(), cut + 1, circuit.end());
            std::vector<int> trail;
            for (int a : circuit) {
                if (a >= real) { trails.push_back(std::move(trail)); trail.clear(); }
                else trail.push_back(a);
            }
        } else {
            int holder = -1;
            for (int i = 0; i < vertices; ++i) if (!here[comp.vertices[i]].empty()) { holder = i; break; }
            if (holder < 0) throw InfeasibleOrientation("snapshot component holds no walk");
            trails.push_back(euler_circuit(holder, vertices, arcs));
        }
        std::vector<std::pair<int, int>> moves;
        for (const auto& trail : trails) {
            if (trail.empty()) throw InfeasibleOrientation("empty Euler trail");
            int first = comp.vertices[arcs[trail.front()].first];
            if (here[first].empty()) throw InfeasibleOrientation("not enough walks at trail start");
            int walk = here[first].back(); here[first].pop_back();
            for (int a : trail) walks[walk].edges.push_back(comp.edges[a]);
            moves.emplace_back(walk, comp.vertices[arcs[trail.back()].second]);
        }
        // Reserve all walkers before returning any: they must exist before this time.
        for (const auto& move : moves) here[move.second].push_back(move.first);
    }
    check_walks(inst, walks);
    return walks;
}

void check_walks(const Instance& inst, const std::vector<Walk>& walks) {
    inst.validate();
    std::vector<Count> starts(inst.n, 0), ends(inst.n, 0);
    std::vector<bool> used(inst.edges.size(), false);
    for (const auto& walk : walks) {
        if (walk.start < 0 || walk.start >= inst.n) throw std::invalid_argument("invalid walk start");
        ++starts[walk.start]; int position = walk.start;
        std::optional<Time> last;
        for (int e : walk.edges) {
            if (e < 0 || e >= checked_index(inst.edges.size()) || used[e])
                throw std::invalid_argument("invalid or repeated edge in witness");
            used[e] = true; const auto& edge = inst.edges[e];
            if (position != edge.u && position != edge.v) throw std::invalid_argument("walk is disconnected");
            if (last && edge.time < *last) throw std::invalid_argument("walk time decreases");
            position = position == edge.u ? edge.v : edge.u; last = edge.time;
        }
        ++ends[position];
    }
    if (starts != inst.start) throw std::invalid_argument("witness start counts differ");
    if (std::find(used.begin(), used.end(), false) != used.end()) throw std::invalid_argument("uncovered edge");
    if (inst.end && ends != *inst.end) throw std::invalid_argument("witness end counts differ");
}
} // namespace nscover
