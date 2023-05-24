FROM ultimate-base

# Install UA
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateAutomizer-linux.zip
RUN unzip UltimateAutomizer-linux.zip
RUN mv UAutomizer-linux /home/maze/tools/ultimate
RUN mv /home/maze/tools/run_ultimate.sh /home/maze/tools/run_ua.sh

WORKDIR /home/maze/workspace