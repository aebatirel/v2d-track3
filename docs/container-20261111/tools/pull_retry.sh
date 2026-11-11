#!/bin/bash
D=sha256:77121a430d4243ca661ae26ec3f0c0f03bd45b07679d20e61e4f756ea3104204
for i in $(seq 1 40); do
  docker pull mirror.gcr.io/vastai/pytorch@$D && { echo PULL-OK mirror; exit 0; }
  docker pull vastai/pytorch@$D && { echo PULL-OK hub; exit 0; }
  sleep 75
done
echo PULL-FAIL
