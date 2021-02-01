#! /usr/bin/bash

SANDBOX=${SANDBOX:-sandbox}

for i in 1 2 3; do
    python annotations_to_training.py $SANDBOX/annotations-$i.json > $SANDBOX/TRAINING-annotations-$i.json
done
