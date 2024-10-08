import subprocess
from pathlib import Path
from uuid import UUID

import pytest
from syrupy import SnapshotAssertion
from syrupy.filters import props

from ref_builder.otu.create import create_otu
from ref_builder.otu.update import (
    auto_update_otu,
    add_isolate,
    delete_isolate_from_otu,
    replace_sequence_in_otu,
    update_isolate_from_accessions,
)
from ref_builder.otu.utils import RefSeqConflictError
from ref_builder.repo import Repo
from ref_builder.resources import RepoSequence
from ref_builder.utils import IsolateName, IsolateNameType


def run_create_otu_command(
    path: Path,
    taxid: int,
    accessions: list,
    acronym: str = "",
    autofill: bool = False,
):
    autofill_option = ["--autofill"] if autofill else []

    subprocess.run(
        ["ref-builder", "otu", "create"]
        + [str(taxid)]
        + accessions
        + ["--path", str(path)]
        + ["--acronym", acronym]
        + autofill_option,
        check=False,
    )


def run_update_otu_command(taxid: int, path: Path):
    subprocess.run(
        ["ref-builder", "otu", "update"] + [str(taxid)] + ["--path", str(path)],
        check=False,
    )


class TestCreateOTU:
    def test_empty_success(
        self,
        precached_repo: Repo,
        snapshot: SnapshotAssertion,
    ):
        """Test that an OTU can be created in an empty repository."""
        otu = create_otu(
            precached_repo,
            345184,
            ["DQ178610", "DQ178611"],
            "",
        )

        assert otu.dict() == snapshot(exclude=props("id", "isolates", "repr_isolate"))

        # Ensure only one OTU is present in the repository, and it matches the return
        # value of the creation function.
        assert list(precached_repo.iter_otus()) == [otu]

    def test_empty_fail(self, scratch_repo: Repo):
        with pytest.raises(ValueError):
            create_otu(
                scratch_repo,
                345184,
                ["DQ178610", "DQ178611"],
                "",
            )

    @pytest.mark.parametrize(
        ("taxid", "accessions"),
        [(1278205, ["NC_020160"]), (345184, ["DQ178610", "DQ178611"])],
    )
    def test_otu_create(
        self,
        taxid: int,
        accessions: list[str],
        precached_repo: Repo,
    ):
        assert list(precached_repo.iter_otus()) == []

        otu = create_otu(
            precached_repo,
            taxid,
            accessions,
            "",
        )

        assert list(precached_repo.iter_otus())
        assert otu.schema is not None
        assert otu.repr_isolate is not None

    def test_otu_create_refseq_autoexclude(
        self, precached_repo: Repo, snapshot: SnapshotAssertion
    ):
        """Test that the superceded accessions included in RefSeq metadata
        are automatically added to the OTU's excluded accessions list."""
        otu = create_otu(
            precached_repo,
            3158377,
            [
                "NC_010314",
                "NC_010316",
                "NC_010315",
                "NC_010317",
                "NC_010318",
                "NC_010319",
            ], ""
        )

        assert (
            otu.excluded_accessions == {
                "EF546808",
                "EF546809",
                "EF546810",
                "EF546811",
                "EF546812",
                "EF546813",
            } == snapshot
        )

    def test_otu_create_with_acronym_auto(self, precached_repo: Repo):
        otu = create_otu(
            precached_repo,
            132477,
            ["NC_013006"],
            "",
        )

        assert otu.acronym == "KLV"

    def test_otu_create_with_acronym_manual(self, precached_repo: Repo):
        otu = create_otu(
            precached_repo,
            1441799,
            ["NC_023881"],
            "FBNSV",
        )

        assert otu.acronym == "FBNSV"


class TestCreateOTUCommands:
    @pytest.mark.parametrize(
        "taxid, accessions",
        [(1278205, ["NC_020160"]), (345184, ["DQ178610", "DQ178611"])],
    )
    def test_ok(
        self,
        taxid: int,
        accessions: list[str],
        precached_repo: Repo,
        snapshot: SnapshotAssertion,
    ):
        run_create_otu_command(
            taxid=taxid,
            path=precached_repo.path,
            accessions=accessions,
        )

        otus = list(Repo(precached_repo.path).iter_otus())

        assert len(otus) == 1
        otu = otus[0]

        assert otu.dict() == snapshot(exclude=props("id", "isolates", "repr_isolate"))

    @pytest.mark.ncbi()
    def test_autofill_ok(
        self,
        precached_repo: Repo,
        snapshot: SnapshotAssertion,
    ):
        run_create_otu_command(
            taxid=345184,
            accessions=["DQ178610", "DQ178611"],
            path=precached_repo.path,
            autofill=True,
        )

        otus = list(Repo(precached_repo.path).iter_otus())

        assert len(otus) == 1
        otu = otus[0]

        assert otu.schema.model_dump() == snapshot(exclude=props("segments"))

        for segment in otu.schema.segments:
            assert segment.model_dump() == snapshot(exclude=props("id"))

        assert {"DQ178610", "DQ178611"}.intersection(otu.accessions)

    def test_add_acronym_ok(self, precached_repo: Repo):
        """Test if the --acronym option works as planned."""
        run_create_otu_command(
            taxid=345184,
            accessions=["DQ178610", "DQ178611"],
            path=precached_repo.path,
            acronym="CabLCJV",
            autofill=True,
        )

        otus = list(Repo(precached_repo.path).iter_otus())

        assert len(otus) == 1
        otu = otus[0]

        assert otu.acronym == "CabLCJV"


