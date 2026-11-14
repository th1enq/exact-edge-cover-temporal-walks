#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace nscover {
using Count = std::int64_t;
using Time = std::int64_t;

struct Edge {
  int u = 0;
  int v = 0;
  Time time = 0;
};

// Vertices are 0..n-1. Parallel edges are distinct; loops are not allowed.
// Walks may be empty, wait, and traverse multiple edges at the same timestamp.
struct Instance {
  int n = 0;
  std::vector<Edge> edges;
  std::vector<Count> start;
  std::optional<std::vector<Count>> end;
  std::string name;

  void validate() const;
  Count walk_count() const;
  Instance free_end() const;
  Instance with_end(std::vector<Count> counts) const;
};

Count checked_add(Count a, Count b);
int checked_index(std::size_t size);
} // namespace nscover
