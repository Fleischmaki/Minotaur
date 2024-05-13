FROM minotaur-cpa-base as build
# Install
RUN git pull
RUN ant

### Add scripts
FROM minotaur-base
COPY --from=build /home/maze/tools /home/maze/tools
USER maze

RUN /home/maze/tools/cpa/scripts/cpa.sh

RUN sudo apt-get update && sudo apt-get install -y \
    cvise \
&& sudo rm -rf /var/lib/apt/lists/*

ADD reduce.sh /home/maze/tools
ADD reduce_helper.sh /home/maze/tools
RUN sudo chmod +x /home/maze/tools/*.sh

WORKDIR /home/maze/workspace