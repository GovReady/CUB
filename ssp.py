import csv
import re
import sys
from collections import defaultdict
from collections import namedtuple
from datetime import datetime
from datetime import timezone
from typing import List
from typing import Optional
from typing import Set

import click
import simplejson as json  # we're using simplejson so we can serialize namedtuples
import spacy  # type: ignore
from spacy.pipeline import EntityRuler


def control_id(control: str) -> str:
    # return a valid control identifier from a field
    # take everything up to the first bit of whitespace
    # and remove any wrapping brackets

    control_id = r"[\w\.\-\\(\)]+"
    pattern = re.compile(r"\[?(" + control_id + r")")
    match = pattern.match(control.strip())
    if match:
        return match.group(1).strip()
    else:
        return control.strip()


ControlStatement = namedtuple("ControlStatement", ["control", "text"])


class ControlStatementReader(object):
    def __init__(self, f, encoding, verbose=False):
        self.f = f
        self.encoding = encoding
        self.verbose = verbose

    def read(self) -> List[ControlStatement]:
        with open(self.f, "r", encoding=self.encoding) as stream:
            return self._read(stream)

    def _read(self, stream) -> List[ControlStatement]:
        return []


class JSONLControlStatementReader(ControlStatementReader):
    def __init__(
        self,
        f,
        encoding,
        verbose=False,
        control_id_col=0,  # not used
        statement_col=1,  # not used
        skip_lines=0,
    ):
        super().__init__(f, encoding, verbose)
        self.skip_lines = skip_lines

    def _read(self, stream) -> List[ControlStatement]:
        statements = []
        for count in range(self.skip_lines):
            next(stream)
        for line in stream:
            objects = json.loads(line)
            statements.append(ControlStatement(objects["control"], objects["text"]))
        return statements


class CSVControlStatementReader(ControlStatementReader):

    DELIMITER = ","

    def __init__(
        self,
        f,
        encoding,
        verbose=False,
        control_id_col=0,
        statement_col=1,
        skip_lines=0,
    ):
        super().__init__(f, encoding, verbose)
        self.control_id_col = control_id_col
        self.statement_col = statement_col
        self.skip_lines = skip_lines

    def _read(self, stream) -> List[ControlStatement]:
        reader = csv.reader(stream, delimiter=self.DELIMITER)
        for count in range(self.skip_lines):
            next(reader)
        statements = []
        for row in reader:
            statement = self._statement(row)
            if statement:
                statements.append(statement)
        return statements

    def _statement(self, row) -> Optional[ControlStatement]:
        control = control_id(row[self.control_id_col])
        text = row[self.statement_col].strip()
        return ControlStatement(control, text)


class PSVControlStatementReader(CSVControlStatementReader):

    """
    Reads a Pipe Separated Value file where the control id is in the first column
    and the text is in the second column.  But sometimes the pipe is missing, in
    which case we split the line at the first bit of whitespace.
    """

    DELIMITER = "|"

    def _statement(self, row) -> Optional[ControlStatement]:
        if len(row) == 0:
            return None
        elif len(row) == 1:
            # sometimes we are missing a "|"
            pattern = re.compile(r"(\S+)\s+(.*)")
            match = pattern.match(row[self.control_id_col])
            if match:
                control = control_id(match.group(1))
                text = match.group(2).strip()
                return ControlStatement(control, text)
            else:
                return None
        else:
            control = control_id(row[self.control_id_col])
            text = row[self.statement_col].strip()
            return ControlStatement(control, text)


READERS = {
    "csv": CSVControlStatementReader,
    "psv": PSVControlStatementReader,
    "json-l": JSONLControlStatementReader,
}

CATALOGS = ["NIST_SP-800-53_rev4", "NIST_SP-800-53_rev5", "NIST_SP-800-171_rev1"]


class AllComponentsFilter(object):
    """
    Simple filter that turns a list of component names into a set.
    """

    def filter(self, components) -> Set[str]:
        return set(components)


