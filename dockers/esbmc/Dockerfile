FROM maze-base

### Install Dependencies
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gperf \
    libgmp-dev \
    bison \
    curl \
    flex \
    gcc-multilib \
    linux-libc-dev \
    libboost-all-dev \
    libtinfo-dev \
    ninja-build \
    python3-setuptools \
    unzip \
    python3-pip \
    openjdk-8-jre \
    lld \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /home/maze/tools

### Get CMAKE manually, as we need version >= 3.18
RUN wget https://github.com/Kitware/CMake/releases/download/v3.27.2/cmake-3.27.2-linux-x86_64.tar.gz
RUN tar xf cmake-3.27.2-linux-x86_64.tar.gz
RUN mv cmake-3.27.2-linux-x86_64 cmake
ENV PATH=$PATH:/home/maze/tools/cmake/bin

### Install ESBM
WORKDIR /home/maze/tools
RUN git clone https://github.com/esbmc/esbmc

## Set up SMT solvers
# Boolector
RUN git clone --depth=1 --branch=3.2.1 https://github.com/boolector/boolector
WORKDIR /home/maze/tools/boolector
RUN ./contrib/setup-lingeling.sh
RUN ./contrib/setup-btor2tools.sh
RUN ./configure.sh --prefix $PWD/../boolector-release
WORKDIR /home/maze/tools/boolector/build
RUN make -j9 && make install

# CVC4
WORKDIR /home/maze/tools
RUN pip3 install toml
RUN git clone https://github.com/CVC4/CVC4.git 
WORKDIR /home/maze/tools/CVC4
RUN git reset --hard b826fc8ae95fc && ./contrib/get-antlr-3.4 && ./configure.sh --optimized --prefix=../cvc4 --static --no-static-binary 
WORKDIR /home/maze/tools/CVC4/build
RUN make -j4 && make install 

# MathSAT
WORKDIR /home/maze/tools
RUN wget http://mathsat.fbk.eu/download.php?file=mathsat-5.5.4-linux-x86_64.tar.gz -O mathsat.tar.gz && tar xf mathsat.tar.gz && mv mathsat-5.5.4-linux-x86_64 mathsat

# Yices
RUN wget https://gmplib.org/download/gmp/gmp-6.1.2.tar.xz && tar xf gmp-6.1.2.tar.xz && rm gmp-6.1.2.tar.xz
WORKDIR /home/maze/tools/gmp-6.1.2
RUN ./configure --prefix $PWD/../gmp --disable-shared ABI=64 CFLAGS=-fPIC CPPFLAGS=-DPIC && make -j4 && make install
WORKDIR /home/maze/tools
RUN git clone https://github.com/SRI-CSL/yices2.git
WORKDIR /home/maze/tools/yices2
RUN git checkout Yices-2.6.1 && autoreconf -fi && ./configure --prefix $PWD/../yices --with-static-gmp=$PWD/../gmp/lib/libgmp.a && make -j9 && make static-lib && make install && cp ./build/x86_64-pc-linux-gnu-release/static_lib/libyices.a ../yices/lib

# Z3
WORKDIR /home/maze/tools
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.8.9/z3-4.8.9-x64-ubuntu-16.04.zip && unzip z3-4.8.9-x64-ubuntu-16.04.zip && mv z3-4.8.9-x64-ubuntu-16.04 z3

# Bitwuzla
RUN git clone --depth=1 --branch=smtcomp-2021 https://github.com/bitwuzla/bitwuzla.git
WORKDIR /home/maze/tools/bitwuzla
RUN ./contrib/setup-lingeling.sh && ./contrib/setup-btor2tools.sh && ./contrib/setup-symfpu.sh && ./configure.sh --prefix $PWD/../bitwuzla-release
WORKDIR /home/maze/tools/bitwuzla/build
RUN cmake -DGMP_INCLUDE_DIR=$PWD/../../gmp/include -DGMP_LIBRARIES=$PWD/../../gmp/lib/libgmp.a -DONLY_LINGELING=ON ../ && make -j8 && make install

### Build esbmc
WORKDIR /home/maze/tools/esbmc
RUN mkdir build 
WORKDIR /home/maze/tools/esbmc/build
RUN cmake .. -GNinja -DDOWNLOAD_DEPENDENCIES=On -DBUILD_STATIC=On -DBoolector_DIR=$PWD/../../boolector-release -DZ3_DIR=$PWD/../../z3 -DENABLE_MATHSAT=ON -DMathsat_DIR=$PWD/../../mathsat -DENABLE_YICES=On -DYices_DIR=$PWD/../../yices -DCVC4_DIR=$PWD/../../cvc4 -DBitwuzla_DIR=$PWD/../../bitwuzla-release -DCMAKE_INSTALL_PREFIX:PATH=$PWD/../../release
RUN cmake --build . -j1
RUN ninja install

WORKDIR /home/maze/tools
USER maze

ADD run_esbmc.sh /home/maze/tools/run_esbmc.sh
RUN sudo chmod +x /home/maze/tools/run_esbmc.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py

