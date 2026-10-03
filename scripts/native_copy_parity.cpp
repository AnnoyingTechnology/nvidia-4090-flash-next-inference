// Ordered H2D and D2D checks for the CUDA compatibility path; no model oracle.
#include <cuda_runtime.h>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace strata::core {
bool copy_blobs(void* const*, const void* const*, const size_t*, size_t, void*);
}

void checked(cudaError_t error) {
    if (error != cudaSuccess) {
        std::fprintf(stderr, "%s\n", cudaGetErrorString(error));
        std::exit(1);
    }
}

int main() {
    constexpr size_t N = 5;
    const std::array<size_t, N> sizes{1, 63, 4097, 65537, 131072};
    std::array<void*, N> first{}, second{}, host{};
    cudaStream_t stream;
    checked(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking));
    for (size_t i = 0; i < N; ++i) {
        checked(cudaMallocHost(&host[i], sizes[i]));
        checked(cudaMalloc(&first[i], sizes[i]));
        checked(cudaMalloc(&second[i], sizes[i]));
    }
    if (!strata::core::copy_blobs(nullptr, nullptr, nullptr, 0, stream)) return 2;
    for (int pass = 0; pass < 8; ++pass) {
        std::array<const void*, N> sources{};
        for (size_t i = 0; i < N; ++i) {
            auto* values = static_cast<unsigned char*>(host[i]);
            for (size_t j = 0; j < sizes[i]; ++j) values[j] = (j * 37 + i * 13 + pass) % 256;
            sources[i] = host[i];
        }
        if (!strata::core::copy_blobs(first.data(), sources.data(), sizes.data(), N, stream)) return 3;
        for (size_t i = 0; i < N; ++i) sources[i] = first[i];
        if (!strata::core::copy_blobs(second.data(), sources.data(), sizes.data(), N, stream)) return 4;
        checked(cudaStreamSynchronize(stream));
        for (size_t i = 0; i < N; ++i) {
            std::vector<unsigned char> actual(sizes[i]);
            checked(cudaMemcpy(actual.data(), second[i], sizes[i], cudaMemcpyDeviceToHost));
            for (size_t j = 0; j < sizes[i]; ++j) {
                if (actual[j] != (j * 37 + i * 13 + pass) % 256) return 5;
            }
            // Pending writes on a nondefault stream must precede D2D copying.
            checked(cudaMemsetAsync(first[i], pass + 11, sizes[i], stream));
        }
        if (!strata::core::copy_blobs(second.data(), sources.data(), sizes.data(), N, stream)) return 6;
        checked(cudaStreamSynchronize(stream));
        for (size_t i = 0; i < N; ++i) {
            std::vector<unsigned char> actual(sizes[i]);
            checked(cudaMemcpy(actual.data(), second[i], sizes[i], cudaMemcpyDeviceToHost));
            for (auto value : actual) if (value != pass + 11) return 7;
        }
    }
    for (size_t i = 0; i < N; ++i) {
        checked(cudaFree(first[i])); checked(cudaFree(second[i])); checked(cudaFreeHost(host[i]));
    }
    checked(cudaStreamDestroy(stream));
    std::puts("copy parity: 8 passes, 5 sizes, ordered H2D/D2D and zero-copy-count checks passed");
}
