#pragma once
#include "nscover/chainflow.hpp"
#include <limits>

namespace nscover {
enum class Status { Yes, No, Limit };
const char* status_name(Status status);

struct Result {
    Status status = Status::No;
    std::vector<int> tails;
    std::uint64_t flows = 0;
    int dead = 0;
    int augmentations = 0;
    std::string reason;
    // BFS-reachable ports when pair-flow cannot find an augmenting path.
    std::vector<int> reachable_ports;
};

struct BranchOptions {
    std::uint64_t max_flows = 1000000;
    double max_seconds = std::numeric_limits<double>::infinity();
    Backend backend = Backend::Online;
};
Result solve_branch(const Instance&, const BranchOptions& options = {});
Result solve_pairflow(const Instance&, Backend backend = Backend::Online);
} // namespace nscover
