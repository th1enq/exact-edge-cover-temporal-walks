#include "nscover/solver.hpp"
#include <algorithm>
#include <chrono>
#include <numeric>
#include <stdexcept>

namespace nscover {
const char *status_name(Status status) {
  switch (status) {
  case Status::Yes:
    return "YES";
  case Status::No:
    return "NO";
  case Status::Limit:
    return "LIMIT";
  }
  throw std::logic_error("unknown status");
}
Result solve_branch(const Instance &inst, const BranchOptions &options) {
  const auto began = std::chrono::steady_clock::now();
  Timeline tl(inst);
  auto root = prefix_caps(inst, tl);
  Result result;
  if (!root) {
    result.reason = "counting";
    return result;
  }
  std::vector<PrefixCaps> stack{*root};
  while (!stack.empty()) {
    double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - began)
            .count();
    if (result.flows >= options.max_flows || seconds >= options.max_seconds) {
      result.status = Status::Limit;
      result.reason = "branch resource limit";
      return result;
    }
    auto caps = std::move(stack.back());
    stack.pop_back();
    ++result.flows;
    auto chain = solve_chain(inst, tl, caps, options.backend);
    if (!chain.complete)
      continue;
    auto counts = walk_counts(inst, tl, chain.tails);
    int dead = -1;
    for (const auto &c : tl.components)
      if (std::accumulate(counts.before[c.index].begin(),
                          counts.before[c.index].end(), Count{0}) == 0) {
        dead = c.index;
        break;
      }
    if (dead < 0) {
      result.status = Status::Yes;
      result.tails = std::move(chain.tails);
      return result;
    }
    const auto &comp = tl.components[dead];
    if (!comp.even)
      throw std::logic_error("dead component is not even");
    for (int i = 0; i < checked_index(comp.vertices.size()); ++i) {
      int v = comp.vertices[i], previous = comp.position[i] - 1;
      if (previous < 0)
        continue;
      auto child = caps;
      child[v][previous] = std::min(child[v][previous], comp.before[i] / 2 - 1);
      if (child[v][previous] >= 0)
        stack.push_back(std::move(child));
    }
  }
  result.reason = "branch exhausted";
  return result;
}
} // namespace nscover
