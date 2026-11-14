#pragma once
#include "nscover/solver.hpp"

namespace nscover {
struct BacktrackOptions {
  std::uint64_t max_states = 2000000;
  double max_seconds = std::numeric_limits<double>::infinity();
};
struct BacktrackResult {
  Status status = Status::No;
  std::uint64_t states = 0;
};
// Independent definition-based oracle. It tries each unused edge and each token
// direction inside a snapshot; it does not use Timeline or orientations.
BacktrackResult solve_backtrack(const Instance &,
                                const BacktrackOptions &options = {});
} // namespace nscover
