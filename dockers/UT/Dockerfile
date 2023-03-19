FROM ultimate-base

# Install UA
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateTaipan-linux.zip
RUN unzip UltimateTaipan-linux.zip
RUN mv UTaipan-linux /home/maze/tools/ultimate
RUN mv /home/maze/tools/run_ultimate.sh /home/maze/tools/run_ut.sh

WORKDIR /home/maze/workspace