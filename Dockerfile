FROM minotaur-base
USER root
WORKDIR /home/maze/workspace

# Get additional dependencies 
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    software-properties-common \
&& rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    python3.10 \
    python3.10-dev \
&& rm -rf /var/lib/apt/lists/*

USER maze
RUN sudo update-alternatives --install /usr/bin/python3 pyhton3 /usr/bin/python3.10 1

# Install pip
RUN wget https://bootstrap.pypa.io/get-pip.py &&  python3 get-pip.py && rm get-pip.py

# # Install requirements
ADD dockers/gen/requirements.txt /home/maze/workspace/requirements.txt
RUN /home/maze/.local/bin/pip3 install -r requirements.txt
RUN python3 -m pysmt install --confirm-agreement --z3
WORKDIR /home/maze/tools
RUN git clone https://github.com/testsmt/yinyang.git yinyang
WORKDIR /home/maze/tools/yinyang
RUN git checkout f38bb10
ADD dockers/gen/yinyang.patch /home/maze/tools/yinyang.patch
RUN git apply /home/maze/tools/yinyang.patch
ENV PATH=/home/maze/tools/yinyang/bin:$PATH

WORKDIR /home/maze/workspace
# ADD token.txt /home/maze/workspace/token.txt
# RUN sudo chmod +r token.txt
# RUN git clone https://$(cat /home/maze/workspace/token.txt)@github.com/Fleischmaki/Minotaur.git -c core.sshCommand 
# WORKDIR /home/maze/workspace/Minotaur
# RUN git checkout working
ADD . /home/maze/workspace//Minotaur

WORKDIR /home/maze/workspace