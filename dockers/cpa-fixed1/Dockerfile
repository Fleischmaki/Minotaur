FROM minotaur-cpa-base

# Install
WORKDIR /home/maze/tools/cpa
RUN git checkout cdee5c75 
RUN ant

RUN mv /home/maze/tools/run_cpa.sh /home/maze/tools/run_cpa-fixed1.sh

WORKDIR /home/maze/workspace