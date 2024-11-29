import datetime
from uuid import UUID

from pydantic import BaseModel, UUID4, Field

from ref_builder.resources.models import IsolateModel, OTUModel, SequenceModel
from ref_builder.utils import DataType, IsolateName


class RepoMeta(BaseModel):
    """Represents the metadata for a Virtool reference repository."""

    id: UUID4
    """The repository id."""

    created_at: datetime.datetime
    """The date and time the repository was created."""

    data_type: DataType
    """The repository data type."""

    name: str
    """The repository name."""

    organism: str
    """The repository organism."""


class RepoSettings(BaseModel):
    """The default settings of a Virtool reference repository."""

    default_segment_length_tolerance: float = Field(0.03, ge=0.0, le=1.0)
    """The deviation a sequence is allowed from its plan segment's length before it fails validation."""


class RepoSequence(SequenceModel):
    """Represents a sequence in a Virtool reference repository."""


class RepoIsolate(IsolateModel):
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


class RepoOTU(OTUModel):
    """Represents an OTU in a Virtool reference repository."""

    excluded_accessions: set[str]
    """A set of accessions that should not be retrieved in future fetch operations."""

    representative_isolate: UUID4 | None
    """The UUID of the representative isolate for the OTU."""

    isolates: list[RepoIsolate]
    """Isolates contained in this OTU."""

    _isolates_by_id: dict[UUID4:RepoIsolate]
    """A dictionary of isolates indexed by isolate UUID"""

    _sequences_by_id: dict[UUID4:RepoSequence]
    """A dictionary of sequences indexed by sequence UUID"""

    def __init__(self, **data) -> None:
        super().__init__(**data)

        self._sequences_by_id = {}
        self._isolates_by_id = {}
        for isolate in self.isolates:
            self._isolates_by_id[isolate.id] = isolate
            for sequence in isolate.sequences:
                self._sequences_by_id[sequence.id] = sequence

    @property
    def accessions(self) -> set[str]:
        """A set of accessions contained in this isolate."""
        return {sequence.accession.key for sequence in self._sequences_by_id.values()}

    @property
    def blocked_accessions(self) -> set[str]:
        """Accessions that should not be considered for addition to the OTU.

        This includes accessions that already exist in the OTU and accessions that have
        been explicitly excluded.
        """
        return self.accessions | self.excluded_accessions

    @property
    def isolate_ids(self) -> set[UUID4]:
        """A set of UUIDs for isolates in the OTU."""
        return set(self._isolates_by_id.keys())

    def add_isolate(self, isolate: RepoIsolate) -> None:
        """Add an isolate to the OTU."""
        self.isolates.append(isolate)
        self._isolates_by_id[isolate.id] = isolate

    def add_sequence(self, sequence: RepoSequence) -> None:
        """Add a sequence to a given isolate."""
        self._sequences_by_id[sequence.id] = sequence

    def get_sequence_by_id(self, sequence_id: UUID) -> RepoSequence | None:
        return self._sequences_by_id.get(sequence_id)

    def delete_isolate(self, isolate_id: UUID4) -> None:
        """Remove an isolate from the OTU."""
        self._isolates_by_id.pop(isolate_id)

        for isolate in self.isolates:
            if isolate.id == isolate_id:
                for sequence in isolate.sequences:
                    self._sequences_by_id.pop(sequence.id)

                self.isolates.remove(isolate)
                break

    def delete_sequence(self, sequence_id: UUID4) -> None:
        """Delete a sequence from a given isolate. Used only during rehydration."""
        self._sequences_by_id.pop(sequence_id)

    def get_isolate(self, isolate_id: UUID4) -> RepoIsolate | None:
        """Get isolate associated with a given ID.

        Returns None if no such isolate exists.

        :param isolate_id: The UUID of the isolate to retrieve
        :return: the isolate or ``None``
        """
        return self._isolates_by_id.get(isolate_id)

    def get_isolate_id_by_name(self, name: IsolateName) -> UUID4 | None:
        """Get the ID for the isolate with the passed ``name``.

        Returns None if no such isolate exists.

        :param name: The name of the isolate to retrieve
        :return: The isolate ID or ``None``

        """
        for isolate in self.isolates:
            if isolate.name == name:
                return isolate.id

        return None

    def get_sequence_by_accession(
        self,
        accession: str,
    ) -> RepoSequence | None:
        """Return a sequence corresponding to given accession
        if it exists in this OTU.
        """
        if accession not in self.accessions:
            return None

        for isolate in self.isolates:
            if (sequence := isolate.get_sequence_by_accession(accession)) is not None:
                return sequence

        raise ValueError(f"Accession {accession} found in index, but not in data")

    def get_sequence_id_hierarchy_from_accession(
        self,
        accession: str,
    ) -> tuple[UUID4, UUID4] | tuple[None, None]:
        """Return the isolate ID and sequence ID of a given accession."""
        if accession not in self.accessions:
            return None, None

        for isolate in self.isolates:
            if (sequence := isolate.get_sequence_by_accession(accession)) is not None:
                return isolate.id, sequence.id

        raise ValueError(f"Accession {accession} found in index, but not in data")

    def link_sequence(
        self, isolate_id: UUID4, sequence_id: UUID4
    ) -> RepoSequence | None:
        """Link the given sequence to the given isolate."""
        self.get_isolate(isolate_id).add_sequence(self.get_sequence_by_id(sequence_id))

        return self.get_isolate(isolate_id).get_sequence_by_id(sequence_id)

    def unlink_sequence(self, isolate_id: UUID4, sequence_id: UUID4) -> None:
        """Unlink the given sequence from the given isolate. Used only during rehydration."""
        self.get_isolate(isolate_id).delete_sequence(sequence_id)

    def replace_sequence(
        self,
        sequence: RepoSequence,
        isolate_id: UUID4,
        replaced_sequence_id: UUID4,
    ) -> None:
        """Replace a sequence with the given ID with a new sequence."""
        self.get_isolate(isolate_id).replace_sequence(sequence, replaced_sequence_id)
