#pragma once
#include "nscover/timeline.hpp"
#include <stdexcept>

namespace nscover {
struct Walk { int start; std::vector<int> edges; };
class InfeasibleOrientation : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
std::vector<Walk> build_walks(const Instance&, const std::vector<int>& tails);
// Checks the original definition, including edge identity, time and terminals.
// Throws std::invalid_argument on an invalid witness, also in release builds.
void check_walks(const Instance&, const std::vector<Walk>&);
} // namespace nscover
