ARG BASE_IMAGE=jammy-scm
# Base image with usual build dependencies
FROM buildpack-deps:$BASE_IMAGE

# Install dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
  apt-get install -yqq software-properties-common && \
  apt-get update && \
  apt-get upgrade -yqq && \
  apt-get install -yqq unzip \
      zlib1g-dev \
      ninja-build libgraphviz-dev \
      libgmp-dev libmpfr-dev \
      libboost1.74-dev \
      python3-pip \
      less vim \
      gcc-multilib \
      sudo \
      graphviz libgraphviz-dev python3-pygraphviz \
      lcov gcovr rsync \
      clang-14 lldb-14 lld-14 clang-format-14 && \
  pip3 install lit OutputCheck && \
  pip3 install networkx && \
  mkdir seahorn

# Install z3 v4.8.9 since bionic comes with much older version
WORKDIR /tmp
RUN wget https://github.com/Z3Prover/z3/releases/download/z3-4.8.9/z3-4.8.9-x64-ubuntu-16.04.zip && \
  unzip z3-4.8.9-x64-ubuntu-16.04.zip && \
  mv z3-4.8.9-x64-ubuntu-16.04 /opt/z3-4.8.9

# Install yices 2.6.1
RUN curl -sSOL https://yices.csl.sri.com/releases/2.6.1/yices-2.6.1-x86_64-pc-linux-gnu-static-gmp.tar.gz && \
  tar xf yices-2.6.1-x86_64-pc-linux-gnu-static-gmp.tar.gz && \
  cd /tmp/yices-2.6.1/ && \
  ./install-yices /opt/yices-2.6.1

# Install cmake manually for newer version
RUN wget https://github.com/Kitware/CMake/releases/download/v3.27.2/cmake-3.27.2-linux-x86_64.tar.gz
RUN tar xf cmake-3.27.2-linux-x86_64.tar.gz
RUN mv cmake-3.27.2-linux-x86_64 /opt/cmake
ENV PATH=$PATH:/opt/cmake/bin
