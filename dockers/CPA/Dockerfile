FROM maze-base

RUN apt -y install gcc

# Install
WORKDIR /home/maze/tools/

#RUN wget https://download.java.net/java/GA/jdk19.0.2/fdb695a9d9064ad6b064dc6df578380c/7/GPL/openjdk-19.0.2_linux-x64_bin.tar.gz
RUN wget https://cpachecker.sosy-lab.org/CPAchecker-2.2-unix.zip
#RUN tar -xf openjdk-19.0.2_linux-x64_bin.tar.gz
RUN unzip CPAchecker-2.2-unix.zip
RUN mv CPAchecker-2.2-unix cpa
#RUN mv jdk-19.0.2 java
#RUN export PATH=$PATH:/home/maze/tools/java/bin

### Add scripts
USER maze

ADD run_cpa.sh /home/maze/tools/run_cpa.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD svcompNotl.properties /home/maze/tools/cpa/config/svcompNotl.properties

RUN /home/maze/tools/cpa/scripts/cpa.sh

WORKDIR /home/maze/workspace