#include "nscover/maxflow.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>
#include <unordered_map>

namespace nscover {
MaxFlow::MaxFlow(int nodes) : nodes_(nodes) {
  if (nodes < 0)
    throw std::invalid_argument("negative network size");
}
int MaxFlow::add(int from, int to, Count capacity) {
  if (packed_)
    throw std::logic_error("arc added after the network was used");
  if (from < 0 || to < 0 || from >= nodes_ || to >= nodes_ || capacity < 0)
    throw std::invalid_argument("invalid flow arc");
  int id = checked_index(from_.size());
  checked_index(from_.size() + 2);
  from_.push_back(from);
  to_.push_back(to);
  capacity_.push_back(capacity);
  from_.push_back(to);
  to_.push_back(from);
  capacity_.push_back(0);
  return id;
}
void MaxFlow::pack() const {
  if (packed_)
    return;
  first_.assign(static_cast<std::size_t>(nodes_) + 1, 0);
  for (int a : from_)
    ++first_[a + 1];
  for (int v = 0; v < nodes_; ++v)
    first_[v + 1] += first_[v];
  auto fill = first_;
  position_.resize(from_.size());
  arcs_.resize(from_.size());
  // Newest arc first per node, as in a head-inserted adjacency list; the flow
  // found (and so the orientation and D) matches the recorded runs.
  for (std::size_t id = from_.size(); id-- > 0;)
    position_[id] = fill[from_[id]]++;
  for (std::size_t id = 0; id < from_.size(); ++id)
    arcs_[position_[id]] = {to_[id], position_[id ^ 1], capacity_[id]};
  from_ = {};
  to_ = {};
  capacity_ = {};
  packed_ = true;
}
void MaxFlow::push(int arc, Count amount) {
  pack();
  if (arc < 0 || arc >= checked_index(position_.size()))
    throw std::logic_error("invalid residual push");
  auto &forward = arcs_[position_[arc]];
  if (amount < 0 || amount > forward.capacity)
    throw std::logic_error("invalid residual push");
  forward.capacity -= amount;
  arcs_[forward.reverse].capacity =
      checked_add(arcs_[forward.reverse].capacity, amount);
}
Count MaxFlow::residual(int arc) const {
  pack();
  return arcs_[position_.at(arc)].capacity;
}
Count MaxFlow::flow(int source, int sink) {
  pack();
  if (source < 0 || sink < 0 || source >= nodes_ || sink >= nodes_)
    throw std::invalid_argument("invalid flow terminal");
  if (source == sink)
    throw std::invalid_argument("flow source equals sink");
  Count total = 0;
  for (;;) {
    level_.assign(nodes_, -1);
    queue_.clear();
    level_[source] = 0;
    queue_.push_back(source);
    // Nodes beyond the sink's level cannot lie on a shortest augmenting path.
    for (std::size_t q = 0; q < queue_.size() && level_[sink] < 0; ++q) {
      int a = queue_[q];
      for (int k = first_[a]; k < first_[a + 1]; ++k) {
        int b = arcs_[k].to;
        if (arcs_[k].capacity > 0 && level_[b] < 0) {
          level_[b] = level_[a] + 1;
          queue_.push_back(b);
        }
      }
    }
    if (level_[sink] < 0)
      return total;
    current_.assign(first_.begin(), first_.end() - 1);
    for (;;) {
      path_.clear();
      int a = source;
      while (a != sink) {
        int &k = current_[a];
        while (k < first_[a + 1] &&
               !(arcs_[k].capacity > 0 && level_[arcs_[k].to] == level_[a] + 1))
          ++k;
        if (k == first_[a + 1]) {
          if (a == source)
            break;
          level_[a] = -1;
          a = arcs_[arcs_[path_.back()].reverse].to;
          path_.pop_back();
        } else {
          path_.push_back(k);
          a = arcs_[k].to;
        }
      }
      if (a != sink)
        break;
      Count amount = std::numeric_limits<Count>::max();
      for (int k : path_)
        amount = std::min(amount, arcs_[k].capacity);
      for (int k : path_) {
        arcs_[k].capacity -= amount;
        arcs_[arcs_[k].reverse].capacity =
            checked_add(arcs_[arcs_[k].reverse].capacity, amount);
      }
      total = checked_add(total, amount);
    }
  }
}
std::vector<bool> MaxFlow::reachable(int source) const {
  pack();
  std::vector<bool> seen(nodes_, false);
  seen.at(source) = true;
  std::vector<int> stack{source};
  while (!stack.empty()) {
    int a = stack.back();
    stack.pop_back();
    for (int k = first_[a]; k < first_[a + 1]; ++k)
      if (arcs_[k].capacity > 0 && !seen[arcs_[k].to]) {
        seen[arcs_[k].to] = true;
        stack.push_back(arcs_[k].to);
      }
  }
  return seen;
}
std::optional<std::vector<int>>
orient_with_indegree(const std::vector<int> &vertices,
                     const std::vector<std::pair<int, int>> &edges,
                     const std::vector<Count> &indegree) {
  if (vertices.size() != indegree.size())
    throw std::invalid_argument("wrong indegree size");
  Count sum = 0;
  for (Count d : indegree) {
    if (d < 0)
      return std::nullopt;
    sum = checked_add(sum, d);
  }
  if (sum != checked_index(edges.size()))
    return std::nullopt;
  std::unordered_map<int, int> local;
  for (int i = 0; i < checked_index(vertices.size()); ++i)
    if (!local.emplace(vertices[i], i).second)
      throw std::invalid_argument("duplicate vertex");
  int m = checked_index(edges.size());
  MaxFlow net(checked_index(2 + edges.size() + vertices.size()));
  std::vector<int> choice;
  for (int e = 0; e < m; ++e) {
    net.add(0, 2 + e, 1);
    choice.push_back(net.add(2 + e, 2 + m + local.at(edges[e].first), 1));
    net.add(2 + e, 2 + m + local.at(edges[e].second), 1);
  }
  for (int i = 0; i < checked_index(vertices.size()); ++i)
    net.add(2 + m + i, 1, indegree[i]);
  if (net.flow(0, 1) < m)
    return std::nullopt;
  std::vector<int> heads;
  for (int e = 0; e < m; ++e)
    heads.push_back(net.residual(choice[e]) == 0 ? edges[e].first
                                                 : edges[e].second);
  return heads;
}
} // namespace nscover
