FROM minotaur-esbmc-base

USER root 
RUN apt-get update && DEBIANFRONTEND=noninteractive apt-get install -y \
    patch \
    default-jdk \
    maven \
&& rm -rf /var/lib/apt/lists/*

USER maze
WORKDIR /home/maze/tools
RUN git clone https://github.com/diffblue/cbmc.git
WORKDIR /home/maze/tools/cbmc
RUN git submodule update --init
RUN cmake -S . -Bbuild -Denable_coverage=True -DCMAKE_CXX_OUTPUT_EXTENSION_REPLACE=ON 
RUN cmake --build build

RUN pip3 install gcovr

ENV PATH="${PATH}:/home/maze/tools/boolector-release/bin:/home/maze/tools/cvc4/bin:/home/maze/tools/yices/bin:/home/maze/tools/z3/bin:/home/maze/tools/mathsat/bin:/home/maze/tools/cbmc/build/bin"

WORKDIR /home/maze/workspace

ADD run_cbmc.sh /home/maze/tools/run_cbmc.sh
ADD get_coverage.sh /home/maze/tools/get_coverage.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
RUN sudo chmod +rwx /home/maze/tools/*