class TestAddIsolate:
    def test_ok(self, precached_repo: Repo):
        isolate_1_accessions = ["DQ178610", "DQ178611"]
        isolate_2_accessions = ["DQ178613", "DQ178614"]

        otu = create_otu(precached_repo, 345184, isolate_1_accessions, acronym="")

        assert otu.accessions == set(isolate_1_accessions)

        isolate = add_isolate(precached_repo, otu, isolate_2_accessions)

        otu = precached_repo.get_otu_by_taxid(345184)

        assert otu.accessions == set(isolate_1_accessions).union(set(isolate_2_accessions))

        assert otu.get_isolate(isolate.id).accessions == set(isolate_2_accessions)

    def test_ignore_name_ok(self, precached_repo: Repo):
        """Test that ignore_name flag works as planned."""
        isolate_1_accessions = ["DQ178610", "DQ178611"]
        isolate_2_accessions = ["DQ178613", "DQ178614"]

        otu = create_otu(precached_repo, 345184, isolate_1_accessions, acronym="")

        assert otu.accessions == set(isolate_1_accessions)

        isolate = add_isolate(precached_repo, otu, isolate_2_accessions, ignore_name=True)

        otu_after = precached_repo.get_otu_by_taxid(345184)

        assert otu_after.isolate_ids == {otu_after.repr_isolate, isolate.id}

        isolate_after = otu_after.get_isolate(isolate.id)

        assert isolate_after.name is None

        assert isolate_after.accessions == {"DQ178613", "DQ178614"}

    def test_ignore_name_override_ok(self, precached_repo: Repo):
        """Test that ignore_name flag works as planned."""
        isolate_1_accessions = ["DQ178610", "DQ178611"]
        isolate_2_accessions = ["DQ178613", "DQ178614"]

        otu = create_otu(precached_repo, 345184, isolate_1_accessions, acronym="")

        assert otu.accessions == set(isolate_1_accessions)

        isolate = add_isolate(
            precached_repo,
            otu,
            isolate_2_accessions,
            ignore_name=True,
            isolate_name=IsolateName(type=IsolateNameType.ISOLATE, value="dummy")
        )

        otu_after = precached_repo.get_otu_by_taxid(345184)

        assert otu_after.isolate_ids == {otu_after.repr_isolate, isolate.id}

        isolate_after = otu_after.get_isolate(isolate.id)

        assert isolate_after.name == IsolateName(type=IsolateNameType.ISOLATE, value="dummy")

        assert isolate_after.accessions == {"DQ178613", "DQ178614"}

    def test_conflict_fail(self, precached_repo: Repo):
        """Test that an isolate cannot be added to an OTU
        if both its name and its accessions are already contained."""
        taxid = 2164102
        accessions = ["MF062136", "MF062137", "MF062138"]

        otu = create_otu(
            precached_repo,
            taxid,
            accessions,
            "",
        )

        assert add_isolate(precached_repo, otu, accessions) is None


