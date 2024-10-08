from typing import Annotated

from pydantic import (
    UUID4,
    AliasChoices,
    BaseModel,
    Field,
    TypeAdapter,
    field_serializer,
    field_validator,
)

from ref_builder.schema import OTUSchema
from ref_builder.utils import Accession, IsolateName, IsolateNameType


class OTUSnapshotMeta(BaseModel):
    """Structures metadata about the OTU snapshot itself."""

    at_event: int | None = None
    """The event ID of the last change made to this snapshot."""


class OTUSnapshotSequence(BaseModel):
    """Stores and parses sequence data."""

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

    sequence: str
    """The sequence."""

    segment: str
    """The sequence segment."""

    @field_validator("accession", mode="before")
    @classmethod
    def convert_accession(cls, v: Accession | str) -> Accession:
        if type(v) is Accession:
            return v

        if type(v) is str:
            return Accession.from_string(v)

    @field_serializer("accession")
    def serialize_accession(self, _info) -> str:
        return str(self.accession)


class OTUSnapshotIsolate(BaseModel):
    """Stores and parses isolate data."""

    id: UUID4
    """The isolate ID."""

    name: IsolateName | None
    """The isolate's source name metadata."""

    legacy_id: str | None = None
    """A string based ID carried over from a legacy Virtool reference repository."""

    @field_validator("name", mode="before")
    @classmethod
    def convert_isolate_name(cls, raw: dict | None) -> IsolateName | None:
        """Takes a dictionary and converts to IsolateName."""
        if raw is None:
            return None
        return IsolateName(type=IsolateNameType(raw["type"]), value=raw["value"])


class OTUSnapshotOTU(BaseModel):
    """Stores and parses OTU data."""

    acronym: str = ""
    """The OTU acronym (eg. TMV for Tobacco mosaic virus)."""

    id: UUID4
    """The OTU id."""

    name: str
    """The name of the OTU (eg. TMV for Tobacco mosaic virus)."""

    taxid: int
    """The NCBI Taxonomy id for this OTU."""

    otu_schema: Annotated[
        OTUSchema,
        Field(
            validation_alias=AliasChoices("otu_schema", "schema"),
            serialization_alias="schema",
        ),
    ]
    """The OTU schema."""

    legacy_id: str | None
    """A string based ID carried over from a legacy Virtool reference repository."""

    repr_isolate: UUID4 | None = None
    """The representative isolate."""


class OTUSnapshotToCIsolate(BaseModel):
    """Stores a table of contents for an isolate."""

    id: UUID4
    """The isolate id."""

    name: IsolateName | None
    """The isolate name."""

    accessions: dict[str, UUID4]
    """A mapping of accessions to sequence ids."""


toc_adapter = TypeAdapter(dict[str, OTUSnapshotToCIsolate])