class ComponentFilter(object):
    """
    Given a known components specification, filter and regularize
    component names.
    """

    def __init__(self, known_components_stream):
        if known_components_stream:
            self._init_from(json.load(known_components_stream))
        else:
            self._init_from({"components": {}, "not_components": []})

    def _init_from(self, known_components):
        self.not_components = known_components.get("not_components", [])
        self.canonical_names = {}
        for component_name, body in known_components.get("components", {}).items():
            self.canonical_names[component_name.casefold()] = component_name
            for aka in body.get("aka", []):
                self.canonical_names[aka.casefold()] = component_name

    def filter(self, components) -> Set[str]:
        # keep terms that might be components
        components = set(
            component for component in components if self.maybe_component(component)
        )
        # canonicalize
        components = set(self.canonical_name(component) for component in components)
        return components

    def maybe_component(self, component) -> bool:
        return not any(
            component.casefold() == nc.casefold() for nc in self.not_components
        )

    def canonical_name(self, component) -> str:
        return self.canonical_names.get(component.casefold(), component)


@click.group()
@click.option(
    "--reader", type=click.Choice(READERS.keys(), case_sensitive=False), default="psv"
)
@click.option("--control-id-col", type=int, default=0)
@click.option("--statement-col", type=int, default=1)
@click.option("--skip-lines", type=int, default=0)
@click.option("--encoding", default="utf-8", help="Set input character encoding")
@click.option("--verbose", is_flag=True, default=False)
@click.pass_context
def cli(ctx, reader, encoding, verbose, control_id_col, statement_col, skip_lines):
    """
    Parse and process a machine-readable SSP from FILENAME.

    Processing options are:
        - convert structured SSP data from one format to another
        - recognize likely component entities based on a trained model
        - match components by a rule-based pattern matcher
    """

    ctx.ensure_object(dict)
    ctx.obj["control_reader"] = READERS[reader]
    ctx.obj["control_reader_args"] = dict(
        control_id_col=control_id_col,
        statement_col=statement_col,
        skip_lines=skip_lines,
    )
    ctx.obj["encoding"] = encoding
    ctx.obj["verbose"] = verbose


def write_psv_statement(statement: ControlStatement):
    # we don't want newlines in this format
    print(statement.control, "|", statement.text.replace("\n", " ").strip())

def write_csv_statement(statement: ControlStatement):
    writer = csv.writer(sys.stdout)
    writer.writerow([statement.control, statement.text])

def write_jsonl_statement(statement: ControlStatement):
    print(json.dumps(dict(control=statement.control, text=statement.text)))


@cli.command()
@click.option("--format", type=click.Choice(["csv", "psv", "json-l"]), default="psv")
@click.argument("filename", type=click.Path(exists=True), required=True)
@click.pass_context
def convert(ctx, filename, format):
    writers = {
        'csv': write_csv_statement,
        'psv': write_psv_statement,
        'json-l': write_jsonl_statement
    }

    writer = writers[format]
    statements = read_statements(ctx, filename)
    for statement in statements:
        writer(statement)


@cli.command()
@click.option(
    "--model",
    default="en_core_web_sm",
    help="Name of model to use for component entity recognition",
)
@click.option(
    "--components",
    type=click.File("r"),
    required=False,
    help="Name of JSON file containing component tailoring",
)
@click.option(
    "--component-entity-label",
    default="S-Component",
    help="NER label for components (default 'S-Component')",
)
@click.option(
    "--catalog",
    type=click.Choice(CATALOGS),
    default=CATALOGS[0],
    help=f"Control catalog (default {CATALOGS[0]})",
)
@click.option("--remarks", help="Optional remarks to include in component output")
@click.argument("filename", type=click.Path(exists=True), required=True)
@click.pass_context
def recognize(
    ctx, filename, model, components, component_entity_label, catalog, remarks
):
    verbose = ctx.obj["verbose"]
    component_filter = ComponentFilter(components)
    nlp = spacy.load(model)
    statements = read_statements(ctx, filename)
    statements_by_component = collate_statements(
        nlp, statements, component_filter, component_entity_label, verbose
    )

    write_recognition(
        make_metadata(filename, catalog, remarks), statements_by_component
    )


