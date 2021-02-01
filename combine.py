import json
from collections import defaultdict

import click


def combine(component_files):
    ssps = [json.load(component_file) for component_file in component_files]
    combined = {"metadata": list(), "components": defaultdict(dict)}

    for ssp in ssps:
        combined["metadata"].append(ssp["metadata"])

        catalog = ssp["metadata"]["catalog"]
        source = ssp["metadata"]["source"]

        for component in ssp["components"]:
            combined_component = combined["components"][component]
            if catalog not in combined_component:
                combined_component[catalog] = defaultdict(list)
            for statement in ssp["components"][component]:
                control = statement["control"]
                text = statement["text"]
                item = {"source": source, "text": text}
                combined_component[catalog][control].append(item)

    return combined


@click.command()
@click.argument("component_file", type=click.File("r"), nargs=-1)
def main(component_file):
    """
    Combine component files produced from multiple SSPs into a single
    object.
    """

    print(json.dumps(combine(component_file), indent=2))


if __name__ == "__main__":
    main()
