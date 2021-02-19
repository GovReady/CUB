#
# This is a toy example of a prefect.io pipeline for
# processsing SSPs using
#
import tempfile
from pathlib import Path

import click
from prefect import Flow
from prefect import Parameter
from prefect import task
from prefect.tasks.shell import ShellTask
from prefect.utilities.edges import unmapped


@task
def discover_ssps(src_dir):
    ssps = Path(src_dir).glob("*.jsonl")
    return list(ssps)


@task
def match_ssp(ssp, component_spec):
    command = "python ssp.py --reader json-l match --components {} {}".format(
        component_spec, ssp
    )
    output = ShellTask(command=command, return_all=True).run()
    return "\n".join(output)


@task
def combine(components):
    paths = []
    for component in components:
        component_file = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        )
        component_file.write(component)
        paths.append(component_file.name)
        component_file.close()

    paths_arg = " ".join(paths)
    command = "python ssp.py combine {}".format(paths_arg)
    return "\n".join(ShellTask(command=command, return_all=True).run())


@task
def oscalize(combined, title):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as combined_file:
        combined_file.write(combined)
        command = "python oscalize.py --title {} {}".format(title, combined_file.name)
        return "\n".join(ShellTask(command=command, return_all=True).run())


@task
def markdown(combined, dest_dir):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as combined_file:
        combined_file.write(combined)
        command = "python component_report.py {} {}".format(
            combined_file.name, Path(dest_dir) / "markdown"
        )
        return "\n".join(ShellTask(command=command, return_all=True).run())


@task
def write_file(s, path):
    with Path(path).open("w") as f:
        f.write(s)


@click.command()
@click.option("--title", default="Components")
@click.argument(
    "component_spec_file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.argument(
    "src_dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    required=True,
)
@click.argument(
    "dest_dir",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
)
def main(component_spec_file, src_dir, dest_dir, title):
    """
    Runs a parameterized pipeline that processes all the SSP's in the
    SRC_DIR and places output files in the DEST_DIR.  The COMPONENT_SPEC_FILE
    is supplied to the *match* phase.
    """

    with Flow("SSP Pipeline") as flow:
        src = Parameter("src")
        dest = Parameter("dest")
        component_spec = Parameter("component_spec")
        ssps = discover_ssps(src)
        components = match_ssp.map(ssps, unmapped(component_spec))
        combined = combine(components)
        oscal = oscalize(combined, title)
        write_file(oscal, Path(dest_dir) / "oscal.json")
        markdown(combined, dest)

    flow.run(component_spec=component_spec_file, src=src_dir, dest=dest_dir)


if __name__ == "__main__":
    main()
