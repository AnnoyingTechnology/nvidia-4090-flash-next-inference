FROM ulmus/strata:99f3dbd-ownerapi
WORKDIR /opt/strata-next
COPY source/ .
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN cmake -S . -B /opt/strata-next-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES=89-real -DSTRATA_BUILD_TESTS=OFF \
    -DSTRATA_PORTABLE=OFF -DSTRATA_BUILD_CONVERSATION_TESTS=ON \
    -DSTRATA_PARITY_PROMPT_ATTN=ON -DSTRATA_NATIVE_EXPERTS=ON \
    -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_GGML_DIR=/opt/strata/ref/llama.cpp \
    && cmake --build /opt/strata-next-build -j 12 --target strata strata_kq
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/local/cuda/lib64
LABEL ulmus.strata.commit=146df3c468739147f520ac3816de806f71232571 ulmus.purpose=isolated-update-20261108
CMD ["/opt/strata-next-build/strata", "--help"]
