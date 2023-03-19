FROM ultimate-base

# Install UA
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateKojak-linux.zip
RUN unzip UltimateKojak-linux.zip
RUN mv UKojak-linux /home/maze/tools/ultimate
RUN mv /home/maze/tools/run_ultimate.sh /home/maze/tools/run_uk.sh

WORKDIR /home/maze/workspace