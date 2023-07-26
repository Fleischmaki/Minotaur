FROM maze-base

RUN apt-get -y install cbmc

USER maze

ADD run_cbmc.sh /home/maze/tools/run_cbmc.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py

RUN sudo chmod -R +rwx /home/maze/tools

WORKDIR /home/maze/workspace