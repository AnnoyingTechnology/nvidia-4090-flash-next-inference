/* Diagnostic sequential read ceiling; not an inference benchmark or STREAM score.
 * Build: gcc -O3 -march=native -fopenmp host_memory_read_probe.c -o /tmp/ulmus-memory-read
 * 1 GiB exceeds LLC. Each trial reads all bytes, with a checked checksum. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

int main(void) {
    const size_t n = ((size_t)1 << 30) / sizeof(uint64_t);
    uint64_t *a = NULL;
    if (posix_memalign((void **)&a, 4096, n * sizeof(*a))) return 1;
    #pragma omp parallel for num_threads(12) schedule(static)
    for (size_t i = 0; i < n; ++i) a[i] = i & 255;
    const uint64_t expected = (uint64_t)(n / 256) * 32640;
    const int counts[] = {1, 12};
    for (int c = 0; c < 2; ++c) {
        int threads = counts[c];
        for (int trial = 0; trial < 6; ++trial) {
            uint64_t total = 0;
            double start = omp_get_wtime();
            #pragma omp parallel for simd num_threads(threads) schedule(static) reduction(+:total)
            for (size_t i = 0; i < n; ++i) total += a[i];
            double seconds = omp_get_wtime() - start;
            if (total != expected) { free(a); return 2; }
            printf("{\"threads\":%d,\"trial\":%d,\"bytes\":%zu,\"seconds\":%.9f,\"gb_s\":%.6f,\"checksum_ok\":true}\n",
                   threads, trial, n * sizeof(*a), seconds, n * sizeof(*a) / seconds / 1e9);
        }
    }
    free(a);
    return 0;
}
