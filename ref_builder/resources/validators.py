from collections import Counter
from uuid import UUID

from pydantic import UUID4, Field, model_validator

from ref_builder.resources import RepoIsolate, RepoSequence
from ref_builder.resources.base import IsolateBase, OTUBase


class Isolate(IsolateBase):
    """A class representing an isolate with full validation."""

    sequences: list[RepoSequence] = Field(min_length=1)
    """The isolates sequences.

    A valid isolate must have at least one sequence.
    """


class OTU(OTUBase):
    """A class representing an OTU with full validation."""

    isolates: list[RepoIsolate] = Field(min_length=1)
    """Isolates contained in this OTU.

    A valid OTU must have at least one isolate.
    """

    representative_isolate: UUID4
    """The UUID of the representative isolate of this OTU.

    A valid OTU must have a representative isolate.
    """

    @model_validator(mode="after")
    def check_excluded_accessions(self) -> "OTU":
        """Ensure that excluded accessions are not in the OTU."""
        if accessions := self.excluded_accessions & {
            sequence.accession.key for sequence in self.sequences
        }:
            raise ValueError(
                f"Excluded accessions found in the OTU: {', '.join(accessions)}"
            )

        return self

    @model_validator(mode="after")
    def check_representative_isolate(self) -> "OTU":
        """Ensure that the default isolate is in the OTU."""
        if self.representative_isolate not in {isolate.id for isolate in self.isolates}:
            raise ValueError("Representative isolate must be in the OTU")

        return self

    @model_validator(mode="after")
    def check_unique_isolate_names(self) -> "OTU":
        """Ensure there are no duplicate isolate names in the OTU."""
        counts = Counter(isolate.name for isolate in self.isolates)

        duplicates = ", ".join(
            [str(name) for name, count in counts.items() if name and count > 1]
        )

        if duplicates:
            raise ValueError(
                f"Isolate names must be unique. Non-unique names: {duplicates}",
            )

        return self

    @model_validator(mode="after")
    def check_isolates_against_plan(self) -> "OTU":
        """Check that all isolates satisfy the OTU's plan.

        TODO: Implement this method.
        """
        return self
