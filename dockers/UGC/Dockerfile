FROM ultimate-base

# Install UA
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateGemCutter-linux.zip
RUN unzip UltimateGemCutter-linux.zip
RUN mv UGemCutter-linux /home/maze/tools/ultimate
RUN mv /home/maze/tools/run_ultimate.sh /home/maze/tools/run_ugc.sh

WORKDIR /home/maze/workspace