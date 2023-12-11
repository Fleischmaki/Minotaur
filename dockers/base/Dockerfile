FROM ubuntu:20.04

### Prepare apt
RUN sed -i 's/archive.ubuntu.com/ftp.daumkakao.com/g' /etc/apt/sources.list
RUN sed -i 's/# deb-src/deb-src/g' /etc/apt/sources.list
ENV DEBIAN_FRONTEND="noninteractive"

### Create maze account
RUN groupadd --gid 2000 maze \
    && useradd --uid 2000 --gid maze --shell /bin/bash --create-home maze

### Set up directory structure
USER maze
RUN mkdir -p /home/maze/tools
RUN mkdir -p /home/maze/workspace

USER root

### Install common packages
RUN apt-get update && apt-get install -y \
    vim \
    git\
    wget \
    unzip \
    sudo \
    python3 \
    gcc \
    make \
&& rm -rf /var/lib/apt/lists/*

RUN echo 'maze  ALL=(root) NOPASSWD: ALL' >> /etc/sudoers