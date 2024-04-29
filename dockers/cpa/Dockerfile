FROM minotaur-cpa-base as build
# Install
RUN ant

### Add scripts
FROM minotaur-base
COPY --from=build /home/maze/tools /home/maze/tools
USER maze

RUN /home/maze/tools/cpa/scripts/cpa.sh

WORKDIR /home/maze/workspace