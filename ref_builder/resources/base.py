from uuid import UUID

from pydantic import UUID4

from ref_builder.resources import IsolateModel, RepoSequence, OTUModel
from ref_builder.utils import Accession


class IsolateBase(IsolateModel):
    """A class representing an isolate with basic validation."""

    sequences: list[RepoSequence]
    """The isolates sequences."""

    def get_sequence_by_accession(
        self,
        accession: Accession,
    ) -> RepoSequence | None:
        """Get a sequence by its accession.

        Return ``None`` if the sequence is not found.

        :param accession: the accession of the sequence to retrieve
        :return: the sequence with the given accession, or None
        """
        for sequence in self.sequences:
            if sequence.accession == accession:
                return sequence

        return None

    def get_sequence_by_id(self, sequence_id: UUID) -> RepoSequence | None:
        """Get a sequence by its ID.

        Return ``None`` if the sequence is not found.

        :param sequence_id: the ID of the sequence to retrieve
        :return: the sequence with the given ID, or None
        """
        for sequence in self.sequences:
            if sequence.id == sequence_id:
                return sequence

        return None


class OTUBase(OTUModel):
    """A class representing an OTU with basic validation."""

    excluded_accessions: set[str]
    """A set of accessions that should not be retrieved in future fetch operations."""

    isolates: list[IsolateBase]
    """Isolates contained in this OTU."""

    repr_isolate: UUID4 | None
    """The UUID of the representative isolate of this OTU"""

    sequences: list[RepoSequence]
    """Sequences contained in this OTU."""
