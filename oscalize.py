import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Dict

import click

from oscal import Component
from oscal import ComponentDefinition
from oscal import control_to_statement_id
from oscal import ControlImplementation
from oscal import ImplementedRequirement
from oscal import Metadata
from oscal import oscalize_control_id
from oscal import Property
from oscal import Revision
from oscal import Root
from oscal import Statement


def oscalify(components: Dict, title: str):
    now = datetime.now(timezone.utc)
    revision = Revision(title="Initial revision", published=now)
    metadata = Metadata(
        title=title,
        version="1.0",
        published=now,
        last_modified=now,
        properties=[Property(name="generated-by", value="oscal.py")],
        revision_history=[revision],
    )
    component_def = ComponentDefinition(metadata=metadata)
    for component_name, catalogs in components["components"].items():
        component = Component(
            name=component_name, title=component_name, description=component_name
        )
        component_def.add_component(component)
        for catalog_name, controls in catalogs.items():
            control_implementation = ControlImplementation(
                source=catalog_name, description=catalog_name
            )
            component.control_implementations.append(control_implementation)
            for control_key, control_descs in controls.items():
                descriptions = []
                ssp_sources = []

                for control_desc in control_descs:
                    descriptions.append(control_desc["text"])
                    ssp_sources.append(control_desc["source"])

                description = "\n\n".join(descriptions)
                remarks = "From: " + ", ".join(ssp_sources)

                control_id = oscalize_control_id(control_key)

                implemented_requirement = ImplementedRequirement(
                    control_id=control_id, description=description, remarks=remarks
                )

                control_implementation.implemented_requirements.append(
                    implemented_requirement
                )

                statement_id = control_to_statement_id(control_key)
                statement = Statement(
                    statement_id=statement_id, description=description
                )
                implemented_requirement.add_statement(statement)

    return Root(component_definition=component_def)


def do_stdout(title, combined, selected_components):
    if selected_components:
        our_components = {c: combined["components"][c] for c in selected_components}
        metadata = combined["metadata"]
        combined = {"metadata": metadata, "components": our_components}

    oscal = oscalify(combined, title)
    print(oscal.json(indent=2))


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def do_batch(title, combined, selected_components, batch_output, batch_size):
    metadata = combined["metadata"]

    # if no components selected, default to all

    if not selected_components:
        selected_components = combined["components"].keys()

    selected_components = sorted(list(selected_components))
    for batch_no, components in enumerate(chunks(selected_components, batch_size)):
        our_components = {c: combined["components"][c] for c in components}
        combined_batch = {"metadata": metadata, "components": our_components}
        batch_title = f"{title}: {batch_no}"
        oscal = oscalify(combined_batch, batch_title)
        batch_file = Path(batch_output) / f"COMPONENTS-BATCH-{batch_no}.json"
        with batch_file.open(mode="w") as f:
            f.write(oscal.json(indent=2))


@click.command()
@click.option("--title", required=True)
@click.option(
    "--component", help="Only produce OSCAL for this component", multiple=True
)
@click.option("--component-list-file", type=click.File("r"))
@click.option("--batch-size", type=int, default=10)
@click.option(
    "--batch-output",
    type=click.Path(dir_okay=True),
    help="Directory to place batch output",
)
@click.argument("input", type=click.File("r"), required=True)
def main(input, title, component, component_list_file, batch_output, batch_size):
    """
    Generates an OSCAL JSON component definition set from the JSON produced by
    combine.py.
    """

    combined = json.load(input)

    # take any components specified on the command line via `--component`, and
    # add any component names from `--component-list-file`
    # if neither of these mechanisms are used, we will default to
    # using all components found in the combined JSON.

    selected_components = set(component)
    if component_list_file:
        for name in component_list_file.readlines():
            selected_components.add(name.strip())

    if batch_output:
        do_batch(title, combined, selected_components, batch_output, batch_size)
    else:
        do_stdout(title, combined, selected_components)


if __name__ == "__main__":
    main()
