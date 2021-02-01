#! /usr/bin/bash

SANDBOX=${SANDBOX:-sandbox}

mkdir -p $SANDBOX

# this CSV file has some heading we don't want, so we skip over them
python ssp.py --reader csv --encoding cp1252 convert /usr/share/CAC/ComplianceAsCode/SSP_GSS1.csv \
    | tail --lines +2 \
    > $SANDBOX/SSP_GSS1.txt
python ssp.py --reader psv-1 convert /usr/share/CAC/ComplianceAsCode/SSP_Enterprise_Network.txt \
    > $SANDBOX/SSP_Enterprise_Network.txt


for i in SSP_GSS1.txt SSP_Enterprise_Network.txt; do
    python sample.py --number 10 $SANDBOX/$i > $SANDBOX/SAMPLED-${i}
done
