// Fixture-free CPU test for PR #500. Serial ggml quantizers are the reference.
// Synthetic weights use the actual Flash-Next expert geometry and relevant formats.
#include "strata/kernels/cpu/pool.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"
#include "ggml.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <stdexcept>
#include <vector>

namespace cpu = strata::kernels::cpu;
struct alignas(64) Token {
    cpu::ActQ q2_down_act{};
    std::array<uint8_t, cpu::kNativeActBytes> act{};
    std::array<uint8_t, cpu::kNativeHBytes> hq{};
    std::array<float, cpu::FF> ff{};
    std::array<float, cpu::H> want{}, got{};
};

static std::vector<uint8_t> weights(const cpu::NativeFmt& f, int seed) {
    std::vector<uint8_t> blob(f.bytes);
    std::mt19937 rng(seed);
    std::normal_distribution<float> normal(0, .02f);
    auto quant = [&](int type, int rows, int cols, size_t off) {
        std::vector<float> floats(size_t(rows) * cols), importance(cols, 1.f);
        for (float& value : floats) value = normal(rng);
        ggml_quantize_chunk(ggml_type(type), floats.data(), blob.data() + off,
                           0, rows, cols, ggml_quantize_requires_imatrix(ggml_type(type))
                               ? importance.data() : nullptr);
    };
    quant(f.gu_type, cpu::FF, cpu::H, 0);
    quant(f.gu_type, cpu::FF, cpu::H, f.up_off);
    quant(f.d_type, cpu::H, cpu::FF, f.down_off);
    return blob;
}

static int check(int gu, int down, int workers, bool host, int count, bool sleep) {
    cpu::NativeFmt f;
    std::string err;
    if (!cpu::native_fmt(gu, down, cpu::H, cpu::FF, f, err))
        throw std::runtime_error(err);
    const auto blob = weights(f, gu + down);
    std::vector<Token> tokens(size_t(count) * cpu::MAXT);
    std::vector<cpu::ExpertJobMulti> jobs(count);
    std::mt19937 rng(42);
    std::normal_distribution<float> normal(0, .7f);
    for (int e = 0; e < count; ++e) {
        auto& job = jobs[e];
        job.blob = blob.data();
        job.nt = 1 + e % cpu::MAXT;
        std::array<const void*, cpu::MAXT> aq{}, hq{};
        std::array<const cpu::ActQ*, cpu::MAXT> q2_act{};
        std::array<float*, cpu::MAXT> ff{}, out{};
        for (int t = 0; t < job.nt; ++t) {
            auto& token = tokens[size_t(e) * cpu::MAXT + t];
            std::array<float, cpu::H> x;
            for (float& value : x) value = normal(rng);
            cpu::native_quant_act(f, x.data(), token.act.data());
            aq[t] = job.nact[t] = token.act.data();
            ff[t] = token.ff.data();
            hq[t] = token.hq.data();
            q2_act[t] = &token.q2_down_act;
            out[t] = token.want.data();
            job.out[t] = token.got.data();
        }
        cpu::native_gu_rows(f, blob.data(), aq.data(), job.nt, ff.data(), 0, cpu::FF);
        for (int t = 0; t < job.nt; ++t) {
            auto& token = tokens[size_t(e) * cpu::MAXT + t];
            if (down == 42) cpu::act_quant_any(ff[t], cpu::FF, token.q2_down_act);
            else cpu::native_quant_h(f, ff[t], token.hq.data());
        }
        if (down == 42)
            cpu::q2_rows_any(blob.data() + f.down_off, f.d_row, cpu::FF / 64,
                             q2_act.data(), job.nt, out.data(), 0, cpu::H);
        else cpu::native_down_rows(f, blob.data(), hq.data(), job.nt, out.data(), 0, cpu::H);
    }
    cpu::ExpertPool pool(workers, false, host);
    if (sleep) std::this_thread::sleep_for(std::chrono::milliseconds(30));
    // Repeated dispatches catch stale phase descriptors as well as arithmetic changes.
    for (int repeat = 0; repeat < 4; ++repeat) {
        for (auto& token : tokens) token.got.fill(NAN);
        pool.run_split_multi_native(f, jobs.data(), count);
        for (int e = 0; e < count; ++e)
            for (int t = 0; t < jobs[e].nt; ++t) {
                const auto& token = tokens[size_t(e) * cpu::MAXT + t];
                if (std::memcmp(token.want.data(), token.got.data(), sizeof(token.want))) {
                    std::printf("FAIL gu=%d down=%d workers=%d host=%d experts=%d token=%d repeat=%d\n",
                                gu, down, workers, host, count, t, repeat);
                    return 1;
                }
            }
    }
    std::printf("PASS bitwise gu=%d down=%d workers=%d host=%d experts=%d sleep=%d threshold=%d\n",
                gu, down, workers, host, count, sleep, pool.quant_threshold());
    return 0;
}

int main() {
    int failures = 0;
    // Force serial and parallel quant phases; include >96 experts to test chunk boundaries.
    for (const char* threshold : {"9999", "0"}) {
        setenv("STRATA_POOL_QUANT_THRESH", threshold, 1);
        for (const auto pair : {std::pair<int,int>{GGML_TYPE_IQ3_S, GGML_TYPE_IQ4_NL},
                              std::pair<int,int>{GGML_TYPE_IQ3_S, 42},
                              std::pair<int,int>{GGML_TYPE_Q4_K, GGML_TYPE_Q5_1}}) {
            failures += check(pair.first, pair.second, 4, true, 8, false);
            failures += check(pair.first, pair.second, 3, false, 9, true);
            failures += check(pair.first, pair.second, 11, true, 97, true);
        }
    }
    std::printf("Native pool parity: %d failures\n", failures);
    return failures ? 1 : 0;
}
