FROM minotaur-esbmc-base

USER maze
WORKDIR /home/maze/tools/esbmc
# Cuold be outdated as we cloned in base
RUN git pull 

RUN mkdir build 
WORKDIR /home/maze/tools/esbmc/build
RUN cmake .. -GNinja -DENABLE_COVERAGE=On -DDOWNLOAD_DEPENDENCIES=On -DBUILD_STATIC=On -DBoolector_DIR=$PWD/../../boolector-release -DZ3_DIR=$PWD/../../z3 -DENABLE_MATHSAT=ON -DMathsat_DIR=$PWD/../../mathsat -DENABLE_YICES=On -DYices_DIR=$PWD/../../yices -DCVC4_DIR=$PWD/../../cvc4 -DGMP_DIR=$PWD/../../gmp -DCMAKE_INSTALL_PREFIX:PATH=$PWD/../../release
RUN cmake --build . -j6
RUN ninja install

RUN pip3 install gcovr

WORKDIR /home/maze/tools
ADD run_esbmc.sh /home/maze/tools/run_esbmc.sh
ADD get_coverage.sh /home/maze/tools/get_coverage.sh
RUN sudo chmod +x /home/maze/tools/*.sh
ADD get_tcs.py /home/maze/tools/get_tcs.py

### Cleanup
WORKDIR /home/maze/workspace