# Keep Ulmus's R550 driver: compile Ada kernels with the existing CUDA 12.4 base.
FROM nvidia/cuda@sha256:622e78a1d02c0f90ed900e3985d6c975d8e2dc9ee5e61643aed587dcf9129f42
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3 python3-venv python3-dev git curl ca-certificates \
    libgomp1 libnuma-dev pkg-config && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/strata
COPY . .
RUN python3 -m venv .venv && .venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH=/opt/strata/.venv/bin:$PATH STRATA_GGUF_PY=/opt/strata/ref/llama.cpp/gguf-py
RUN cmake -S . -B /opt/strata-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES=89 -DSTRATA_BUILD_TESTS=OFF \
    -DSTRATA_BUILD_CONVERSATION_TESTS=ON -DSTRATA_PARITY_PROMPT_ATTN=ON \
    -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_GGML_DIR=/opt/strata/ref/llama.cpp \
    && cmake --build /opt/strata-build -j 12 --target \
    strata strata-device ple_reader_test pinned_shared_test native_expert_parity \
    qsa_prompt_attn_parity conversation_cache_test conversation_memory_test
RUN cmake -S ref/llama.cpp -B /opt/llama-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_CURL=OFF \
    && cmake --build /opt/llama-build -j 12 --target llama-server llama-bench llama-cli
RUN cmake -S tools/vision -B /opt/vision-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DLLAMA_DIR=/opt/strata/ref/llama.cpp \
    -DSTRATA_VISION_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 \
    && cmake --build /opt/vision-build -j 12 --target strata-vision
RUN cmake --build /opt/strata-build -j 2 --target coupled_draft_test sampler_parity
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/local/cuda/lib64
CMD ["python", "-m", "serve.server", "--engine", "strata", "--config", "/work/profiles/flash-q4.json", "--port", "19623"]
