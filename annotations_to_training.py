import json

import click


@click.command()
@click.argument("annotations_file", type=click.File("r"), required=True)
def main(annotations_file):
    """
    Convert annotations in ANNOTATIONS_FILE to training set JSON format.
    """

    annotations = json.load(annotations_file)
    training_data = []
    for data in annotations:
        ents = [tuple(entity[:3]) for entity in data["entities"]]
        training_data.append((data["content"], {"entities": ents}))
    print(json.dumps(training_data, indent=2))


if __name__ == "__main__":
    main()
