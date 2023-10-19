FROM seahorn/seahorn-llvm14:nightly

USER usea
RUN mkdir -p /home/usea/tools
RUN mkdir -p /home/usea/workspace
ADD run_seahorn.sh /home/usea/tools/run_seahorn.sh
ADD get_tcs.py /home/usea/tools/get_tcs.py

WORKDIR /home/usea/workspace