#! /usr/bin/bash

SANDBOX=${SANDBOX:-sandbox}

SSPS=("SSP_Enterprise_Network"
      "SSP_GSS1")

# corresponding catalogs

CATALOGS=("NIST_SP-800-171_rev1"
          "NIST_SP-800-171_rev1"
          "NIST_SP-800-53_rev4")

echo "Processing SSP's"

for (( i=0; i<${#SSPS[@]}; i++ )); do
    ssp="${SSPS[$i]}"
    catalog="${CATALOGS[$i]}"
    echo "  +" "$ssp" "/" "$catalog"
    python ssp.py recognize \
       --components $SANDBOX/known-components.json \
       --model $SANDBOX/components-model \
       --catalog $catalog \
       $SANDBOX/$ssp.txt  > $SANDBOX/$ssp.json
done

python combine.py $SANDBOX/SSP_Enterprise_Network.json $SANDBOX/SSP_GSS1.json > $SANDBOX/combined-components.json

n=`jq '.components|keys[]' < $SANDBOX/combined-components.json | wc -l`
echo "$n candidate components written to $SANDBOX/combined-components.json"

python component_report.py $SANDBOX/combined-components.json $SANDBOX/markdown
echo "Markdown written to $SANDBOX/markdown"

python oscal.py --title "Example SSP Components" $SANDBOX/combined-components.json > $SANDBOX/oscal-components.json
