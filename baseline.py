import json
import re
from collections import ChainMap
from itertools import product
from string import Template

import click


class BaselineStatement(object):
    # placeholder pattern, like ${name}
    PATTERN = re.compile(r"\${(\w+)}")

    def __init__(self, statement):
        self.statement = statement
        self.component_category = set()

        words = statement.split()
        for word in words:
            match = re.match(self.PATTERN, word)
            if match:
                self.component_category.add(match.group(1))

    def render(self, component_assignments):
        return Template(self.statement).safe_substitute(**component_assignments)

    def generate_case(self, component_assignments, entity_label):
        rendered = self.render(component_assignments)

        # for each substituted value in the rendered text, add an entity record
        entities = []
        for value in component_assignments.values():
            index = rendered.find(value)
            while index >= 0:
                entity = [index, index + len(value), entity_label]
                entities.append(entity)
                index = rendered.find(value, index + len(value))

        return [rendered, dict(entities=entities)]


class Baseline(object):
    def __init__(self, baseline_file, entity_label):
        baseline = json.load(baseline_file)
        self.components = baseline["components"]
        self.statements = [
            BaselineStatement(statement) for statement in baseline["statements"]
        ]
        self.entity_label = entity_label

    def components_for_statement(self, statement):
        """
        Returns a list of dictionaries containing all possible category =>
        value assignments for statement.
        """

        categories = list(statement.component_category)
        category_values = []
        for category in categories:
            values = [{category: value} for value in self.components[category]]
            category_values.append(values)
        return product(*category_values)

    def generate(self):
        cases = []
        for statement in self.statements:
            for component_tuples in self.components_for_statement(statement):
                component_assignments = dict(ChainMap(*component_tuples))
                case = statement.generate_case(component_assignments, self.entity_label)
                cases.append(case)
        return cases


@click.command()
@click.option("--entity-label", default="S-Component")
@click.argument("baseline_file", type=click.File("r"))
def main(baseline_file, entity_label):
    baseline = Baseline(baseline_file, entity_label)
    cases = baseline.generate()
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
