FROM maze-base

# Install
WORKDIR /home/maze/tools/

RUN sudo apt-get install -y ant openjdk-17-jdk openjdk-17-jre
RUN wget https://github.com/sosy-lab/cpachecker/archive/refs/heads/trunk.zip
RUN unzip trunk.zip
RUN mv cpachecker-trunk cpa

WORKDIR /home/maze/tools/cpa
RUN ant

# Get gcc for preprocessing
RUN apt-get -y install gcc


### Add scripts
USER maze

WORKDIR /home/maze/tools/
ADD run_cpa.sh /home/maze/tools/run_cpa.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD svcompNotl.properties /home/maze/tools/cpa/config/svcompNotl.properties

RUN /home/maze/tools/cpa/scripts/cpa.sh

WORKDIR /home/maze/workspace