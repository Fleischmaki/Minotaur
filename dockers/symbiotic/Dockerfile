FROM minotaur-base

WORKDIR /home/maze/tools

RUN apt-get update && apt-get install -y \
    rsync \
    cmake \
    npm \
&& rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/staticafi/symbiotic
WORKDIR /home/maze/tools/symbiotic
RUN apt-get update && yes | scripts/install-ubuntu.sh 
RUN ./build.sh 

### Set up directory structure
USER maze
RUN mkdir -p /home/maze/tools
RUN mkdir -p /home/maze/workspace
ADD run_symbiotic.sh /home/maze/tools/run_symbiotic.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
USER root
RUN chmod +x /home/maze/tools/run_symbiotic.sh
USER maze
WORKDIR /home/maze/workspace
