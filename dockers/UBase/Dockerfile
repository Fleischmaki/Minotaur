FROM maze-base

# Install dependencies
RUN apt-get -y install make clang openjdk-11-jre

WORKDIR /home/maze/tools/

USER maze

# Add scripts
ADD run_ultimate.sh /home/maze/tools/run_ultimate.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py
ADD unreach.prp /home/maze/workspace/unreach.prp