@pytest.mark.ncbi()
class TestUpdateOTU:
    def test_without_exclusions_ok(
        self,
        precached_repo: Repo,
        snapshot: SnapshotAssertion,
    ):
        otu_before = create_otu(
            precached_repo,
            2164102,
            ["MF062136", "MF062137", "MF062138"],
            "",
        )

        assert otu_before.accessions == {"MF062136", "MF062137", "MF062138"}

        auto_update_otu(precached_repo, otu_before)

        otu_after = precached_repo.get_otu(otu_before.id)

        assert otu_after.id == otu_before.id

        assert otu_after.isolate_ids.issuperset(otu_before.isolate_ids)

        assert {isolate.name: isolate.accessions for isolate in otu_after.isolates} == snapshot()

        assert otu_after.excluded_accessions == {"MF062125", "MF062126", "MF062127"}

        assert otu_after.accessions == {
            "MF062136",
            "MF062137",
            "MF062138",
            "MF062130",
            "MF062131",
            "MF062132",
            "MK936225",
            "MK936226",
            "MK936227",
            "OQ420743",
            "OQ420744",
            "OQ420745",
            "NC_055390",
            "NC_055391",
            "NC_055392",
        }

    def test_with_replacement_ok(
        self,
        precached_repo: Repo,
        snapshot: SnapshotAssertion,
    ):
        otu_before = create_otu(
            precached_repo,
            2164102,
            ["MF062125", "MF062126", "MF062127"],
            "",
        )

        assert (
            otu_before.accessions
            ==
            otu_before.get_isolate(otu_before.repr_isolate).accessions
            ==
            {"MF062125", "MF062126", "MF062127"}
        )

        auto_update_otu(precached_repo, otu_before)

        otu_after = precached_repo.get_otu(otu_before.id)

        assert otu_after.get_isolate(otu_after.repr_isolate).accessions == {
            "NC_055390",
            "NC_055391",
            "NC_055392",
        }

        assert {"MF062125", "MF062126", "MF062127"}.isdisjoint(otu_after.accessions)

        assert otu_after.repr_isolate == otu_before.repr_isolate

        assert (
            otu_after.get_isolate(otu_before.repr_isolate).accessions
            !=
            otu_before.get_isolate(otu_before.repr_isolate).accessions
        )

        assert otu_after.id == otu_before.id

        assert otu_after.isolate_ids.issuperset(otu_before.isolate_ids)

        assert otu_after.excluded_accessions == {"MF062125", "MF062126", "MF062127"}

        assert otu_after.accessions == {
            "MF062136",
            "MF062137",
            "MF062138",
            "MF062130",
            "MF062131",
            "MF062132",
            "MK936225",
            "MK936226",
            "MK936227",
            "OQ420743",
            "OQ420744",
            "OQ420745",
            "NC_055390",
            "NC_055391",
            "NC_055392",
        }


@pytest.mark.parametrize(
        "taxid, original_accessions, refseq_accessions",
        [
            (1169032, ["AB017503"], ["NC_003355"]),
            (345184, ["DQ178608", "DQ178609"], ["NC_038792", "NC_038793"])
        ]
    )
class TestReplaceIsolateSequences:
    def test_manual_replace_ok(
        self, empty_repo, taxid, original_accessions, refseq_accessions
    ):
        """Test that a requested replacement occurs as expected."""
        create_otu(
            empty_repo, taxid, accessions=original_accessions, acronym=""
        )

        otu_before = empty_repo.get_otu_by_taxid(taxid)

        assert otu_before.accessions == set(original_accessions)

        isolate = list(otu_before.isolates)[0]

        update_isolate_from_accessions(empty_repo, otu_before, isolate.name, refseq_accessions)

        otu_after = empty_repo.get_otu(otu_before.id)

        assert otu_after.accessions == set(refseq_accessions)

        assert otu_after.excluded_accessions == set(original_accessions)

    def test_raise_refseq_exception(
        self,
        empty_repo,
        taxid: int,
        original_accessions: list[str],
        refseq_accessions: list[str],
    ):
        """Test that attempting to add an isolate with RefSeq accessions
        raises RefSeqConflictError"""
        create_otu(
            empty_repo, taxid, accessions=original_accessions, acronym=""
        )

        otu_before = empty_repo.get_otu_by_taxid(taxid)

        assert otu_before.accessions == set(original_accessions)

        add_isolate(empty_repo, otu_before, original_accessions)

        with pytest.raises(RefSeqConflictError):
            add_isolate(empty_repo, otu_before, refseq_accessions)


class TestRemoveIsolate:
    def test_ok(self, scratch_repo):
        """Test that a given isolate can be removed from the OTU."""
        taxid = 1169032

        otu_before = scratch_repo.get_otu_by_taxid(taxid)

        isolate_id = otu_before.get_isolate_id_by_name(
            IsolateName(type=IsolateNameType.ISOLATE, value="WMoV-6.3")
        )

        assert type(isolate_id) is UUID

        delete_isolate_from_otu(scratch_repo, otu_before, isolate_id)

        otu_after = scratch_repo.get_otu_by_taxid(taxid)

        assert otu_after.get_isolate(isolate_id) is None

        assert otu_before.get_isolate(isolate_id).accessions not in otu_after.accessions

        assert len(otu_after.isolate_ids) == len(otu_before.isolate_ids) - 1


class TestReplaceSequence:
    def test_ok(self, precached_repo):
        """Test that a sequence in an OTU can be replaced manually."""
        otu_before = create_otu(
            precached_repo,
            1169032,
            ["MK431779"],
            acronym="",
        )

        isolate_id, old_sequence_id = otu_before.get_sequence_id_hierarchy_from_accession(
            "MK431779"
        )

        assert type(old_sequence_id) is UUID

        sequence = replace_sequence_in_otu(
            repo=precached_repo,
            otu=otu_before,
            new_accession="NC_003355",
            replaced_accession="MK431779"
        )

        assert type(sequence) is RepoSequence

        otu_after = precached_repo.get_otu_by_taxid(1169032)

        assert otu_after.accessions == {"NC_003355"}

        assert otu_after.get_isolate(isolate_id).accessions == {"NC_003355"}
