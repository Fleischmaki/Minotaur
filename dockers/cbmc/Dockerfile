FROM minotaur-esbmc-base

USER root 
RUN apt-get update && apt-get install -y \
    cbmc \
&& rm -rf /var/lib/apt/lists/*


USER maze

ADD run_cbmc.sh /home/maze/tools/run_cbmc.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py

RUN sudo chmod +rwx /home/maze/tools/*
ENV PATH="${PATH}:/home/maze/tools/boolector-release/bin:/home/maze/tools/cvc4/bin:/home/maze/tools/yices/bin:/home/maze/tools/z3/bin:/home/maze/tools/mathsat/bin"

WORKDIR /home/maze/workspace