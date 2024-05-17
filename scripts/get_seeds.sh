#!/bin/bash
echo "[*] Cloning into directory smt_comp_benchmarks"
for logic in BV ABV UFBV AUFBV LIA ALIA UFLIA AUFLIA; do
    wget "https://zenodo.org/records/11061097/files/QF_$logic.tar.zst";
    tar xf "QF_$logic.tar.zst";
    rm "QF_$logic.tar.zst";
done
mv non-incremental smt_comp_benchmarks