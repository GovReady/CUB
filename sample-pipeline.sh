#! /bin/sh

# This script demonstrates a component processing pipeline using the sample SSP data files
# in `data/ssps`.
#
# This example uses the pattern matcher in `ssp.py` as opposed to the
# named entity recgonizer, so it does not require training.
#
# Output written to git ignored directory `data/components`.
#
# TODO: provide an example of training!
#

echo "Creating output directory data/components and data/components/markdown"
mkdir -p data/components/markdown

echo "Matching components in data/ssps/ssp1.jsonl: writing data/components/ssp1-components.json"
python ssp.py --reader json-l match --components data/ssp-components.json data/ssps/ssp1.jsonl > data/components/ssp1-components.json

echo "Matching components in data/ssps/ssp2.jsonl: writing data/components/ssp2-components.json"
python ssp.py --reader json-l match --components data/ssp-components.json data/ssps/ssp2.jsonl > data/components/ssp2-components.json

echo "Combining components: writing data/components/combined.json"
python combine.py data/components/ssp1-components.json data/components/ssp2-components.json > data/components/combined.json

echo "Generating OSCAL component-definition: writing data/components/oscal.json"
python oscalize.py --title 'SSP Toolkit Components (subset)' data/components/combined.json > data/components/oscal.json

echo "Generating a markdown summmary"
python component_report.py data/components/combined.json data/components/markdown
