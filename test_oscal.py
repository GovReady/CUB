import json
from datetime import datetime
from datetime import timezone

import jsonschema
import pytest

from oscal import Component
from oscal import ComponentDefinition
from oscal import control_to_statement_id
from oscal import ControlImplementation
from oscal import Email
from oscal import ImplementedRequirement
from oscal import Link
from oscal import LinkRelEnum
from oscal import Metadata
from oscal import oscalize_control_id
from oscal import Party
from oscal import PartyTypeEnum
from oscal import Revision
from oscal import Root
from oscal import Statement


class TestValidOSCAL:
    def setup(self):
        with open("oscal_component_schema.json", "r") as f:
            self.schema = json.load(f)

    @classmethod
    def component(cls, name):
        return Component(
            name=f"{name} component",
            title=f"title of {name} component",
            description=f"description of {name} component",
        )

    def is_valid(self, oscal):
        try:
            obj = json.loads(oscal)
            jsonschema.validate(instance=obj, schema=self.schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            print("EXCEPTION", str(e))
            return False
        return False

    def test_empty(self):
        metadata = Metadata(title="Testing", version="1.0")
        component_def = ComponentDefinition(metadata=metadata)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_parties(self):
        parties = [
            Party(type=PartyTypeEnum.person, name="Harry Potter"),
            Party(
                type=PartyTypeEnum.organization,
                name="Hogwarts School of Magic",
                short_name="Hogwarts",
                email_addresses=[Email("harry.potter@hogwarts.edu")],
            ),
        ]
        metadata = Metadata(title="Testing", version="1.0", parties=parties)
        component_def = ComponentDefinition(metadata=metadata)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_revision_history(self):
        # oddly, spec says empty revisions are OK
        revisions = [
            Revision(title="Revision 2", published=datetime.now(timezone.utc)),
            Revision(
                title="Revision 1",
                published=datetime.now(timezone.utc),
                version="1.2.3",
            ),
            Revision(),
        ]
        metadata = Metadata(title="Testing", version="1.0", revisions=revisions)
        component_def = ComponentDefinition(metadata=metadata)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_links(self):
        links = [
            Link(text="Google", href="https://google.com"),
            Link(text="Picture", href="#photo_1", rel=LinkRelEnum.photograph),
        ]
        metadata = Metadata(title="Testing", version="1.0", links=links)
        component_def = ComponentDefinition(metadata=metadata)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_empty_component(self):
        metadata = Metadata(title="Testing", version="1.0")
        component_def = ComponentDefinition(metadata=metadata)
        component = self.component("test")
        component_def.add_component(component)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_one_component(self):
        metadata = Metadata(title="Testing", version="1.0")
        component_def = ComponentDefinition(metadata=metadata)
        component = self.component("test")
        impl = ControlImplementation(source="NIST 800-53rev4", description="Testing")
        req = ImplementedRequirement(control_id="AC-1", description="About AC-1")
        req.add_statement(
            Statement(statement_id="1", description="First statement about AC-1")
        )
        req.add_statement(
            Statement(statement_id="2", description="Second statement about AC-1")
        )
        impl.implemented_requirements.append(req)
        component.control_implementations.append(impl)
        component_def.add_component(component)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_multiple_components(self):
        metadata = Metadata(title="Testing", version="1.0")
        component_def = ComponentDefinition(metadata=metadata)
        for name in ["component 1", "component 2", "component 3"]:
            component = self.component(name)
            impl = ControlImplementation(
                source="NIST 800-53rev4", description=f"800-53 controls for {name}"
            )
            for control in ["AC-1", "AC-2(1)", "RA-1.b", "PE-2(1).a"]:
                req = ImplementedRequirement(
                    control_id=control,
                    description=f"About {control} in component {name}",
                )
                req.add_statement(
                    Statement(
                        statement_id="S1", description=f"Statement 1 about {control}"
                    )
                )
                req.add_statement(
                    Statement(
                        statement_id="S2", description=f"Statement 2 about {control}"
                    )
                )
                impl.implemented_requirements.append(req)
            component.control_implementations.append(impl)
            component_def.add_component(component)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)

    def test_multiple_components_multiple_implementations(self):
        metadata = Metadata(title="Testing", version="1.0")
        component_def = ComponentDefinition(metadata=metadata)
        for name in ["component 1", "component 2", "component 3"]:
            component = self.component(name)
            for source in ["NIST 800-53rev4", "NIST 800-171rev1"]:
                impl = ControlImplementation(
                    source=source, description=f"{source} controls for {name}"
                )
                for control in ["AC-1", "AC-2(1)", "RA-1.b", "PE-2(1).a"]:
                    req = ImplementedRequirement(
                        control_id=control,
                        description=f"About {control} in component {name}",
                    )
                    req.add_statement(
                        Statement(
                            statement_id="S1",
                            description=f"Statement 1 about {control}",
                        )
                    )
                    req.add_statement(
                        Statement(
                            statement_id="S2",
                            description=f"Statement 2 about {control}",
                        )
                    )
                    impl.implemented_requirements.append(req)
                component.control_implementations.append(impl)
            component_def.add_component(component)
        root = Root(component_definition=component_def)
        oscal = root.json(indent=2)
        assert self.is_valid(oscal)


