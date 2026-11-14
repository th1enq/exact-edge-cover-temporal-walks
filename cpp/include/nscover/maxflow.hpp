#pragma once
#include "nscover/instance.hpp"
#include <optional>
#include <utility>

namespace nscover {
// Iterative Dinic: no recursion proportional to the number of timeline slots.
// Arcs are added first; the first query packs them into a CSR array so that
// each node's arcs are contiguous. Arc IDs returned by add() stay valid.
class MaxFlow {
public:
    explicit MaxFlow(int nodes);
    int add(int from, int to, Count capacity);
    void push(int arc, Count amount);
    Count flow(int source, int sink);
    Count residual(int arc) const;
    std::vector<bool> reachable(int source) const;
private:
    struct Arc { int to; int reverse; Count capacity; };
    void pack() const;
    int nodes_;
    // Arc 2k is the forward arc of add() call k, arc 2k + 1 its reverse.
    mutable std::vector<int> from_, to_;
    mutable std::vector<Count> capacity_;
    mutable std::vector<int> first_, position_;
    mutable std::vector<Arc> arcs_;
    mutable bool packed_ = false;
    std::vector<int> level_, current_, queue_, path_;
};

// Returns the head vertex of each edge, or nullopt if not realisable.
std::optional<std::vector<int>> orient_with_indegree(
    const std::vector<int>& vertices,
    const std::vector<std::pair<int, int>>& edges,
    const std::vector<Count>& indegree);
} // namespace nscover
