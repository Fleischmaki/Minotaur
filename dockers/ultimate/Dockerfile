FROM maze-base

# Install dependencies
RUN apt-get update && apt-get install -y \
    make \
    clang \
    maven \
    openjdk-11-jre \
    zip \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /home/maze/tools/

USER maze

# Add scripts
ADD run_ultimate.sh /home/maze/tools/run_ultimate.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp

RUN git clone https://github.com/ultimate-pa/ultimate.git

WORKDIR /home/maze/tools/ultimate/releaseScripts/default
RUN update-alternatives --config java
RUN ./makeFresh.sh
RUN ls

WORKDIR  /home/maze/tools/
RUN mv /home/maze/tools/ultimate/releaseScripts/default/UAutomizer-linux ua
RUN mv /home/maze/tools/ultimate/releaseScripts/default/UTaipan-linux ut
RUN mv /home/maze/tools/ultimate/releaseScripts/default/UKojak-linux uk
RUN mv /home/maze/tools/ultimate/releaseScripts/default/UGemCutter-linux ugc

WORKDIR /home/maze/workspace