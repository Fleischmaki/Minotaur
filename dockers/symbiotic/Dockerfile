# FROM maze-base

# WORKDIR /home/maze/tools

# RUN apt-get update && apt-get install -y \
#     gcc-multilib \
#     rsync \
#     cmake \
#     make \
#     curl \
#     build-essential \ 
# && rm -rf /var/lib/apt/lists/*

# RUN git clone https://github.com/staticafi/symbiotic
# WORKDIR /home/maze/tools/symbiotic
# RUN ./build.sh -j2

# ### Build not working yet, grap prebuilt docker image
FROM mchalupa/symbiotic:latest

### Add maze user
RUN groupadd --gid 2000 maze \
    && useradd --uid 2000 --gid maze --shell /bin/bash --create-home maze

### Get python
RUN apt-get update && apt-get install -y \
    python3 \
&& rm -rf /var/lib/apt/lists/*


### Set up directory structure
USER maze
RUN mkdir -p /home/maze/tools
ADD ./utils.py /home/maze/tools/utils.py
RUN mkdir -p /home/maze/workspace
ADD run_symbiotic.sh /home/maze/tools/run_symbiotic.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
USER root
RUN chmod +x /home/maze/tools/run_symbiotic.sh
USER maze
WORKDIR /home/maze/workspace
