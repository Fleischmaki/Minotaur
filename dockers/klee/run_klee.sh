#! /bin/bash
sudo mkdir /seeds/output;
clang -I klee_src/include/klee -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone /seeds/*.c;
for f in $(ls | grep .bc); 
    do klee --write-smt2s --only-output-states-covering-new --output-dir="${f%.bc}" --max-time 300s $f; 
    sudo cp -r ${f%.bc} /seeds/output;
done;