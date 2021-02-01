import json
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Dict

import click
from slugify import slugify


def summarize(selected: Dict, spec: Dict):
    for selector_name in sorted(selected):
        for catalog_name in sorted(selected[selector_name]):
            matches = sorted(selected[selector_name][catalog_name].keys())
            match_str = ", ".join(f"+{match}" for match in matches)

            missing = set(spec["selectors"][selector_name][catalog_name]) - set(matches)
            missing_str = ", ".join(f"-{missed}" for missed in sorted(missing))

            print(
                "{:30} {} | {}".format(
                    f"{selector_name}/{catalog_name}", match_str, missing_str
                )
            )


def select_controls(select_controls, controls) -> Dict[str, dict]:
    select_controls_set = set(select_controls)
    controls_set = set(controls)
    return {key: controls[key] for key in select_controls_set & controls_set}


def _match(item, item_filter) -> bool:
    if item_filter is None:
        return True
    else:
        return item == item_filter


def do_select(spec, components, catalog_filter, selector_filter) -> Dict:
    results: Dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for component_name, catalogs in components["components"].items():
        for catalog_name, controls in catalogs.items():
            if _match(catalog_name, catalog_filter):
                for selector_name, selector_catalogs in spec["selectors"].items():
                    if _match(selector_name, selector_filter):
                        for (
                            selector_catalog_name,
                            controls_spec,
                        ) in selector_catalogs.items():
                            if selector_catalog_name == catalog_name:
                                matches = select_controls(controls_spec, controls)
                                for match_name, statement in matches.items():
                                    desc = dict(
                                        component=component_name,
                                        statements=statement,
                                    )
                                    results[selector_name][catalog_name][
                                        match_name
                                    ].append(desc)
    return results


def write_component(markdown_file, component, statements):
    markdown_file.write(f"#### Component {component}\n\n")
    for statement in statements:
        markdown_file.write("*From {}*\n\n".format(statement["source"]))
        lines = textwrap.wrap(statement["text"], width=79)
        for line in lines:
            markdown_file.write(line + "\n")
        markdown_file.write("\n")


def write_control(markdown_file, control, components):
    markdown_file.write(f"### {control}\n\n")
    for component in sorted(components, key=lambda item: item["component"]):
        write_component(markdown_file, component["component"], component["statements"])


def write_catalog(markdown_file, catalog, controls):
    markdown_file.write(f"## Catalog {catalog}\n\n")
    for control, components in sorted(controls.items(), key=lambda item: item[0]):
        write_control(markdown_file, control, components)


def write_selector(markdown_file, selector, catalogs):
    markdown_file.write(f"# Selector {selector}\n\n")
    for catalog, controls in sorted(catalogs.items(), key=lambda item: item[0]):
        write_catalog(markdown_file, catalog, controls)


def report(selected: Dict, markdown_dir: str):
    for selector, catalogs in selected.items():
        markdown_path = Path(markdown_dir) / Path(slugify(selector)).with_suffix(".md")
        with open(markdown_path, "w") as markdown_file:
            write_selector(markdown_file, selector, catalogs)


@click.command()
@click.argument("spec", type=click.File("r"), required=True)
@click.argument("components", type=click.File("r"), required=True)
@click.option("--catalog", help="Output only statements from this catalog")
@click.option(
    "--selector", help="Output only statements with controls from this selector"
)
@click.option("--summary", is_flag=True, help="Summarize controls found")
@click.option(
    "--markdown",
    type=click.Path(dir_okay=True, writable=True),
    help="Write markdown reports in this directory",
)
def main(spec, components, summary, catalog, selector, markdown):
    """
    Given a "combined" JSON file COMPONENTS containing
    component-collated implementation statements, re-collate based on
    controls specified by a selector configuration file SPEC.  By
    default writes JSON output to stdout.
    """
    spec_json = json.load(spec)
    components_json = json.load(components)
    selected = do_select(spec_json, components_json, catalog, selector)
    if summary:
        summarize(selected, spec_json)
    elif markdown:
        report(selected, markdown)
    else:
        print(json.dumps(selected, indent=2))


if __name__ == "__main__":
    main()
