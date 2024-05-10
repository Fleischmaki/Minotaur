FROM minotaur-esbmc-base as build

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

FROM minotaur-base
USER maze 
COPY --from=build /home/maze/tools/2ls /home/maze/tools/2ls

RUN sudo apt-get update && sudo apt-get install -y \
    cbmc \
    cvise \
&& sudo rm -rf /var/lib/apt/lists/*


ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD run_2ls.sh /home/maze/tools/run_2ls.sh
ADD reduce.sh /home/maze/tools/reduce.sh
ADD reduce_helper.sh /home/maze/tools/reduce_helper.sh

RUN sudo chmod +x /home/maze/tools/*.sh

WORKDIR /home/maze/workspace

