FROM maze-base

# Install dependencies
RUN apt -y install make clang

# Install UA
RUN wget https://github.com/ultimate-pa/ultimate/releases/download/v0.2.3/UltimateAutomizer-linux.zip
RUN unzip UltimateAutomizer-linux.zip
RUN mv UAutomizer-linux /home/maze/tools/UA

WORKDIR /home/maze/tools/

USER maze

# Add scripts
ADD run_ua.sh /home/maze/tools/run_ua.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp

#RUN /home/maze/tools/UA/z3 --version
#RUN /home/maze/tools/UA/Ultimate.py -h

WORKDIR /home/maze/workspace
