FROM minotaur-cpa-base

# Install
WORKDIR /home/maze/tools/cpa
RUN git checkout 568683fe 
RUN ant

RUN mv /home/maze/tools/run_cpa.sh /home/maze/tools/run_cpa-fixed2.sh

WORKDIR /home/maze/workspace