#! /usr/bin/bash

SANDBOX=${SANDBOX:-sandbox}

python train.py --iterations 30 --output-model $SANDBOX/components-model $SANDBOX/TRAINING-*
