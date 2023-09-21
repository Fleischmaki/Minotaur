FROM maze-base

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

WORKDIR /home/maze/tools/ultimate/releaseScripts/default
RUN ./makeFresh.sh
RUN mv *-linux /home/maze/tools

WORKDIR /home/maze/tools/
ADD run_ultimate.sh /home/maze/tools/run_ultimate.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp


WORKDIR /home/maze/workspace