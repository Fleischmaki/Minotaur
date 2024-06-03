FROM minotaur-cpa-base as build
# Install
RUN git pull
RUN ant

### Add scripts
FROM minotaur-base
COPY --from=build /home/maze/tools /home/maze/tools
USER maze

RUN /home/maze/tools/cpa/scripts/cpa.sh
RUN sudo chmod +x /home/maze/tools/*.sh

WORKDIR /home/maze/workspace