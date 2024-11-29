from uuid import UUID

from ref_builder.resources.models import IsolateModel
from ref_builder.resources.sequence import RepoSequence
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


class RepoIsolate(IsolateBase):
    """Represents an isolate in a Virtool reference repository."""

    sequences: list[RepoSequence]

    _sequences_by_accession: dict[str, RepoSequence] = {}
    """A dictionary of sequences indexed by accession"""

    def __init__(self, **data) -> None:
        super().__init__(**data)

        self._sequences_by_accession = {
            sequence.accession.key: sequence for sequence in self.sequences
        }

        self._sequences_by_id = {sequence.id: sequence for sequence in self.sequences}

    @property
    def accessions(self) -> set[str]:
        """A set of accession numbers for sequences in the isolate."""
        return set(self._sequences_by_accession.keys())

    @property
    def sequence_ids(self) -> set[UUID]:
        """A set of UUIDs for sequences in the isolate."""
        return {sequence.id for sequence in self.sequences}

    def add_sequence(self, sequence: RepoSequence) -> None:
        """Add a sequence to the isolate."""
        self.sequences.append(
            sequence,
        )

        self._sequences_by_accession[sequence.accession.key] = sequence
        self._sequences_by_id[sequence.id] = sequence

    def replace_sequence(
        self,
        sequence: RepoSequence,
        replaced_sequence_id: UUID,
    ) -> None:
        """Replace a sequence with the given ID with a new sequence."""
        self.add_sequence(sequence)
        self.delete_sequence(replaced_sequence_id)

        self._sequences_by_accession[sequence.accession.key] = sequence
        self._sequences_by_id[sequence.id] = sequence

        self._update_sequence_lookups()

    def delete_sequence(self, sequence_id: UUID) -> None:
        """Delete a sequence from a given isolate."""
        sequence = self.get_sequence_by_id(sequence_id)

        if not sequence:
            raise ValueError("This sequence ID does not exist")

        self._sequences_by_accession.pop(sequence.accession.key)
        self._sequences_by_id.pop(sequence_id)

        for sequence in self.sequences:
            if sequence.id == sequence_id:
                self.sequences.remove(sequence)

    def get_sequence_by_accession(
        self,
        accession: str,
    ) -> RepoSequence | None:
        """Return a sequence with the given accession if it exists in the isolate,
        else None.
        """
        return self._sequences_by_accession.get(accession)

    def get_sequence_by_id(self, sequence_id: UUID) -> RepoSequence | None:
        """Return a sequence with the given ID if it exists in the isolate,
        else None.
        """
        if sequence_id not in self.sequence_ids:
            return None

        for sequence in self.sequences:
            if sequence.id:
                return sequence

        return None
