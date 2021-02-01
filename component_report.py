import json
import textwrap
from pathlib import Path

import click
from slugify import slugify


def write_metadata(output_file, metadata_list):
    output_file.write("## Sources\n\n")
    for metadata in metadata_list:
        source = metadata["source"]
        output_file.write(f"* From: {source}\n")
        for key, value in metadata.items():
            if key != "source" and value:
                output_file.write(f"  * *{key}*: {value}\n")
        output_file.write("\n")


def write_catalog(output_file, catalog, controls):
    output_file.write(f"## Catalog: {catalog}\n\n")
    for control_key in sorted(controls.keys()):
        output_file.write(f"### Control {control_key}\n\n")
        statements = controls[control_key]
        for statement in sorted(statements, key=lambda s: s["source"]):
            statement_source = statement["source"]
            output_file.write(f"#### {statement_source}\n\n")
            lines = textwrap.wrap(statement["text"], width=79)
            for line in lines:
                output_file.write(line + "\n")
            output_file.write("\n")


def write_component(output_dir, component, metadata, contents):
    component_file = Path(output_dir) / Path(slugify(component)).with_suffix(".md")
    with open(component_file, "w") as output_file:
        output_file.write(f"# {component}\n\n")
        for catalog in sorted(contents):
            catalog_controls = contents[catalog]
            write_catalog(output_file, catalog, catalog_controls)
        write_metadata(output_file, metadata)


@click.command()
@click.argument("input", type=click.File("r"), required=True)
@click.argument(
    "output_dir", type=click.Path(dir_okay=True, writable=True), required=True
)
def main(input, output_dir):
    """
    Read a combined component JSON specification from INPUT, and
    create a markdown file per component in the directory OUTPUT_DIR
    """

    component_collection = json.load(input)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    metadata = component_collection["metadata"]
    for component, contents in component_collection["components"].items():
        write_component(output_dir, component, metadata, contents)


if __name__ == "__main__":
    main()