def make_metadata(source, catalog, remarks):
    return {
        "source": source,
        "catalog": catalog,
        "remarks": remarks or "",
        "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "command": " ".join(sys.argv),
    }


def write_recognition(metadata, statements_by_component):
    output_object = {"metadata": metadata, "components": statements_by_component}
    print(json.dumps(output_object, indent=2))


def read_statements(ctx, filename) -> List[ControlStatement]:
    control_reader = ctx.obj["control_reader"]
    encoding = ctx.obj["encoding"]
    verbose = ctx.obj["verbose"]
    control_reader_args = ctx.obj["control_reader_args"]

    return control_reader(filename, encoding, verbose, **control_reader_args).read()


def process_statement(nlp, statement, component_entity_label, verbose) -> Set[str]:
    control = statement.control
    txt = statement.text
    doc = nlp(txt)

    nouns = set()
    for token in doc:
        if token.tag_ in ("NN", "NNP", "NNPS", "NNS"):
            nouns.add(token.text)

    if verbose:
        print("control", control)
        print("  text:", txt)
        print("  nouns:", list(nouns))
        for chunk in doc.noun_chunks:
            print("  chunk", chunk.text, chunk.root.text)
        for ent in doc.ents:
            print("  entity", ent.text, ent.label_)
        for sent in doc.sents:
            print("  sentence", sent.text)

    def _ent_name(e):
        return e.ent_id_ or e.text

    return set(
        _ent_name(ent) for ent in doc.ents if ent.label_ == component_entity_label
    )


def collate_statements(
    nlp, statements, component_filter, component_entity_label, verbose
):
    statements_by_component = defaultdict(list)
    for statement in statements:
        components = process_statement(
            nlp, statement, component_entity_label, verbose=verbose
        )
        components = component_filter.filter(components)
        if components:
            for component in components:
                statements_by_component[component].append(statement)
        else:
            statements_by_component["UNKNOWN"].append(statement)

    return statements_by_component


class PatternBuilder:
    def __init__(self, components, component_entity_label):
        self.components = components["components"]
        self.entity_label = component_entity_label
        
    def patterns(self):
        pattern_list = []
        for component, body in self.components.items():
            pattern_id = component
            pattern = {"label": self.entity_label, "pattern": component, "id": pattern_id}
            pattern_list.append(pattern)
            for aka in body.get("aka", []):
                pattern = {"label": self.entity_label, "pattern": aka, "id": pattern_id}
                pattern_list.append(pattern)
        return pattern_list


@cli.command()
@click.option(
    "--components",
    type=click.File("r"),
    required=True,
    help="Name of JSON file containing known components",
)
@click.option(
    "--model",
    default="en_core_web_sm",
    help="Name of model to use for component entity recognition",
)
@click.option(
    "--component-entity-label",
    default="S-Component",
    help="NER label for components (default 'S-Component')",
)
@click.option(
    "--catalog",
    type=click.Choice(CATALOGS),
    default=CATALOGS[0],
    help=f"Control catalog (default {CATALOGS[0]})",
)
@click.option("--remarks", help="Optional remarks to include in component output")
@click.argument("filename", type=click.Path(exists=True), required=True)
@click.pass_context
def match(ctx, filename, model, components, component_entity_label, catalog, remarks):
    verbose = ctx.obj["verbose"]
    nlp = spacy.load(model)
    ruler = EntityRuler(nlp)
    ruler.add_patterns(PatternBuilder(json.load(components), component_entity_label).patterns())
    nlp.add_pipe(ruler, before="ner")

    statements = read_statements(ctx, filename)

    # we're relying on the entity pattern match to take care of
    # making component names canonical, so just pass a filter
    # that does minimal processing

    statements_by_component = collate_statements(
        nlp, statements, AllComponentsFilter(), component_entity_label, verbose
    )

    write_recognition(
        make_metadata(filename, catalog, remarks), statements_by_component
    )


if __name__ == "__main__":
    cli()
