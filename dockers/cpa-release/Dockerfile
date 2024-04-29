FROM minotaur-base as build

# Install
WORKDIR /home/maze/tools/

RUN apt-get update && apt-get install -y \
    ant \
    openjdk-17-jdk \
    openjdk-17-jre \
&& rm -rf /var/lib/apt/lists/*

RUN wget https://cpachecker.sosy-lab.org/CPAchecker-2.2-unix.zip
RUN unzip CPAchecker-2.2-unix.zip
RUN mv CPAchecker-2.2-unix cpa

### Add scripts
FROM minotaur-base
COPY --from=build /home/maze/tools/cpa /home/maze/tools/cpa
USER maze

WORKDIR /home/maze/tools/
ADD run_cpa-release.sh /home/maze/tools/run_cpa-release.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py

RUN /home/maze/tools/cpa/scripts/cpa.sh

WORKDIR /home/maze/workspace