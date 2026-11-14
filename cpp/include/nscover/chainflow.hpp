#pragma once
#include "nscover/timeline.hpp"

namespace nscover {
// GreedyDinic: greedy in time order, then Dinic on the residual network.
// Online: greedy in time order with an augmenting search as soon as an edge is
// stuck, while only earlier edges are oriented. Phased: the same greedy start, then
// augmenting paths found in phases from all stuck edges at once. Dinic: from scratch
// (a check).
enum class Backend { Dinic, GreedyDinic, Online, Phased };
using PrefixCaps = std::vector<std::vector<Count>>;

std::optional<PrefixCaps> prefix_caps(const Instance&, const Timeline&);

struct ChainResult {
    bool complete = false;
    Count value = 0;
    Count rounds = 0;  // searches (Online) or phases (Phased) that were run
    std::vector<int> tails;
};
ChainResult solve_chain(const Instance&, const Timeline&, const PrefixCaps&,
                        Backend backend = Backend::Online);

struct WalkCounts {
    // before[c][i] is the token count at component c's local vertex i.
    std::vector<std::vector<Count>> before;
    std::vector<Count> final;
};
WalkCounts walk_counts(const Instance&, const Timeline&, const std::vector<int>& tails);
} // namespace nscover
