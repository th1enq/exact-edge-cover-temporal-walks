#include "nscover/io.hpp"
#include "nscover/maxflow.hpp"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <stdexcept>

namespace {
using namespace nscover;
using Metrics = std::map<std::string, std::uint64_t>;
Metrics metrics;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
template <typename F> void rejects(F action, const std::string& label) {
    bool threw = false;
    try { action(); } catch (const std::exception&) { threw = true; }
    require(threw, label + " should have failed");
}
void check(const Instance& inst, bool use_oracle, std::optional<bool> expected = std::nullopt) {
    try {
        std::optional<Status> truth;
        if (use_oracle) {
            BacktrackOptions options; options.max_states = 5000000; options.max_seconds = 10;
            auto oracle = solve_backtrack(inst, options);
            require(oracle.status != Status::Limit, "oracle hit resource limit");
            truth = oracle.status; ++metrics["oracle_checked"];
            metrics["oracle_states"] += oracle.states;
        }
        BranchOptions options; options.max_flows = 2000; options.max_seconds = 0.25;
        auto branch = solve_branch(inst, options);
        if (use_oracle) require(branch.status != Status::Limit, "small branch hit limit");
        if (branch.status == Status::Limit) ++metrics["branch_limit"];
        else {
            ++metrics["branch_checked"];
            if (truth) require(branch.status == *truth, "branch disagrees with backtracking");
            else truth = branch.status;
            metrics["max_branch_flows"] = std::max(metrics["max_branch_flows"], branch.flows);
        }
        if (branch.status == Status::Yes) check_walks(inst, build_walks(inst, branch.tails));
        std::optional<Status> previous;
        for (Backend backend : {Backend::GreedyDinic, Backend::Online, Backend::Phased, Backend::Dinic}) {
            auto pair = solve_pairflow(inst, backend);
            require(pair.status != Status::Limit, "pair-flow returned LIMIT");
            if (truth) require(pair.status == *truth, "pair-flow disagrees with independent solver");
            if (previous) require(pair.status == *previous, "pair backends disagree");
            if (expected) require((pair.status == Status::Yes) == *expected, "unexpected answer");
            if (pair.status == Status::Yes) {
                check_walks(inst, build_walks(inst, pair.tails)); ++metrics["witnesses_checked"];
            }
            if (!previous) {
                ++metrics[pair.status == Status::Yes ? "yes" : "no"];
                ++metrics[inst.end ? "fixed" : "free"];
            }
            previous = pair.status;
            metrics["dead_ge2"] += pair.dead >= 2;
            metrics["augmented"] += pair.augmentations > 0;
            metrics["augmented_yes"] += pair.augmentations > 0 && pair.status == Status::Yes;
            metrics["no_path"] += pair.reason == "no augmenting path";
            metrics["no_after_augmentation"] += pair.augmentations > 0 && pair.status == Status::No;
            metrics["max_dead"] = std::max(metrics["max_dead"], static_cast<std::uint64_t>(pair.dead));
            metrics["max_augmentations"] = std::max(metrics["max_augmentations"], static_cast<std::uint64_t>(pair.augmentations));
            require(pair.augmentations <= pair.dead, "more than D augmentations");
            if (pair.reason == "no augmenting path") require(!pair.reachable_ports.empty(), "missing reachable set");
        }
        ++metrics["instances"];
        metrics["max_edges"] = std::max(metrics["max_edges"], static_cast<std::uint64_t>(inst.edges.size()));
    } catch (...) {
        std::ofstream("failure.json") << instance_to_json(inst).dump(2) << '\n';
        throw;
    }
}

Instance family(int gadgets, int pairs) {
    Instance inst; inst.n = 3 * gadgets + 1; inst.start.assign(inst.n, 0); inst.start[0] = 2 * pairs;
    for (int i = 0; i < gadgets; ++i) {
        int u = 3 * i + 1, v = u + 1, w = u + 2, t = 2 * i + 1;
        inst.edges.insert(inst.edges.end(), {{0,u,t},{0,u,t},{0,v,t},{0,v,t},
            {u,v,t+1},{v,w,t+1},{w,u,t+1}});
    }
    return inst;
}

void unit() {
    Instance aaai{5, {{0,1,1},{1,2,1},{1,3,2},{3,4,2},{4,1,2}}, {1,0,0,0,0}, std::vector<Count>{0,0,1,0,0}, "AAAI"};
    check(aaai, true, false); check(aaai.free_end(), true, false);
    auto second = aaai; second.start[3] = 1; (*second.end)[3] = 1; check(second, true, true);
    Timeline tl(aaai); int evens = 0;
    for (const auto& c : tl.components) if (c.even) { ++evens; require(c.time == 2, "wrong even component time"); }
    require(evens == 1, "wrong even component count");
    check({3, {{0,1,5},{1,2,5}}, {1,0,0}, std::vector<Count>{0,0,1}, "equal-times"}, true, true);
    check({2, {}, {1,0}, std::vector<Count>{1,0}, "empty-yes"}, true, true);
    check({2, {}, {1,0}, std::vector<Count>{0,1}, "empty-no"}, true, false);
    check({0, {}, {}, std::nullopt, "zero-vertices"}, true, true);
    check({3, {{0,1,1}}, {1,0,2}, std::vector<Count>{0,1,0}, "isolated"}, true, false);
    check({2, {{0,1,-3},{0,1,-3}}, {2,0}, std::vector<Count>{0,2}, "parallel"}, true, true);
    check({2, {{0,1,1}}, {0,0}, std::nullopt, "zero-walks"}, true, false);
    check({2, {{0,1,1}}, {1,0}, std::vector<Count>{0,0}, "sum-mismatch"}, true, false);
    check({2, {{0,1,1}}, {1,0}, std::vector<Count>{1,0}, "parity-mismatch"}, true, false);
    Instance triangle{3, {{0,1,1},{1,2,1},{2,0,1}}, {0,0,0}, std::nullopt, "triangle"};
    check(triangle, true, false);
    rejects([&]{ build_walks(triangle, {0,1,2}); }, "closed trail without token");
    rejects([&]{ check_walks({3, {{0,1,2},{1,2,1}}, {1,0,0}, std::nullopt, ""}, {{0,{0,1}}}); }, "time reversal");
    Instance path{3, {{0,1,1},{1,2,1}}, {1,0,0}, std::nullopt, ""};
    rejects([&]{ check_walks(path, {{0,{0,0}}}); }, "repeated edge");
    rejects([&]{ check_walks(path, {{0,{0}}}); }, "missing edge");
    rejects([&]{ check_walks(path, {{0,{1,0}}}); }, "disconnected walk");
    rejects([&]{ check_walks(path, {{0,{-1,0}}}); }, "negative edge index");
    rejects([&]{ build_walks(path, {2,1}); }, "invalid tail");
    require(orient_with_indegree({0,1,2}, {{0,1},{1,2},{2,0}}, {1,1,1}).has_value(), "orientation missing");
    require(!orient_with_indegree({0,1,2}, {{0,1},{1,2},{2,0}}, {3,0,0}), "bad orientation accepted");
    for (const auto& bad : {
        R"({"num_vertices":2,"start":[1],"edges":[]})",
        R"({"num_vertices":2,"start":[-1,1],"edges":[]})",
        R"({"num_vertices":2,"start":[1,0],"edges":[{"u":0,"v":0,"time":1}]})",
        R"({"num_vertices":2,"start":[1.5,0],"edges":[]})",
        R"({"num_vertices":2,"start":[18446744073709551615,0],"edges":[]})"})
        rejects([&]{ instance_from_json(nlohmann::json::parse(bad)); }, "malformed instance");
    require(instance_to_json(instance_from_json(instance_to_json(aaai))) == instance_to_json(aaai), "JSON roundtrip");
    BacktrackOptions zero_states; zero_states.max_states = 0;
    require(solve_backtrack(path, zero_states).status == Status::Limit, "backtrack limit mislabeled");
    BranchOptions zero_flows; zero_flows.max_flows = 0;
    require(solve_branch(path, zero_flows).status == Status::Limit, "branch limit mislabeled");
    BacktrackOptions zero_time; zero_time.max_seconds = 0;
    require(solve_backtrack(path, zero_time).status == Status::Limit, "backtrack time limit mislabeled");

    // Large counts and timestamps exercise numeric types without expanding k walks.
    Instance huge{2, {{0,1,std::numeric_limits<Time>::min()}}, {Count{1} << 40,0},
        std::vector<Count>{(Count{1} << 40)-1,1}, "64-bit"};
    require(solve_pairflow(huge).status == Status::Yes, "64-bit solve failed");
    require(solve_backtrack(huge).status == Status::Yes, "64-bit oracle failed");
    // More than 64 edges in a snapshot: oracle masks must not truncate.
    Instance many{2, {}, {1,0}, std::vector<Count>{1,0}, "wide-snapshot"};
    for (int i = 0; i < 70; ++i) many.edges.push_back({0,1,0});
    check(many, true, true);
    // An odd edge beyond bit 63 changes the required endpoint; truncating the
    // second mask word would now disagree with the expected answer.
    many.edges.resize(65); many.end = std::vector<Count>{0,1};
    check(many, true, true);
    // Long chains must not depend on the process recursion stack.
    Instance long_path{2, {}, {1,0}, std::vector<Count>{1,0}, "long-timeline"};
    for (int i = 0; i < 20000; ++i) long_path.edges.push_back({0,1,i});
    auto long_result = solve_pairflow(long_path, Backend::GreedyDinic);
    require(long_result.status == Status::Yes, "long timeline failed");
    check_walks(long_path, build_walks(long_path, long_result.tails));
    auto online_result = solve_pairflow(long_path, Backend::Online);
    require(online_result.status == Status::Yes, "online long timeline failed");
    check_walks(long_path, build_walks(long_path, online_result.tails));
    // Test Dinic's deep traversal directly with one 20,000-arc augmenting path.
    // Routing 20,000 separate source edges down the same chain would add a
    // quadratic throughput benchmark rather than additional stack-depth coverage.
    MaxFlow deep(20001);
    for (int i = 0; i < 20000; ++i) deep.add(i, i+1, 1);
    require(deep.flow(0,20000) == 1, "deep iterative Dinic failed");
    require(!deep.reachable(0)[20000], "incorrect residual cut");
    rejects([&]{ deep.add(0, 1, 1); }, "arc added after packing");
    auto medium = long_path; medium.edges.resize(512);
    auto medium_result = solve_pairflow(medium, Backend::Dinic);
    require(medium_result.status == Status::Yes, "Dinic timeline failed");
    check_walks(medium, build_walks(medium, medium_result.tails));
    for (int e = 1; e <= 8; ++e) for (int r : {e-1,e,e+1}) check(family(e,r), e <= 2, r >= e);
}

void exhaustive() {
    // Every multiset of <=4 edges on 3 labelled vertices and 2 timestamps.
    // Every start vector in {0,1,2}^3; FREE and every end vector of equal total.
    std::vector<Edge> types;
    for (int t = 0; t < 2; ++t) for (int u = 0; u < 3; ++u) for (int v = u+1; v < 3; ++v) types.push_back({u,v,t});
    Instance inst; inst.n = 3; inst.start.resize(3);
    std::function<void(int,int)> graphs = [&](int next, int left) {
        if (left == 0) {
            for (int a = 0; a <= 2; ++a) for (int b = 0; b <= 2; ++b) for (int c = 0; c <= 2; ++c) {
                inst.start = {a,b,c}; inst.end.reset(); check(inst, true);
                for (int x = 0; x <= a+b+c; ++x) for (int y = 0; y <= a+b+c-x; ++y)
                    check(inst.with_end({x,y,a+b+c-x-y}), true);
            }
            return;
        }
        for (int e = next; e < checked_index(types.size()); ++e) {
            inst.edges.push_back(types[e]); graphs(e, left-1); inst.edges.pop_back();
        }
    };
    for (int m = 0; m <= 4; ++m) graphs(0,m);
}

int draw(std::mt19937_64& rng, int low, int high) { return std::uniform_int_distribution<int>(low,high)(rng); }
Instance random_instance(std::mt19937_64& rng, bool large) {
    Instance inst; inst.n = draw(rng, 2, large ? 12 : 7); inst.start.resize(inst.n);
    for (auto& a : inst.start) a = draw(rng,0,3) == 0 ? 2 : draw(rng,0,1);
    if (draw(rng,0,9) < 6 && inst.n >= 3) {
        int snapshots = draw(rng,1,large ? 18 : 4);
        std::vector<int> vertices(inst.n); std::iota(vertices.begin(), vertices.end(), 0);
        for (int t = 0; t < snapshots; ++t) {
            int parts = draw(rng,1,2);
            for (int part = 0; part < parts; ++part) {
                std::shuffle(vertices.begin(), vertices.end(), rng);
                int size = draw(rng,2,std::min(inst.n,4));
                for (int i = 0; i < size; ++i) inst.edges.push_back({vertices[i],vertices[(i+1)%size],t-2});
            }
        }
    } else {
        int m = draw(rng,0,large ? 120 : 11), horizon = draw(rng,1,5);
        for (int i = 0; i < m; ++i) {
            int u = draw(rng,0,inst.n-1), v = draw(rng,0,inst.n-2); if (v >= u) ++v;
            inst.edges.push_back({u,v,draw(rng,0,horizon)-2});
        }
    }
    if (!large && inst.edges.size() > 11) inst.edges.resize(11);
    std::shuffle(inst.edges.begin(), inst.edges.end(), rng);
    for (auto& e : inst.edges) if (draw(rng,0,1)) std::swap(e.u,e.v);
    return inst;
}
std::vector<Count> random_end(std::mt19937_64& rng, const Instance& inst) {
    auto tokens = inst.start;
    std::vector<int> order(inst.edges.size()); std::iota(order.begin(), order.end(), 0);
    std::shuffle(order.begin(), order.end(), rng);
    std::stable_sort(order.begin(), order.end(), [&](int a,int b){ return inst.edges[a].time < inst.edges[b].time; });
    bool ok = true;
    for (int e : order) {
        int u = inst.edges[e].u, v = inst.edges[e].v;
        if (!tokens[u] && !tokens[v]) { ok = false; break; }
        if (!tokens[u] || (tokens[v] && draw(rng,0,1))) std::swap(u,v);
        --tokens[u]; ++tokens[v];
    }
    if (ok && draw(rng,0,9) < 7) return tokens;
    std::fill(tokens.begin(), tokens.end(), 0);
    for (Count j = 0; j < inst.walk_count(); ++j) ++tokens[draw(rng,0,inst.n-1)];
    return tokens;
}
void random_checks(bool large, int cases, std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    for (int i = 0; i < cases; ++i) {
        auto inst = random_instance(rng,large);
        check(inst, !large); check(inst.with_end(random_end(rng,inst)), !large);
    }
    require(metrics["augmented_yes"] > 0, "random suite missed successful augmentation");
    require(metrics["no_path"] > 0, "random suite missed no-path rejection");
    if (large) {
        require(metrics["dead_ge2"] > 0, "large suite missed D >= 2");
        require(metrics["no_after_augmentation"] > 0, "large suite missed NO after an augmentation");
    }
}
} // namespace

int main(int argc, char** argv) {
    std::string mode = "unit"; int cases = 5000; std::uint64_t seed = 1;
    try {
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (++i == argc) throw std::invalid_argument("missing argument");
            if (arg == "--mode") mode = argv[i];
            else if (arg == "--cases") cases = std::stoi(argv[i]);
            else if (arg == "--seed") seed = std::stoull(argv[i]);
            else throw std::invalid_argument("unknown argument");
        }
        require(cases > 0, "cases must be positive");
        auto began = std::chrono::steady_clock::now();
        if (mode == "unit") unit();
        else if (mode == "exhaustive") exhaustive();
        else if (mode == "small") random_checks(false,cases,seed);
        else if (mode == "large") random_checks(true,cases,seed);
        else throw std::invalid_argument("unknown mode");
        nlohmann::json result = metrics;
        result["mode"] = mode; result["seed"] = seed; result["status"] = "PASS";
        result["seconds"] = std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
        std::cout << result.dump() << '\n'; return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL: " << e.what() << "; replay input (if applicable): failure.json\n"; return 1;
    }
}
