FROM maze-base

USER maze
WORKDIR /home/maze/workspace

# Get additional dependencies 
RUN sudo apt-get update
RUN sudo apt-get -y install pip

# Install requirements
ADD requirements.txt /home/maze/workspace/requirements.txt
RUN pip install -r requirements.txt

ADD token.txt /home/maze/workspace/token.txt
RUN sudo chmod +r token.txt

RUN git clone https://$(cat token.txt)@github.com/Fleischmaki/Minotaur.git -c core.sshCommand 