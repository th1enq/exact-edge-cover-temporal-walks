#include "nscover/io.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <random>
#include <thread>

using Json = nlohmann::json;
using Clock = std::chrono::steady_clock;

static Json read(const std::string &path) {
  std::ifstream f(path);
  if (!f)
    throw std::runtime_error("cannot read " + path);
  Json j;
  f >> j;
  return j;
}
static void save(const std::string &path, const Json &state) {
  const auto tmp = path + ".tmp";
  {
    std::ofstream f(tmp);
    f << state.dump() << '\n';
    f.flush();
    if (!f)
      throw std::runtime_error("cannot write " + tmp);
  }
  std::filesystem::rename(tmp, path);
}
// Stable identity includes the given vector and every edge in input order.
static std::string identity(const Json &data) {
  std::uint64_t h = 14695981039346656037ULL;
  for (unsigned char c : data.dump()) {
    h ^= c;
    h *= 1099511628211ULL;
  }
  return std::to_string(h);
}
int main(int argc, char **argv) {
  const auto began = Clock::now();
  try {
    if (argc < 2)
      throw std::invalid_argument(
          "nscover_mink instance.json --out state.json --seconds S --seed N");
    std::string input = argv[1], output;
    double seconds = 40;
    std::uint64_t seed = 1;
    for (int i = 2; i < argc; ++i) {
      std::string arg = argv[i];
      if (++i == argc)
        throw std::invalid_argument("missing option value");
      std::string value = argv[i];
      std::size_t used = 0;
      if (arg == "--out")
        output = value;
      else if (arg == "--seconds") {
        seconds = std::stod(value, &used);
        if (used != value.size() || !std::isfinite(seconds) || seconds <= 0)
          throw std::invalid_argument("seconds must be positive and finite");
      } else if (arg == "--seed") {
        if (value.empty() ||
            value.find_first_not_of("0123456789") != std::string::npos)
          throw std::invalid_argument("invalid seed");
        seed = std::stoull(value);
      } else
        throw std::invalid_argument("unknown option " + arg);
    }
    if (output.empty() || input == output)
      throw std::invalid_argument("distinct --out required");
    auto data = read(input);
    auto inst = nscover::instance_from_json(data);
    if (inst.end)
      throw std::invalid_argument("FREE instance required");
    const auto id = identity(data);
    Json state;
    std::vector<int> pool;
    std::size_t chunk, cursor = 0;
    bool resumed = std::filesystem::exists(output);
    if (resumed) {
      state = read(output);
      if (state.at("instance_id") != id || state.at("seed") != seed)
        throw std::invalid_argument("checkpoint instance or seed mismatch");
      inst.start = state.at("start").get<std::vector<nscover::Count>>();
      inst.validate();
      pool = state.at("pool").get<std::vector<int>>();
      std::vector<nscover::Count> counts(inst.n, 0);
      for (int v : pool) {
        if (v < 0 || v >= inst.n)
          throw std::invalid_argument("invalid checkpoint pool");
        ++counts[v];
      }
      if (counts != inst.start)
        throw std::invalid_argument("checkpoint pool mismatch");
      chunk = state.at("chunk");
      cursor = state.at("cursor");
      if (!chunk || cursor > pool.size())
        throw std::invalid_argument("invalid checkpoint progress");
      auto given = data.at("start").get<std::vector<nscover::Count>>();
      for (int v = 0; v < inst.n; ++v)
        if (inst.start[v] > given[v])
          throw std::invalid_argument("checkpoint exceeds given vector");
    } else {
      std::vector<int> order(inst.n);
      std::iota(order.begin(), order.end(), 0);
      std::mt19937_64 rng(seed);
      std::shuffle(order.begin(), order.end(), rng);
      for (int v : order)
        for (nscover::Count i = 0; i < inst.start[v]; ++i)
          pool.push_back(v);
      chunk = std::max<std::size_t>(1, (pool.size() + 1) / 2);
      state = {{"name", inst.name},
               {"n", inst.n},
               {"m", inst.edges.size()},
               {"given_k", inst.walk_count()},
               {"best_k", inst.walk_count()},
               {"converged", false},
               {"checks", 0},
               {"seconds", 0.0},
               {"seed", seed},
               {"instance_id", id},
               {"start", inst.start}};
    }
    const auto deadline = began + std::chrono::duration<double>(seconds);
    const double previous = state.at("seconds");
    std::mutex mutex;
    std::condition_variable cv;
    bool done = false, verified = false;
    std::exception_ptr error;
    std::thread worker([&] {
      try {
        auto yes = [](const nscover::Instance &trial) {
          auto result = nscover::solve_pairflow(trial);
          if (result.status != nscover::Status::Yes)
            return false;
          nscover::check_walks(trial,
                               nscover::build_walks(trial, result.tails));
          return true;
        };
        if (!yes(inst))
          throw std::runtime_error("initial/checkpoint vector is not YES");
        {
          std::lock_guard<std::mutex> lock(mutex);
          state["checks"] = state.at("checks").get<std::uint64_t>() + 1;
          state["pool"] = pool;
          state["chunk"] = chunk;
          state["cursor"] = cursor;
          state["witness"] = "checked";
          verified = true;
        }
        while (!state.at("converged").get<bool>()) {
          if (cursor >= pool.size()) {
            std::lock_guard<std::mutex> lock(mutex);
            if (chunk == 1) {
              state["converged"] = true;
              break;
            }
            chunk = (chunk + 1) / 2;
            cursor = 0;
            state["chunk"] = chunk;
            state["cursor"] = cursor;
            continue;
          }
          auto end = std::min(pool.size(), cursor + chunk);
          auto trial = inst;
          for (auto i = cursor; i < end; ++i)
            --trial.start[pool[i]];
          bool accepted = yes(trial);
          std::lock_guard<std::mutex> lock(mutex);
          state["checks"] = state.at("checks").get<std::uint64_t>() + 1;
          if (accepted) {
            inst.start = std::move(trial.start);
            pool.erase(pool.begin() + cursor, pool.begin() + end);
            state["start"] = inst.start;
            state["best_k"] = inst.walk_count();
            state["pool"] = pool;
          } else {
            // Tokens of a vertex are contiguous. Equal-sized chunks
            // entirely at that vertex produce the identical vector;
            // do not solve that same rejected vector repeatedly.
            const int v = pool[cursor];
            const bool one_vertex =
                std::all_of(pool.begin() + cursor, pool.begin() + end,
                            [v](int w) { return w == v; });
            cursor = end;
            if (one_vertex) {
              auto run_end = cursor;
              while (run_end < pool.size() && pool[run_end] == v)
                ++run_end;
              cursor += ((run_end - cursor) / chunk) * chunk;
            }
          }
          state["cursor"] = cursor;
        }
      } catch (...) {
        error = std::current_exception();
      }
      {
        std::lock_guard<std::mutex> lock(mutex);
        done = true;
      }
      cv.notify_one();
    });
    // The solver has no cancellation API. Exit without joining an unfinished
    // in-process call; only completed, witness-checked removals enter state.
    std::unique_lock<std::mutex> lock(mutex);
    cv.wait_until(lock, deadline, [&] { return done; });
    if (verified) {
      state["seconds"] =
          previous +
          std::chrono::duration<double>(Clock::now() - began).count();
      save(output, state);
      Json summary;
      for (const auto *key : {"name", "n", "m", "given_k", "best_k",
                              "converged", "checks", "seconds"})
        summary[key] = state.at(key);
      std::cout << summary.dump() << '\n' << std::flush;
    }
    if (!done) {
      if (!verified)
        std::cerr << "deadline before initial witness check; no new state\n"
                  << std::flush;
      std::_Exit(verified ? 0 : 2);
    }
    lock.unlock();
    worker.join();
    if (error)
      std::rethrow_exception(error);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "mink: " << e.what() << '\n';
    return 2;
  }
}
