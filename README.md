# CaC (Compliance as Code) Utility Belt

"Only you can prevent copy and paste."

Collection and extension of parsers from GovReady for parsing SSPs
and control implementation statements.

## Component extraction

### Overview

- Use the tool `ssp.py` to convert existing machine
  readable SSPs into a standard format (e.g., CSV or JSON-L)
- Generate samples of the standard format SSPs using `ssp.py sample`
- Load samples into annotator and annotate.  Download and save
  annotations in JSON format.
- Convert JSON annotations into training format using
  `annotations_to_training.py`
- Train and generate a component recognition model with `train.py`
- Apply the model to SSPs using `ssp.py recognize` to recognize component
  entities and produce a candidate set of components.
- Based on the output, create a `components.json` file to fine tune
  the component identification process.  You can exclude certain
  candidates as "not a component", and define canonical names for
  other candidate components.
- Reapply the model, and refine `components.json` as needed.
- Combine the results of applying the model to muliple SSPs using
  `combine.py`
- Generate markdown for each component with `component_report.py`

There are some sample data files in the `data` directory.

The shell script `sample-pipeline.sh` demonstrates some very simple
processing using sample data.

### ssp.py (overview)

The `ssp.py` tool performs operations on machine readable SSP's.  Command line
usage looks like:

```
python ssp.py [GLOBAL OPTIONS] convert|recognize [OPTIONS] FILENAME
```

Global options apply to SSP parsing:

Use the `--reader` CLI option to specify the format to be read.

`--reader csv|psv|json-l`

- CSV format ("csv")
- PSV format ("pipe-separated values")
- JSON-L format

By default, the parser expects the control ID to be in the first
column, and the implementation statement text to be in the second
column.  You can use the `--control-id-col N` and `--statement-col N`
to choose other columns.  Column number is 0-based.

Since CSV files often contain headers, use the `--skip-lines N` option
to have the parser skip *N* lines before looking for control
statements.

Examples:

To parse a CSV file with no headers, the control ID in the first
column, and the statement text in the second column (i.e., all the
defaults):

```
python ssp.py --reader csv SSP.csv COMMAND ...
```

To parse a CSV file with one line of headers, the control ID in the
second column, and the statement text in the third column:

```
python ssp.py --reader csv --skip-lines 1 \
              --control-id-col 1 --statement-col 2 SSP.csv COMMAND ...
```

You can also parse SSP's that are stored as JSON-L files, where
each line contains a JSON object with a *control* key and a *text* key.

E.g.,

```
{"control": "1.1", "text": "Employee accounts are managed with Active Directory."}
{"control": "1.2", "text": "Passwords must be greater than 8 characters."}
```

If you run into a file created on Windows, you may wish to use the global
option `--encoding cp1252` option to the command line to deal with the
Windows character set.

### ssp.py (for conversion)

`ssp.py convert` is used to parse existing machine readable SSP
documents and convert them into other formats.  The default format is
the simple "Pipe Separated Value" (PSV) format that works well with
the annotator.  Use the `--format json-l` to convert to a JSON-L
format.

```
python ssp.py --reader csv convert SSP1.csv > SSP1.txt
```

or

```
python ssp.py --reader csv convert --format json-l SSP1.csv > SSP1.jsonl
```

### ssp.py (for sampling)

To produce a subset of SSP statements from an SSP file, use the `ssp.py sample` command:

```
python ssp.py sample sample --number 10 SSP1.csv > SSP1-sample.txt
```

The above will generate a 10 line sample from `SSP1.txt` and store in
`SSP1-sample.txt`.

### Annotator

```
git clone https://github.com/ManivannanMurugavel/spacy-ner-annotator.git
```

and then use a browser to open `index.html` in the newly created directory.

"Upload" a sampled SSP PSV file and annotate component terms in
the control text with the class *S-Component*

### annotations_to_training.py

_Remind:_ could teach the trainer to read annotation files directly, but for now...

The annotator generates JSON files that need to be converted to
another JSON representation for consumption as a training set by the
component recognizer trainer.

```
# python annotations_to_training.py SSP1-annotations.json > SSP1-training.json
```

### train.py

Given one or more training sets, use `train.py` to train a custom
component recognizer. The following command will create a new model
`components-model` that recognizes components:

```
python train.py --output-model components-model SSP1-training.json SSP2-training.json
```

### ssp.py (for component recognition)

To apply a custom component recognizer to a machine readable SSP, use
the `ssp.py recognize` command:

```
python ssp.py --reader csv recognize --model components-model  SSP1.csv
```

The output is a JSON document that describes the candidate components
and associated control statements.

The recognizer adds some metadata to the component output, including
a control set catalog identifier.  The default is *NIST_SP-800-53_rev4*, but
you can override this with the `--catalog CATALOG`` option.  Valid choices are:

- NIST_SP-800-53_rev4
- NIST_SP-800-53_rev5
- NIST_SP-800-171_rev1

### components.json

You can supply a components.json file to `ssp.py recognize
--components FILE` to filter and refine how components are identified.

1. You can exclude certain candidate components from consideration by
   adding them to the `not_components` list.

1. You can define a canonical name for a component and list synonyms
   by adding entries to the `components` map.

Example:

```
{
    "components": {
        "Active Directory": {
            "aka": [
                "Microsoft Active Directory",
                "AD",
                "Microsoft AD"
             ]
        }
    },
    "not_components": [
        "Business Impact"
    ]
}
```

The above specification will tell `ssp.py` to not consider
"Business Impact" as a component, and to define a canonical name for
"Active Directory" with three synonyms.

```
python ssp.py --reader csv recognize --model components-model \
    --components components.json SSP1.csv
