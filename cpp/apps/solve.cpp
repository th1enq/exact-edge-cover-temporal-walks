#include "nscover/io.hpp"
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

namespace {
struct Options {
    std::string solver = "pair", input;
    bool batch = false, summary = false, verify_backtrack = false, verify_branch = false;
    nscover::Backend backend = nscover::Backend::Online;
    nscover::BranchOptions branch;
    nscover::BacktrackOptions backtrack;
};
Options parse(int argc, char** argv) {
    Options opts;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto value = [&]() { if (++i == argc) throw std::invalid_argument("missing value for " + arg); return std::string(argv[i]); };
        auto natural = [&](const std::string& text) {
            if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos)
                throw std::invalid_argument("expected nonnegative integer");
            return std::stoull(text);
        };
        if (arg == "--solver") opts.solver = value();
        else if (arg == "--backend") {
            auto backend = value();
            if (backend == "dinic") opts.backend = nscover::Backend::Dinic;
            else if (backend == "greedy") opts.backend = nscover::Backend::GreedyDinic;
            else if (backend == "online") opts.backend = nscover::Backend::Online;
            else if (backend == "phased") opts.backend = nscover::Backend::Phased;
            else throw std::invalid_argument("backend must be greedy, online, phased or dinic");
        } else if (arg == "--batch") opts.batch = true;
        else if (arg == "--summary") opts.summary = true;
        else if (arg == "--verify-backtrack") opts.verify_backtrack = true;
        else if (arg == "--verify-branch") opts.verify_branch = true;
        else if (arg == "--max-flows") opts.branch.max_flows = natural(value());
        else if (arg == "--max-states") opts.backtrack.max_states = natural(value());
        else if (arg == "--seconds") {
            auto text = value(); std::size_t consumed = 0; double seconds = std::stod(text, &consumed);
            if (consumed != text.size() || !std::isfinite(seconds) || seconds < 0) throw std::invalid_argument("invalid seconds");
            opts.branch.max_seconds = opts.backtrack.max_seconds = seconds;
        } else if (arg == "--help") {
            std::cout << "nscover_solve [file.json] [--batch] [--solver pair|branch|backtrack]\n"
                "  [--backend greedy|online|dinic] [--summary] [--verify-backtrack] [--verify-branch]\n"
                "  [--max-flows N] [--max-states N] [--seconds S]\n"
                "Without a file, read stdin. Batch reads one JSON object per line.\n"
                "Every YES from pair/branch builds and checks explicit walks.\n";
            std::exit(0);
        } else if (!arg.empty() && arg[0] == '-') throw std::invalid_argument("unknown option " + arg);
        else if (opts.input.empty()) opts.input = arg;
        else throw std::invalid_argument("multiple input files");
    }
    if (opts.solver != "pair" && opts.solver != "branch" && opts.solver != "backtrack")
        throw std::invalid_argument("solver must be pair, branch or backtrack");
    opts.branch.backend = opts.backend; return opts;
}
nlohmann::json solve(const nlohmann::json& data, const Options& opts) {
    auto inst = nscover::instance_from_json(data);
    auto began = std::chrono::steady_clock::now();
    nscover::Status status;
    nlohmann::json out;
    if (opts.solver == "backtrack") {
        auto result = nscover::solve_backtrack(inst, opts.backtrack); status = result.status;
        out = {{"status", nscover::status_name(status)}, {"states", result.states}};
    } else {
        auto result = opts.solver == "pair" ? nscover::solve_pairflow(inst, opts.backend) : nscover::solve_branch(inst, opts.branch);
        status = result.status; out = nscover::result_to_json(result);
        if (status == nscover::Status::Yes) {
            auto walks = nscover::build_walks(inst, result.tails);
            nscover::check_walks(inst, walks); out["witness"] = "checked";
            if (!opts.summary) out["walks"] = nscover::walks_to_json(walks);
        }
        if (opts.summary) { out.erase("tails"); out.erase("reachable_ports"); }
    }
    out["seconds"] = std::chrono::duration<double>(std::chrono::steady_clock::now() - began).count();
    auto compare = [&](nscover::Status other, const std::string& checker) {
        out[checker] = nscover::status_name(other);
        if (other != nscover::Status::Limit && status != nscover::Status::Limit && other != status)
            throw std::logic_error(checker + " disagrees with solver");
        out[checker + "_verified"] = other != nscover::Status::Limit && status != nscover::Status::Limit;
    };
    if (opts.verify_backtrack) {
        auto truth = nscover::solve_backtrack(inst, opts.backtrack); compare(truth.status, "backtrack"); out["backtrack_states"] = truth.states;
    }
    if (opts.verify_branch) {
        auto branch = nscover::solve_branch(inst, opts.branch); compare(branch.status, "branch"); out["branch_flows"] = branch.flows;
    }
    if (!inst.name.empty()) out["name"] = inst.name;
    return out;
}
} // namespace
int main(int argc, char** argv) {
    try {
        auto opts = parse(argc, argv);
        std::ifstream file;
        if (!opts.input.empty()) { file.open(opts.input); if (!file) throw std::runtime_error("cannot open input file"); }
        std::istream& in = opts.input.empty() ? std::cin : file;
        if (!opts.batch) { nlohmann::json data; in >> data; in >> std::ws; if (!in.eof()) throw std::invalid_argument("trailing input"); std::cout << solve(data, opts).dump() << '\n'; }
        else {
            std::string line;
            while (std::getline(in, line)) {
                if (line.find_first_not_of(" \t\r") == std::string::npos) continue;
                std::cout << solve(nlohmann::json::parse(line), opts).dump() << '\n' << std::flush;
            }
        }
        return 0;
    } catch (const std::exception& error) { std::cerr << "nscover: " << error.what() << '\n'; return 2; }
}
