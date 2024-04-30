FROM minotaur-cpa-base

# Install
USER mazeRUN git checkout 413c89ea 
RUN ant

RUN mv /home/maze/tools/run_cpa.sh /home/maze/tools/run_cpa-bug4-5.sh

WORKDIR /home/maze/workspace