#include "nscover/io.hpp"
#include <limits>
#include <stdexcept>

namespace nscover {
namespace {
Count integer(const nlohmann::json& value) {
    if (!value.is_number_integer()) throw std::invalid_argument("expected integer");
    if (value.is_number_unsigned() && value.get<std::uint64_t>() > static_cast<std::uint64_t>(std::numeric_limits<Count>::max()))
        throw std::out_of_range("JSON integer exceeds int64");
    return value.get<Count>();
}
int index(const nlohmann::json& value) {
    Count number = integer(value);
    if (number < 0 || number > std::numeric_limits<int>::max()) throw std::out_of_range("invalid index");
    return static_cast<int>(number);
}
std::vector<Count> counts(const nlohmann::json& value) {
    if (!value.is_array()) throw std::invalid_argument("expected count array");
    std::vector<Count> result;
    for (const auto& entry : value) result.push_back(integer(entry));
    return result;
}
} // namespace
Instance instance_from_json(const nlohmann::json& data) {
    Instance inst; inst.n = index(data.at("num_vertices")); inst.start = counts(data.at("start"));
    if (data.find("end") != data.end() && !data.at("end").is_null()) inst.end = counts(data.at("end"));
    if (data.find("name") != data.end()) inst.name = data.at("name").get<std::string>();
    if (!data.at("edges").is_array()) throw std::invalid_argument("expected edge array");
    for (const auto& edge : data.at("edges"))
        inst.edges.push_back({index(edge.at("u")), index(edge.at("v")), integer(edge.at("time"))});
    inst.validate(); return inst;
}
nlohmann::json instance_to_json(const Instance& inst) {
    nlohmann::json data{{"num_vertices", inst.n}, {"start", inst.start}, {"edges", nlohmann::json::array()}};
    for (const auto& edge : inst.edges) data["edges"].push_back({{"u", edge.u}, {"v", edge.v}, {"time", edge.time}});
    if (inst.end) data["end"] = *inst.end;
    if (!inst.name.empty()) data["name"] = inst.name;
    return data;
}
nlohmann::json result_to_json(const Result& result) {
    nlohmann::json data{{"status", status_name(result.status)}, {"flows", result.flows},
        {"dead", result.dead}, {"augmentations", result.augmentations}, {"reason", result.reason}};
    if (result.status == Status::Yes) data["tails"] = result.tails;
    if (!result.reachable_ports.empty()) data["reachable_ports"] = result.reachable_ports;
    return data;
}
nlohmann::json walks_to_json(const std::vector<Walk>& walks) {
    auto data = nlohmann::json::array();
    for (const auto& walk : walks) data.push_back({{"start", walk.start}, {"edges", walk.edges}});
    return data;
}
} // namespace nscover
