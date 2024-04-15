FROM minotaur-seahorn-base

RUN groupadd --gid 1000 maze \ 
    && useradd --uid 1000 --gid maze --shell /bin/bash --create-home maze
RUN echo 'maze  ALL=(root) NOPASSWD: ALL' >> /etc/sudoers

### Set up directory structure
USER maze
RUN mkdir -p /home/maze/tools
RUN mkdir -p /home/maze/workspace



# Assume that docker-build is ran in the top-level SeaHorn directory
WORKDIR /home/maze/tools
RUN git clone https://github.com/seahorn/seahorn.git  seahorn
# Re-create the build directory that might have been present in the source tree
RUN rm -rf seahorn/build seahorn/debug seahorn/release && \
  mkdir seahorn/build && \
# Remove any third-party dependencies that build process clones
  rm -rf seahorn/clam seahorn/sea-dsa seahorn/llvm-seahorn
WORKDIR /home/maze/tools/seahorn/build

ARG BUILD_TYPE=Coverage

# Build configuration
RUN cmake .. -GNinja \
  -DCMAKE_BUILD_TYPE=Coverage \
  -DZ3_ROOT=/opt/z3-4.8.9 \
  -DYICES2_HOME=/opt/yices-2.6.1 \
  -DCMAKE_INSTALL_PREFIX=run \
  -DCMAKE_CXX_COMPILER=clang++-14 \
  -DCMAKE_C_COMPILER=clang-14 \
  -DSEA_ENABLE_LLD=ON \
  -DCPACK_GENERATOR="TGZ" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_CXX_OUTPUT_EXTENSION_REPLACE=ON  && \
  cmake --build . --target extra  && cmake .. && \
  cmake --build . --target crab  && cmake .. && \
  cmake --build . --target install && \
  cmake --build . --target units_z3 && \
  cmake --build . --target units_yices2 && \
  cmake --build . --target test_type_checker && \
  cmake --build . --target test_hex_dump && \
  cmake --build . --target package && \
  units/units_z3 && \
  units/units_yices2

RUN pip3 install --upgrade gcovr

ENV PATH "/home/maze/tools/seahorn/build/run/bin:$PATH"

USER maze
WORKDIR /home/maze/tools
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD get_coverage.sh /home/maze/tools/get_coverage.sh
ADD run_seahorn.sh /home/maze/tools/run_seahorn.sh
RUN sudo  chmod +x /home/maze/tools/*.sh
WORKDIR /home/maze/workspace