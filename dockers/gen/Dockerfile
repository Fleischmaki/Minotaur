FROM minotaur-base

USER maze
WORKDIR /home/maze/workspace

# Get additional dependencies 
RUN sudo apt-get update && sudo apt-get -y install \
    pip \
&& sudo rm -rf /var/lib/apt/lists/*


# Install requirements
ADD requirements.txt /home/maze/workspace/requirements.txt
RUN pip install -r requirements.txt
RUN python3 -m pysmt install --confirm-agreement --z3
ADD token.txt /home/maze/workspace/token.txt
RUN sudo chmod +r token.txt

WORKDIR /home/maze/workspace
RUN git clone https://$(cat /home/maze/workspace/token.txt)@github.com/Fleischmaki/Minotaur.git -c core.sshCommand 
WORKDIR /home/maze/workspace/Minotaur
RUN git checkout working
WORKDIR /home/maze/workspace