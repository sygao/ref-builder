from pydantic import (
    UUID4,
    BaseModel,
    Field,
    field_serializer,
    field_validator,
)

from ref_builder.models import Molecule
from ref_builder.plan import Plan
from ref_builder.utils import Accession, IsolateName


class SequenceModel(BaseModel):
    """The basic model of a sequence in the OTU."""

    id: UUID4
    """The sequence id."""

    accession: Accession
    """The sequence accession."""

    definition: str
    """The sequence definition."""

    legacy_id: str | None
    """A string based ID carried over from a legacy Virtool reference repository.

    It the sequence was not migrated from a legacy repository, this will be `None`.
    """

    sequence: str = Field(pattern=r"^[ATCGRYKMSWBDHVN]+$")
    """The sequence."""

    segment: str
    """The sequence segment."""

    @field_serializer("accession")
    @classmethod
    def serialize_accession(self, accession: Accession) -> str:
        """Serialize the accession to a string."""
        return str(accession)

    @field_validator("accession", mode="before")
    @classmethod
    def convert_accession(cls, value: Accession | str) -> Accession:
        """Convert the accession to an Accession object."""
        if isinstance(value, Accession):
            return value

        if isinstance(value, str):
            return Accession.from_string(value)

        raise ValueError(f"Invalid type for accession: {type(value)}")


class IsolateModel(BaseModel):
    """Models the basic structure of an isolate in an OTU, sans sequences."""

    id: UUID4
    """The isolate id."""

    legacy_id: str | None
    """A string based ID carried over from a legacy Virtool reference repository.

    It the isolate was not migrated from a legacy repository, this will be `None`.
    """

    name: IsolateName | None
    """The isolate's source name metadata."""

    @field_serializer("name")
    def serialize_name(self, name: IsolateName | None) -> dict[str, str] | None:
        """Serialize the isolate name."""
        if name is None:
            return None

        return {
            "type": name.type,
            "value": name.value,
        }

    @field_validator("name", mode="before")
    @classmethod
    def convert_name(cls, value: dict | IsolateName | None) -> IsolateName | None:
        """Convert the name to an IsolateName object."""
        if value is None:
            return value

        if isinstance(value, IsolateName):
            return value

        if isinstance(value, dict):
            return IsolateName(**value)

        raise ValueError(f"Invalid type for name: {type(value)}")


class OTUModel(BaseModel):
    """Models the basic structure of an OTU, sans isolates."""

    id: UUID4
    """The OTU id."""

    acronym: str
    """The OTU acronym (eg. TMV for Tobacco mosaic virus)."""

    legacy_id: str | None
    """A string based ID carried over from a legacy Virtool reference repository."""

    name: str
    """The name of the OTU (eg. TMV for Tobacco mosaic virus)"""

    molecule: Molecule
    """The type of molecular information contained in this OTU."""

    plan: Plan
    """The schema of the OTU"""

    taxid: int
    """The NCBI Taxonomy id for this OTU."""
