#pragma once
#include "nscover/backtrack.hpp"
#include "nscover/walks.hpp"
#include <nlohmann/json.hpp>

namespace nscover {
Instance instance_from_json(const nlohmann::json &);
nlohmann::json instance_to_json(const Instance &);
nlohmann::json result_to_json(const Result &);
nlohmann::json walks_to_json(const std::vector<Walk> &);
} // namespace nscover