class TestExceptions:
    def test_statement_already_exists(self):
        impl_req = ImplementedRequirement(control_id="AC-1", description="AC-1")
        statement_1 = Statement(statement_id="S-1", description="Description of S-1")
        statement_2 = Statement(statement_id="S-1", description="Duplicate!")
        impl_req.add_statement(statement_1)

        with pytest.raises(KeyError):
            impl_req.add_statement(statement_2)

    def test_component_already_exists(self):
        component_def = ComponentDefinition(
            metadata=Metadata(title="CD", version="1.0")
        )
        component_1 = Component(name="C1", description="C1", title="C1")
        component_2 = Component(
            name="C2", description="C2", title="C2", uuid=component_1.uuid
        )
        component_def.add_component(component_1)
        with pytest.raises(KeyError):
            component_def.add_component(component_2)


class TestControlID:
    @pytest.mark.parametrize(
        "control,expected",
        (
            ("ac-1", "ac-1"),
            ("AC-1", "ac-1"),
            ("AC-01", "ac-1"),
            ("AC-1(2)", "ac-1.2"),
            ("AC-1 (2)", "ac-1.2"),
            ("AC-01(2)", "ac-1.2"),
            ("AC-01 (2)", "ac-1.2"),
            ("AC-2.a", "ac-2"),
            ("AC-02.a", "ac-2"),
            ("AC-1(2).b", "ac-1.2"),
            ("AC-01(2).b", "ac-1.2"),
            ("3.2.1", "3.2.1"),
        ),
    )
    def test_oscalize_control_id(self, control, expected):
        assert oscalize_control_id(control) == expected, control


class TestStatementID:
    @pytest.mark.parametrize(
        "control,expected",
        (
            ("ac-1", "ac-1_smt"),
            ("AC-1", "ac-1_smt"),
            ("AC-01", "ac-1_smt"),
            ("AC-1(2)", "ac-1.2_smt"),
            ("AC-01(2)", "ac-1.2_smt"),
            ("AC-1 (2)", "ac-1.2_smt"),
            ("AC-01 (2)", "ac-1.2_smt"),
            ("AC-1.a", "ac-1_smt.a"),
            ("AC-01.a", "ac-1_smt.a"),
            ("AC-1(2).b", "ac-1.2_smt.b"),
            ("AC-01(2).b", "ac-1.2_smt.b"),
            ("AC-1 (2).b", "ac-1.2_smt.b"),
            ("AC-01 (2).b", "ac-1.2_smt.b"),
            ("3.2", "3.2_smt"),
            ("3.1.1", "3.1.1_smt"),
            ("3.2.3.4", "3.2.3.4_smt"),
        ),
    )
    def test_control_to_statement_id(self, control, expected):
        assert control_to_statement_id(control) == expected, control
