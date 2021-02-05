import json
import tempfile
from io import StringIO

import pytest

from ssp import AllComponentsFilter
from ssp import ComponentFilter
from ssp import control_id
from ssp import CSVControlStatementReader
from ssp import PatternBuilder
from ssp import PSVControlStatementReader


class TestControlID(object):
    @pytest.mark.parametrize(
        "control,expected",
        (
            ("", ""),
            ("1.2.3", "1.2.3"),
            ("AC-3", "AC-3"),
            ("AC-3(a)", "AC-3(a)"),
            ("1.2.3 foo", "1.2.3"),
            ("AC-3 foo", "AC-3"),
            ("[AC-3]", "AC-3"),
            ("[AC-3 foo", "AC-3"),
        ),
    )
    def test_control_id(self, control, expected):
        assert control_id(control) == expected


class TestAllComponentFilter(object):

    test_filter = AllComponentsFilter()

    def test_all(self):
        assert self.test_filter.filter(set(("A",))) == set(("A",))
        assert self.test_filter.filter(set(("A", "B", "C"))) == set(("A", "B", "C"))
        assert self.test_filter.filter(set()) == set()


class TestPatternBuilder(object):
    def test_empty(self):
        components = {"components": {}}
        patterns = PatternBuilder(components, "S-Component").patterns()
        assert patterns == []

    def test_component(self):
        components = {"components": {"Component A": {}}}
        patterns = PatternBuilder(components, "S-Component").patterns()
        assert patterns == [
            {"label": "S-Component", "pattern": "Component A", "id": "Component A"}
        ]

    def test_component_with_aka(self):
        components = {"components": {"Component A": {"aka": ["Comp-A", "Comp A"]}}}
        patterns = PatternBuilder(components, "S-Component").patterns()
        assert len(patterns) == 3
        assert {
            "label": "S-Component",
            "pattern": "Component A",
            "id": "Component A",
        } in patterns
        assert {
            "label": "S-Component",
            "pattern": "Comp-A",
            "id": "Component A",
        } in patterns
        assert {
            "label": "S-Component",
            "pattern": "Comp A",
            "id": "Component A",
        } in patterns


class TestComponentFilter(object):
    @staticmethod
    def filter_from_objects(objects):
        string = json.dumps(objects)
        stream = StringIO(string)
        return ComponentFilter(stream)

    def test_empty(self):
        filter = self.filter_from_objects({})
        assert filter.filter(set(("A", "B", "C"))) == set(("A", "B", "C"))

    def test_not_components(self):
        filter = self.filter_from_objects(dict(not_components=["A"]))
        assert filter.filter(set(("A", "B"))) == set(("B"))

    def test_known_components(self):
        filter = self.filter_from_objects(dict(components=dict(A={})))
        assert filter.filter(set(("A", "B"))) == set(("A", "B"))
        assert filter.filter(set(("a", "B"))) == set(("A", "B"))

    def test_aka_component(self):
        filter = self.filter_from_objects(
            dict(components=dict(A=dict(aka=["component A"])))
        )
        test_data = (
            (set(("A", "B")), set(("A", "B"))),
            (set(("a", "B")), set(("A", "B"))),
            (set(("component A", "B")), set(("A", "B"))),
            (set(("Component A", "B")), set(("A", "B"))),
            (set(("Component C", "B")), set(("B", "Component C"))),
        )

        for args, expected in test_data:
            assert filter.filter(args) == expected

    def test_multiple_aka_components(self):
        components = {
            "A": {"aka": ["Microsoft A"]},
            "B": {"aka": ["Cisco B", "Cisco B System"]},
        }

        filter = self.filter_from_objects(dict(components=components))

        test_data = (
            (set(("A", "B")), set(("A", "B"))),
            (set(("a", "B")), set(("A", "B"))),
            (set(("Microsoft A", "Cisco B")), set(("A", "B"))),
            (set(("microsoft a", "B")), set(("A", "B"))),
            (set(("microsoft a", "cisco b", "Jira")), set(("A", "B", "Jira"))),
        )

        for args, expected in test_data:
            assert filter.filter(args) == expected

    def test_soup_to_nuts(self):
        components = {
            "A": {"aka": ["Microsoft A"]},
            "B": {"aka": ["Cisco B", "Cisco B System"]},
        }
        not_components = ["Chicken"]

        filter = self.filter_from_objects(
            dict(components=components, not_components=not_components)
        )

        test_data = (
            (set(("A", "B")), set(("A", "B"))),
            (set(("a", "B")), set(("A", "B"))),
            (set(("Microsoft A", "Cisco B")), set(("A", "B"))),
            (set(("microsoft a", "B")), set(("A", "B"))),
            (set(("microsoft a", "cisco b", "Jira")), set(("A", "B", "Jira"))),
            (set(("A", "B", "Chicken")), set(("A", "B"))),
            (set(("A", "B", "Component C", "chicken")), set(("A", "B", "Component C"))),
        )

        for args, expected in test_data:
            assert filter.filter(args) == expected


class TestCSVControlStatementReader(object):
    def test_reader(self):
        text = """\
AC-1, Statement for AC-1
IA-4, Statement for IA-4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as fp:
            fp.write(text)
            fp.close()
            reader = CSVControlStatementReader(fp.name, "utf-8")
            statements = reader.read()

        assert len(statements) == 2
        assert statements[0].control == "AC-1"
        assert statements[0].text == "Statement for AC-1"
        assert statements[1].control == "IA-4"
        assert statements[1].text == "Statement for IA-4"


class TestPSVControlStatementReader(object):
    def test_reader(self):
        text = """
AC-1 | Statement for AC-1
IA-4 | Statement for IA-4
RA-3 extra text | Statement for RA-3
[RA-4] | Statement for RA-4
"""

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as fp:
            fp.write(text)
            fp.close()
            reader = PSVControlStatementReader(fp.name, "utf-8")
            statements = reader.read()

        assert len(statements) == 4
        assert statements[0].control == "AC-1"
        assert statements[0].text == "Statement for AC-1"
        assert statements[1].control == "IA-4"
        assert statements[1].text == "Statement for IA-4"
        assert statements[2].control == "RA-3"
        assert statements[2].text == "Statement for RA-3"
        assert statements[3].control == "RA-4"
        assert statements[3].text == "Statement for RA-4"


class TestPSV2ControlStatementReader(object):
    def test_reader(self):
        text = """
Access Control | AC-1 | Statement for AC-1
Identity |IA-4 | Statement for IA-4
Risk | RA-3 extra text | Statement for RA-3
Risk | [RA-4] | Statement for RA-4
"""

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as fp:
            fp.write(text)
            fp.close()
            reader = PSVControlStatementReader(
                fp.name, "utf-8", control_id_col=1, statement_col=2
            )
            statements = reader.read()

        assert len(statements) == 4
        assert statements[0].control == "AC-1"
        assert statements[0].text == "Statement for AC-1"
        assert statements[1].control == "IA-4"
        assert statements[1].text == "Statement for IA-4"
        assert statements[2].control == "RA-3"
        assert statements[2].text == "Statement for RA-3"
        assert statements[3].control == "RA-4"
        assert statements[3].text == "Statement for RA-4"
