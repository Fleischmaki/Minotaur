FROM minotaur-base

# Install dependencies
RUN apt-get update && apt-get install -y \
    make \
    clang \
    maven \
    openjdk-11-jre \
    zip \
    g++ \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /home/maze/tools/

USER maze

# Add scripts
RUN git clone https://github.com/ultimate-pa/ultimate.git

# Get old version 
WORKDIR /home/maze/tools/ultimate
RUN git checkout bfb52b7

WORKDIR /home/maze/tools/ultimate/releaseScripts/default
RUN ./makeFresh.sh
RUN mv *-linux /home/maze/tools

WORKDIR /home/maze/tools/

RUN mv UAutomizer-linux ua
RUN mv UGemCutter-linux ugc
RUN mv UTaipan-linux ut
RUN mv UKojak-linux uk

ADD run_ultimate.sh /home/maze/tools/run_ultimate-bug2.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp

ENV PATH=$PATH:/home/maze/tools/ua/

WORKDIR /home/maze/workspace