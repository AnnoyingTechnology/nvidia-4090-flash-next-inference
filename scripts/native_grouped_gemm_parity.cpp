// FP16 grouped-fallback checks, including heterogeneous sizes and side-stream joins.
#include "strata/prefill/gemm.hpp"
#include "strata/kernels/f16_bits.hpp"
#include <cuda_runtime.h>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

static void checked(cudaError_t e) {
    if (e != cudaSuccess) { std::fprintf(stderr, "%s\n", cudaGetErrorString(e)); std::exit(1); }
}

int main() {
    constexpr int P = 4, K = 64, N = 96;
    for (bool side : {false, true}) {
        for (bool large : {false, true}) {
            const std::array<int,P> rows = large ? std::array<int,P>{128,129,256,257}
                                                 : std::array<int,P>{1,3,17,127};
            cudaStream_t stream;
            checked(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking));
            std::array<uint16_t*,P> x{}, w{};
            std::array<float*,P> y{};
            std::array<std::vector<uint16_t>,P> hx{}, hw{};
            std::array<const uint16_t*,P> px{}, pw{};
            for (int p=0; p<P; ++p) {
                hx[p].resize(rows[p]*K); hw[p].resize(N*K);
                for (size_t j=0; j<hx[p].size(); ++j)
                    hx[p][j]=strata::kernels::f16_from_f32((int((j*13+p*7)%31)-15)/32.0f);
                for (size_t j=0; j<hw[p].size(); ++j)
                    hw[p][j]=strata::kernels::f16_from_f32((int((j*11+p*3)%23)-11)/16.0f);
                checked(cudaMalloc(&x[p],hx[p].size()*2)); checked(cudaMalloc(&w[p],hw[p].size()*2));
                checked(cudaMalloc(&y[p],rows[p]*N*sizeof(float)));
                checked(cudaMemcpyAsync(x[p],hx[p].data(),hx[p].size()*2,cudaMemcpyHostToDevice,stream));
                checked(cudaMemcpyAsync(w[p],hw[p].data(),hw[p].size()*2,cudaMemcpyHostToDevice,stream));
                checked(cudaMemsetAsync(y[p],0xff,rows[p]*N*sizeof(float),stream));
                px[p]=x[p]; pw[p]=w[p];
            }
            const uint16_t **dx{}, **dw{}; float **dy{};
            checked(cudaMalloc(&dx,P*sizeof(void*))); checked(cudaMalloc(&dw,P*sizeof(void*)));
            checked(cudaMalloc(&dy,P*sizeof(void*)));
            checked(cudaMemcpyAsync(dx,px.data(),P*sizeof(void*),cudaMemcpyHostToDevice,stream));
            checked(cudaMemcpyAsync(dw,pw.data(),P*sizeof(void*),cudaMemcpyHostToDevice,stream));
            checked(cudaMemcpyAsync(dy,y.data(),P*sizeof(void*),cudaMemcpyHostToDevice,stream));
            void* workspace{}; checked(cudaMalloc(&workspace,32<<20));
            float max_error=0;
            {
                strata::prefill::Gemm gemm; std::string error;
                if (!gemm.init(stream,error,side)) { std::fprintf(stderr,"%s\n",error.c_str());return 2; }
                gemm.set_buffers(nullptr,0,workspace,32<<20);
                gemm.f16_grouped(dx,dw,dy,px.data(),pw.data(),y.data(),rows.data(),P,N,K);
                checked(cudaStreamSynchronize(stream));
                for (int p=0; p<P; ++p) {
                    std::vector<float> actual(rows[p]*N);
                    checked(cudaMemcpy(actual.data(),y[p],actual.size()*sizeof(float),cudaMemcpyDeviceToHost));
                    for (int r=0;r<rows[p];++r) for (int n=0;n<N;++n) {
                        float reference=0;
                        for (int k=0;k<K;++k)
                            reference+=strata::kernels::f32_from_f16(hx[p][r*K+k])*
                                       strata::kernels::f32_from_f16(hw[p][n*K+k]);
                        const float delta=std::fabs(actual[r*N+n]-reference);
                        if (!std::isfinite(actual[r*N+n]) || delta>1e-5f) return 3;
                        max_error=std::max(max_error,delta);
                    }
                }
            }
            std::printf("grouped GEMM side=%d large=%d max_abs=%g: passed\n",side,large,max_error);
            for (int p=0;p<P;++p) { checked(cudaFree(x[p]));checked(cudaFree(w[p]));checked(cudaFree(y[p])); }
            checked(cudaFree(dx));checked(cudaFree(dw));checked(cudaFree(dy));checked(cudaFree(workspace));
            checked(cudaStreamDestroy(stream));
        }
    }
    std::puts("grouped GEMM parity: 4 configurations passed");
}
