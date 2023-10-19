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
ADD run_ultimate.sh /home/maze/tools/run_ultimate-release.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp

WORKDIR  /home/maze/tools/
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateAutomizer-linux.zip
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateTaipan-linux.zip
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateKojak-linux.zip
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateGemCutter-linux.zip

RUN unzip UltimateAutomizer-linux.zip
RUN unzip UltimateTaipan-linux.zip
RUN unzip UltimateKojak-linux.zip
RUN unzip UltimateGemCutter-linux.zip

RUN rm *.zip

RUN mv UAutomizer-linux ua
RUN mv UTaipan-linux ut
RUN mv UKojak-linux uk
RUN mv UGemCutter-linux ugc


WORKDIR /home/maze/workspace