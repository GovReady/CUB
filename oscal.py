#
# helpers for constructing OSCAL component structures and
# serializing as JSON
#
# requires pydantic
import re
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field

OSCAL_VERSION = "1.0.0-rc1"


class ControlRegExps:
    nist_800_171 = re.compile(r"^\d+\.\d+(\.\d+)*$")
    nist_800_53_simple = re.compile(r"^([a-z]{2})-(\d+)$")
    nist_800_53_extended = re.compile(r"^([a-z]{2})-(\d+)\s*\((\d+)\)$")
    nist_800_53_part = re.compile(r"^([a-z]{2})-(\d+)\.([a-z]+)$")
    nist_800_53_extended_part = re.compile(r"^([a-z]{2})-(\d+)\s*\((\d+)\)\.([a-z]+)$")


def oscalize_control_id(control_id):
    """
    output an oscal standard control id from various common formats for control ids
    """

    control_id = control_id.strip()
    control_id = control_id.lower()

    # 1.2, 1.2.3, 1.2.3.4, etc.
    if re.match(ControlRegExps.nist_800_171, control_id):
        return control_id

    # AC-1
    match = re.match(ControlRegExps.nist_800_53_simple, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        return f"{family}-{number}"

    # AC-2(1)
    match = re.match(ControlRegExps.nist_800_53_extended, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        extension = int(match.group(3))
        return f"{family}-{number}.{extension}"

    # AC-1.a
    match = re.match(ControlRegExps.nist_800_53_part, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        return f"{family}-{number}"

    # AC-2(1).b
    match = re.match(ControlRegExps.nist_800_53_extended_part, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        extension = int(match.group(3))
        return f"{family}-{number}.{extension}"

    return control_id


def control_to_statement_id(control_id):
    """
    Construct an OSCAL style statement ID from a control identifier.
    """

    control_id = control_id.strip()
    control_id = control_id.lower()

    # 1.2, 1.2.3, 1.2.3.4, etc.
    if re.match(ControlRegExps.nist_800_171, control_id):
        return f"{control_id}_smt"

    # AC-1
    match = re.match(ControlRegExps.nist_800_53_simple, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        return f"{family}-{number}_smt"

    # AC-2(1)
    match = re.match(ControlRegExps.nist_800_53_extended, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        extension = int(match.group(3))
        return f"{family}-{number}.{extension}_smt"

    # AC-1.a
    match = re.match(ControlRegExps.nist_800_53_part, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        part = match.group(3)
        return f"{family}-{number}_smt.{part}"

    # AC-2(1).b
    match = re.match(ControlRegExps.nist_800_53_extended_part, control_id)
    if match:
        family = match.group(1)
        number = int(match.group(2))
        extension = int(match.group(3))
        part = match.group(4)
        return f"{family}-{number}.{extension}_smt.{part}"

    # nothing matched ...
    return f"{control_id}_smt"


class NCName(str):
    pass


class OSCALElement(BaseModel):
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        if hasattr(self.Config, "container_assigned"):
            for key in self.Config.container_assigned:
                if key in d:
                    del d[key]
        if hasattr(self.Config, "exclude_if_false"):
            for key in self.Config.exclude_if_false:
                if not d.get(key, False):
                    del d[key]
        return d


class Property(OSCALElement):
    name: str
    value: str
    uuid: UUID = Field(default_factory=uuid4)


class Email(str):
    pass


class Revision(OSCALElement):
    title: Optional[str]
    published: Optional[datetime]
    last_modified: Optional[datetime]
    version: Optional[str]
    oscal_version: Optional[str]
    props: Optional[List[Property]]

    class Config:
        fields = {"last_modified": "last-modified", "oscal_version": "oscal-version"}
        allow_population_by_field_name = True


class PartyTypeEnum(str, Enum):
    person = "person"
    organization = "organization"


class Party(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    type: PartyTypeEnum
    name: str
    short_name: Optional[str]
    props: Optional[List[Property]]
    email_addresses: Optional[List[Email]]

    class Config:
        fields = {
            "short_name": "short-name",
            "email_addresses": "email-addresses",
        }
        allow_population_by_field_name = True


class LinkRelEnum(str, Enum):
    homepage = "homepage"
    interview_notes = "interview-notes"
    tool_output = "tool-output"
    photograph = "photograph"
    questionaire = "questionaire"
    screen_shot = "screen-shot"


class Link(OSCALElement):
    text: str
    href: str
    rel: Optional[LinkRelEnum]


class Metadata(OSCALElement):
    title: str
    version: str
    oscal_version: str = OSCAL_VERSION
    published: datetime = datetime.now(timezone.utc)
    last_modified: datetime = datetime.now(timezone.utc)
    props: Optional[List[Property]]
    parties: Optional[List[Party]]
    links: Optional[List[Link]]
    revisions: Optional[List[Revision]]

    class Config:
        fields = {
            "oscal_version": "oscal-version",
            "last_modified": "last-modified",
            "revision_history": "revision-history",
        }
        allow_population_by_field_name = True


class ComponentTypeEnum(str, Enum):
    software = "software"
    hardware = "hardware"
    service = "service"
    interconnection = "interconnection"
    policy = "policy"
    process = "process"
    procedure = "procedure"
    plan = "plan"
    guidance = "guidance"
    standard = "standard"
    validation = "validation"


class Statement(OSCALElement):
    statement_id: Optional[NCName]
    uuid: UUID = Field(default_factory=uuid4)
    description: str = ""
    props: Optional[List[Property]]
    remarks: Optional[str]
    links: Optional[List[Link]]

    class Config:
        container_assigned = ["statement_id"]


class ImplementedRequirement(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    control_id: str
    description: str
    statements: Dict[NCName, Statement] = {}
    remarks: Optional[str]
    props: Optional[List[Property]]

    def add_statement(self, statement: Statement):
        key = statement.statement_id
        if key in self.statements:
            raise KeyError(
                f"Statement {key} already in ImplementedRequirement"
                " for {self.control_id}"
            )
        self.statements[NCName(statement.statement_id)] = statement
        return self

    class Config:
        fields = {"control_id": "control-id"}
        allow_population_by_field_name = True
        exclude_if_false = ["statements"]


class ControlImplementation(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    description: str
    source: str
    props: Optional[List[Property]]
    implemented_requirements: List[ImplementedRequirement] = []
    links: Optional[List[Link]]

    class Config:
        fields = {"implemented_requirements": "implemented-requirements"}
        allow_population_by_field_name = True


class Component(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    title: str
    type: ComponentTypeEnum = ComponentTypeEnum.software
    description: str
    props: Optional[List[Property]]
    control_implementations: List[ControlImplementation] = []
    links: Optional[List[Link]]

    class Config:
        fields = {
            "control_implementations": "control-implementations",
        }
        allow_population_by_field_name = True
        container_assigned = ["uuid"]
        exclude_if_false = ["control-implementations"]


class ComponentDefinition(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    metadata: Metadata
    components: Dict[str, Component] = {}

    def add_component(self, component: Component):
        key = str(component.uuid)
        if key in self.components:
            raise KeyError(f"Component {key} already in ComponentDefinition")
        self.components[str(component.uuid)] = component
        return self

    class Config:
        exclude_if_false = ["components"]


class Root(OSCALElement):
    component_definition: ComponentDefinition

    class Config:
        fields = {"component_definition": "component-definition"}
        allow_population_by_field_name = True

    def json(self, **kwargs):
        if "by_alias" in kwargs:
            kwargs.pop("by_alias")
        if "exclude_none" in kwargs:
            kwargs.pop("exclude_none")

        return super().json(by_alias=True, exclude_none=True, **kwargs)
