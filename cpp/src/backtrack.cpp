#include "nscover/backtrack.hpp"
#include <chrono>
#include <map>
#include <unordered_set>

namespace nscover {
namespace {
struct State {
  std::size_t step = 0;
  std::vector<Count> tokens;
  std::vector<std::uint64_t> left;
  bool operator==(const State &other) const {
    return step == other.step && tokens == other.tokens && left == other.left;
  }
};
struct StateHash {
  std::size_t operator()(const State &state) const {
    std::size_t hash = state.step;
    const auto mix = [&hash](std::uint64_t value) {
      hash ^= std::hash<std::uint64_t>{}(value) + 0x9e3779b97f4a7c15ULL +
              (hash << 6U) + (hash >> 2U);
    };
    for (Count count : state.tokens)
      mix(static_cast<std::uint64_t>(count));
    for (auto word : state.left)
      mix(word);
    return hash;
  }
};
struct Frame {
  State state;
  std::size_t next_choice = 0;
};
} // namespace

BacktrackResult solve_backtrack(const Instance &inst,
                                const BacktrackOptions &options) {
  inst.validate();
  const auto began = std::chrono::steady_clock::now();
  std::map<Time, std::vector<int>> by_time;
  for (int e = 0; e < checked_index(inst.edges.size()); ++e)
    by_time[inst.edges[e].time].push_back(e);
  std::vector<std::vector<int>> snapshots;
  for (const auto &entry : by_time)
    snapshots.push_back(entry.second);
  auto reset_mask = [&](State &state) {
    std::size_t edges = snapshots[state.step].size();
    state.left.assign((edges + 63) / 64, ~std::uint64_t{0});
    if (edges % 64 != 0)
      state.left.back() = (std::uint64_t{1} << (edges % 64)) - 1;
  };
  auto normalise = [&](State &state) {
    while (state.step < snapshots.size()) {
      bool empty = true;
      for (auto word : state.left)
        empty = empty && word == 0;
      if (!empty)
        break;
      ++state.step;
      if (state.step < snapshots.size())
        reset_mask(state);
    }
  };
  State first;
  first.tokens = inst.start;
  if (!snapshots.empty())
    reset_mask(first);
  BacktrackResult result;
  std::unordered_set<State, StateHash> seen;
  std::vector<Frame> stack;
  auto enter = [&](State state) {
    normalise(state);
    if (seen.find(state) != seen.end())
      return false;
    if (result.states >= options.max_states) {
      result.status = Status::Limit;
      return false;
    }
    seen.insert(state);
    ++result.states;
    if (state.step == snapshots.size()) {
      if (!inst.end || state.tokens == *inst.end)
        result.status = Status::Yes;
      return false;
    }
    stack.push_back({std::move(state), 0});
    return true;
  };
  enter(std::move(first));
  while (!stack.empty() && result.status == Status::No) {
    double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - began)
            .count();
    if (seconds >= options.max_seconds) {
      result.status = Status::Limit;
      break;
    }
    auto &frame = stack.back();
    const auto &edges = snapshots[frame.state.step];
    bool descended = false;
    while (frame.next_choice < 2 * edges.size()) {
      std::size_t choice = frame.next_choice++, local = choice / 2;
      if (!(frame.state.left[local / 64] & (std::uint64_t{1} << (local % 64))))
        continue;
      const auto &edge = inst.edges[edges[local]];
      int from = choice % 2 == 0 ? edge.u : edge.v,
          to = choice % 2 == 0 ? edge.v : edge.u;
      if (frame.state.tokens[from] == 0)
        continue;
      auto child = frame.state;
      --child.tokens[from];
      ++child.tokens[to];
      child.left[local / 64] &= ~(std::uint64_t{1} << (local % 64));
      if (enter(std::move(child))) {
        descended = true;
        break;
      }
      if (result.status != Status::No)
        break;
    }
    if (!descended && result.status == Status::No)
      stack.pop_back();
  }
  return result;
}
} // namespace nscover
