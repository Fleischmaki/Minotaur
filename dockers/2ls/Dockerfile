FROM minotaur-esbmc-base

USER root
RUN apt-get update && apt-get install -y \
    g++ \
    flex \
    bison \
    curl \
    patch \
    cmake \
    lcov \
&& rm -rf /var/lib/apt/lists/*

USER maze
WORKDIR /home/maze/tools
RUN git clone http://github.com/diffblue/2ls
WORKDIR /home/maze/tools/2ls
RUN ./build.sh  
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD run_2ls.sh /home/maze/tools/run_2ls.sh

RUN sudo chmod +x /home/maze/tools/run_2ls.sh

WORKDIR /home/maze/workspace

