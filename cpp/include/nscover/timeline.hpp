#pragma once
#include "nscover/instance.hpp"
#include <array>

namespace nscover {
struct Component {
    int index = 0;
    Time time = 0;
    // All per-vertex arrays use local indices into sorted vertices.
    std::vector<int> vertices;
    std::vector<int> edges;
    std::vector<int> degree;
    std::vector<Count> before;
    std::vector<int> position;
    bool even = false;

    int local(int vertex) const;
    int parity_in(int local_vertex) const;
    int parity_out(int local_vertex) const;
};

struct Timeline {
    explicit Timeline(const Instance& instance);
    std::vector<std::vector<Time>> appear_times;
    std::vector<std::vector<int>> degree;
    std::vector<std::vector<Count>> before;
    std::vector<Count> total;
    std::vector<std::array<int, 2>> slot;
    std::vector<Component> components;
    std::vector<std::vector<int>> appear_comp;
};
} // namespace nscover
