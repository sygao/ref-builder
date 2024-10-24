from uuid import uuid4
import sys

import structlog

from ref_builder.ncbi.client import NCBIClient
from ref_builder.ncbi.models import NCBIGenbank
from ref_builder.otu.utils import (
    create_isolate_plan_from_records,
    group_genbank_records_by_isolate,
    get_molecule_from_records,
    parse_refseq_comment,
)
from ref_builder.repo import Repo
from ref_builder.resources import RepoOTU, OTUMetadata

logger = structlog.get_logger("otu.create")


def create_otu(
    repo: Repo,
    taxid: int,
    accessions: list[str],
    acronym: str,
    ignore_cache: bool = False,
) -> RepoOTU | None:
    """Create a new OTU by species-level taxonomy ID and autogenerate a schema.

    Uses the provided accessions to generate a schema and add a first isolate.

    If the taxonomy ID is sub species-level, uses the species-level metadata.
    The given taxonomy ID is made subordinate.

    :param repo: the repository to add the OTU to.
    :param taxid: the taxonomy ID to use.
    :param accessions: a list of accessions to use for the schema.
    :param acronym: an alternative name to use during searches.
    :param ignore_cache: whether to ignore the cache.

    """
    otu_logger = logger.bind(taxid=taxid)

    client = NCBIClient(ignore_cache)

    if repo.get_otu_id_by_taxid(taxid):
        raise ValueError(
            f"Taxonomy ID {taxid} has already been added to this reference.",
        )

    if (taxonomy := client.fetch_taxonomy_record(taxid)) is None:
        otu_logger.fatal(f"Could not retrieve {taxid} from NCBI Taxonomy")
        return None

    if not acronym and taxonomy.other_names.acronym:
        acronym = taxonomy.other_names.acronym[0]

    records = client.fetch_genbank_records(accessions)

    if len(records) != len(accessions):
        otu_logger.fatal("Could not retrieve all requested accessions.")
        return None

    if taxonomy.species.id == taxid:
        return construct_otu(
            repo=repo,
            taxid=taxid,
            name=taxonomy.name,
            acronym=acronym,
            records=records,
            subordinates=None,
        )

    else:
        subordinates = [
            OTUMetadata(
                id=uuid4(),
                acronym=acronym,
                legacy_id=None,
                name=taxonomy.name,
                taxid=taxid,
            ),
        ]
        taxid = taxonomy.species.id
        name = taxonomy.species.name

        otu_logger = logger.bind(taxid=taxid, name=name, subordinates=subordinates)

        otu_logger.info(f"Set OTU level data to species level ({taxid})")

        return construct_otu(
            repo=repo,
            taxid=taxid,
            name=name,
            acronym=acronym,
            records=records,
            subordinates=subordinates,
        )


def construct_otu(
    repo: Repo,
    taxid: int,
    name: str,
    acronym: str,
    records: list[NCBIGenbank],
    subordinates: dict[OTUMetadata] | None = None,
):
    """Create an OTU from the given OTU metadata and records."""
    otu_logger = logger.bind(taxid=taxid, accessions=[record.accession_version for record in records])

    binned_records = group_genbank_records_by_isolate(records)

    if len(binned_records) > 1:
        otu_logger.fatal(
            "More than one isolate found. Cannot create schema automatically.",
        )
        return None

    molecule = get_molecule_from_records(records)

    plan = create_isolate_plan_from_records(records)

    if plan is None:
        otu_logger.fatal("Could not create plan from records.")
        return None

    try:
        otu = repo.create_otu(
            acronym=acronym,
            legacy_id=None,
            molecule=molecule,
            name=name,
            plan=plan,
            subordinates=subordinates,
            taxid=taxid,
        )
    except ValueError as e:
        otu_logger.fatal(e)
        sys.exit(1)

    isolate = repo.create_isolate(
        otu_id=otu.id,
        legacy_id=None,
        name=next(iter(binned_records.keys())) if binned_records else None,
    )

    otu.add_isolate(isolate)
    otu.repr_isolate = repo.set_repr_isolate(otu_id=otu.id, isolate_id=isolate.id)

    for record in records:
        sequence = repo.create_sequence(
            otu_id=otu.id,
            accession=record.accession_version,
            definition=record.definition,
            legacy_id=None,
            segment=record.source.segment,
            sequence=record.sequence,
        )

        repo.link_sequence(otu.id, isolate.id, sequence.id)

        if record.refseq:
            _, old_accession = parse_refseq_comment(record.comment)
            repo.exclude_accession(
                otu.id,
                old_accession,
            )

    return repo.get_otu(otu.id)