```

### ssp.py (experimental component pattern matching)

Rather than using the trained component entity recognizer model, `ssp.py` offers
a second option to recognize components using a pattern matcher.  Using the same
format `components.json` file mentioned in the previous section, define all the
components and "also known as" names you would like to find in SSPs.  Then, use
the `ssp.py match` command:

```
python ssp.py --reader csv match --components components.json SSP1.csv
```

### combine.py

`combine.py` takes the component output from runs of `ssp.py
recognize` against multiple SSPs and produces a single representation
of all control statements associated with recognized components across
the SSPs.

```
python combine.py SSP1.json SSP2.json SSP3.json > combined.json
```

### component_report.py

`component_report.py` takes the output of `combine.py` and creates a
Markdown file per component in an output directory.

```
python component_report.py combined.json output-dir
```

### oscalize.py

Given a JSON combined component file produced by `combine.py`, `oscal.py` generates
a JSON OSCAL component file on stdout.

```
python oscalize.py --title "My Title" combined.json > oscal-components.json
```

Example with this repo's test data:

```
python oscalize.py --title "Microsoft Active Directory"  \
    data/test_data/test_combined_microsoft_active_directory.json \
    > data/test_data/test_microsoft-active-directory-oscal.json
```

Use the `--component COMPONENT` option to select a single component from
the combined JSON file.  You can repeat this option to select additional
components.

```
python oscalize.py --title "My Firewall Component" --component Firewall \
    combined.json > firewall-component.json
```

Use the `--component-list-file FILE` option to select components whose
names are listed in `FILE`, one component per line.

Use the `--batch-output DIRECTORY` and `--batch-size N` (defaults to 10) options
to write out component definitions in batches to JSON files in `DIRECTORY`.

```
mkdir batched-components
python oscal.py --title "My Components" --batch-output batched-components combined.json
```

### selector.py (experimental)

Given a JSON combined component file produced by `combine.py` and a
control selector specification file, `selector.py` produces a new JSON
file collated by the control sets specified in the specification file.
It can optionally write markdown files for each control set.

A selector specification file is a JSON file that looks like:

```
{
    "selectors": {
        "firewall": {
            "NIST_SP-800-53_rev4": [
                "AC-1", "AC-2", "IA-1"
            ],
            "NIST_SP-800-171_rev1": [
                "1.1.2", "3.5.5"
            ]
        },
        "directory-service": {
            "NIST_SP-800-53_rev4": [
                "AC-1", "AC-2", "IA-1", "IA-2", "IA-3"
            ],
            "NIST_SP-800-171_rev1": [
                "1.2.1", "2.2.1", 3.5.5"
            ]
        }
    }
}
```

```
python selector.py spec.json combined.json --markdown output_dir
```

### baseline.py (experimental)

`baseline.py` generates a training JSON file based on a set of
"sample" statements with placeholders and a collection of
representative values for each placeholder.  Hypothesis is that we can
teach the component entity recognizer to do a better job of
recognizing names we *know* to be components.

Each statement should contain one or more placeholder that
matches a component category.

```
python baseline.py baseline.json > baseline-training.json
```

Where `baseline.json` might look like:

```
{
    "components": {
        "firewall": [
            "Cisco Firewall",
            "Netgear Firewall",
            "F5 Application Firewall"
        ],
        "antivirus": [
            "McAfee Antivirus",
            "Malware Bytes"
        ],
        "directory-service": [
            "LDAP",
            "Microsoft Active Directory"
        ]
    },
    "statements": [
        "The network is protected by ${firewall}.",
        "User workstations must have the ${antivirus} system installed.",
        "User accounts are managed with ${directory-service}."
    ]
}

```

## similar.py (experimental)

`similar.py` does word vector comparisons between the control
statements in multiple SSPs, and attempts to find clusters of similar
statements.

SSP statements are expected to be in JSON-L format with the usual
`control` and `text` slots.

Specify each SSP with a `--ssp TAG FILE` option.  The `TAG` will be
used to identify the SSP in the output.

```
python similar.py \
    --ssp SSP1 ssp1.jsonl --ssp SSP2 ssp2.jsonl --ssp SSP3 ssp3.jsonl
```

By default, `similar.py` will compare the entire control statements.  With
the `--by sentence` option, you can perform pairwise comparison of sentences
in each statement.

```
python similar.py --by sentence \
    --ssp SSP1 ssp1.jsonl --ssp SSP2 ssp2.jsonl --ssp SSP3 ssp3.jsonl
```

Use the `--threshold FLOAT` option to adjust the threshold where
statements/sentences are considered similar.  The default value is
0.95.

## Dev notes

See [pre-commit](https://pre-commit.com/#install) for instructions on
installing pre-commit.  After installation, install pre-commit hooks
for this repo in your local checkout:

```
pre-commit install
```

Install dependencies via *poetry*, or read `requirements.in`

```
poetry install
```

Load some required spacy models.  Most tools use *en_core_web_sm*.  The
*similar.py* tool needs *en_core_web_lg*.

```
python -m spacy download en_core_web_sm
```

Run tests with pytest:

```
pytest
```

## License

GNU General Public License v3.0 or later.

Sample data files were based on content from the [CivicActions SSP
Toolkit](https://github.com/CivicActions/ssp-toolkit).

SPDX-License-Identifier: `GPL-3.0-or-later`
