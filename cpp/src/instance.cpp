#include "nscover/instance.hpp"
#include <limits>
#include <stdexcept>
#include <utility>

namespace nscover {
Count checked_add(Count a, Count b) {
    if ((b > 0 && a > std::numeric_limits<Count>::max() - b) ||
        (b < 0 && a < std::numeric_limits<Count>::min() - b))
        throw std::overflow_error("64-bit count overflow");
    return a + b;
}
int checked_index(std::size_t size) {
    if (size > static_cast<std::size_t>(std::numeric_limits<int>::max()))
        throw std::length_error("graph is too large for 32-bit node indices");
    return static_cast<int>(size);
}
void Instance::validate() const {
    if (n < 0 || start.size() != static_cast<std::size_t>(n) ||
        (end && end->size() != static_cast<std::size_t>(n)))
        throw std::invalid_argument("wrong vertex count or terminal vector length");
    checked_index(edges.size());
    Count sum = 0;
    for (Count count : start) {
        if (count < 0) throw std::invalid_argument("negative start count");
        sum = checked_add(sum, count);
    }
    sum = 0;
    if (end) for (Count count : *end) {
        if (count < 0) throw std::invalid_argument("negative end count");
        sum = checked_add(sum, count);
    }
    for (const auto& edge : edges)
        if (edge.u < 0 || edge.v < 0 || edge.u >= n || edge.v >= n || edge.u == edge.v)
            throw std::invalid_argument("invalid edge endpoints");
}
Count Instance::walk_count() const {
    Count sum = 0;
    for (Count count : start) sum = checked_add(sum, count);
    return sum;
}
Instance Instance::free_end() const { auto copy = *this; copy.end.reset(); return copy; }
Instance Instance::with_end(std::vector<Count> counts) const {
    auto copy = *this; copy.end = std::move(counts); copy.validate(); return copy;
}
} // namespace nscover
