#include "nscover/timeline.hpp"
#include <algorithm>
#include <map>
#include <numeric>
#include <stdexcept>

namespace nscover {
int Component::local(int vertex) const {
    const auto it = std::lower_bound(vertices.begin(), vertices.end(), vertex);
    if (it == vertices.end() || *it != vertex) throw std::logic_error("vertex not in component");
    return static_cast<int>(it - vertices.begin());
}
int Component::parity_in(int i) const { return static_cast<int>(before[i] % 2); }
int Component::parity_out(int i) const { return (parity_in(i) + degree[i] % 2) % 2; }

Timeline::Timeline(const Instance& inst) {
    inst.validate();
    appear_times.resize(inst.n); degree.resize(inst.n); before.resize(inst.n);
    appear_comp.resize(inst.n); total.resize(inst.n); slot.resize(inst.edges.size());
    std::map<Time, std::vector<int>> by_time;
    for (int e = 0; e < checked_index(inst.edges.size()); ++e) {
        const auto& edge = inst.edges[e];
        by_time[edge.time].push_back(e);
        appear_times[edge.u].push_back(edge.time);
        appear_times[edge.v].push_back(edge.time);
    }
    for (int v = 0; v < inst.n; ++v) {
        auto& times = appear_times[v];
        std::sort(times.begin(), times.end());
        times.erase(std::unique(times.begin(), times.end()), times.end());
        degree[v].assign(times.size(), 0);
        appear_comp[v].assign(times.size(), -1);
    }
    for (int e = 0; e < checked_index(inst.edges.size()); ++e) {
        const auto& edge = inst.edges[e];
        int side = 0;
        for (int v : {edge.u, edge.v}) {
            int j = static_cast<int>(std::lower_bound(appear_times[v].begin(),
                appear_times[v].end(), edge.time) - appear_times[v].begin());
            slot[e][side++] = j;
            ++degree[v][j];
        }
    }
    for (int v = 0; v < inst.n; ++v) {
        Count running = inst.start[v];
        for (int g : degree[v]) { before[v].push_back(running); running = checked_add(running, g); }
        total[v] = running;
    }
    std::vector<int> parent(inst.n), active;
    std::iota(parent.begin(), parent.end(), 0);
    const auto find = [&parent](int v) {
        int root = v;
        while (parent[root] != root) root = parent[root];
        while (parent[v] != v) { int next = parent[v]; parent[v] = root; v = next; }
        return root;
    };
    for (const auto& entry : by_time) {
        active.clear();
        for (int e : entry.second) {
            const auto& edge = inst.edges[e];
            active.push_back(edge.u); active.push_back(edge.v);
        }
        std::sort(active.begin(), active.end());
        active.erase(std::unique(active.begin(), active.end()), active.end());
        for (int v : active) parent[v] = v;
        for (int e : entry.second) parent[find(inst.edges[e].u)] = find(inst.edges[e].v);
        std::map<int, std::vector<int>> groups;
        for (int e : entry.second) groups[find(inst.edges[e].u)].push_back(e);
        for (const auto& group : groups) {
            Component c;
            c.index = checked_index(components.size()); c.time = entry.first; c.edges = group.second;
            for (int e : c.edges) { c.vertices.push_back(inst.edges[e].u); c.vertices.push_back(inst.edges[e].v); }
            std::sort(c.vertices.begin(), c.vertices.end());
            c.vertices.erase(std::unique(c.vertices.begin(), c.vertices.end()), c.vertices.end());
            c.degree.assign(c.vertices.size(), 0);
            for (int e : c.edges) { ++c.degree[c.local(inst.edges[e].u)]; ++c.degree[c.local(inst.edges[e].v)]; }
            c.even = true;
            for (int i = 0; i < checked_index(c.vertices.size()); ++i) {
                int v = c.vertices[i];
                int j = static_cast<int>(std::lower_bound(appear_times[v].begin(),
                    appear_times[v].end(), c.time) - appear_times[v].begin());
                c.position.push_back(j); c.before.push_back(before[v][j]);
                appear_comp[v][j] = c.index;
                c.even = c.even && c.degree[i] % 2 == 0 && c.before[i] % 2 == 0;
            }
            components.push_back(std::move(c));
        }
    }
}
} // namespace nscover
