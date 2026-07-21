"""Behavioral coverage for the owned strict FormID Value Lookup facade."""

import asyncio

import classic_database
import pytest


def test_in_memory_lookup_distinguishes_hit_miss_malformed_and_failure() -> None:
    """Owned replies cross PyO3 without callbacks or collapsed failure states."""

    async def run() -> None:
        lookup = classic_database.FormIdValueLookup.in_memory(
            [
                classic_database.FormIdValueLookupEntry(
                    "000800", "SomeMod.esp", value="Laser Musket"
                ),
                classic_database.FormIdValueLookupEntry(
                    "000801", "SomeMod.esp", value="   "
                ),
                classic_database.FormIdValueLookupEntry(
                    "000802",
                    "SomeMod.esp",
                    operational_failure="fixture offline",
                ),
            ]
        )

        hit = await lookup.lookup("000800", "SOMEMOD.ESP")
        miss = await lookup.lookup("000899", "SomeMod.esp")
        assert (hit.kind, hit.value) == ("found", "Laser Musket")
        assert (miss.kind, miss.value) == ("missing", None)

        with pytest.raises(classic_database.FormIdValueLookupError) as malformed:
            await lookup.lookup("000801", "SomeMod.esp")
        assert malformed.value.code == "malformed_result"

        with pytest.raises(classic_database.FormIdValueLookupError) as failure:
            await lookup.lookup("000802", "SomeMod.esp")
        assert failure.value.code == "operational_failure"
        assert "fixture offline" in failure.value.message

    asyncio.run(run())


def test_disabled_and_shared_pool_adapters_remain_owned() -> None:
    """Disabled and existing-pool adapters expose positional semantic outcomes."""

    async def run() -> None:
        disabled = classic_database.FormIdValueLookup.disabled()
        disabled_outcome = await disabled.lookup("000800", "SomeMod.esp")
        assert disabled_outcome.kind == "disabled"

        pool = classic_database.DatabasePool(game_table="Fallout4")
        shared = classic_database.FormIdValueLookup.from_shared_pool(pool)
        outcomes = await shared.lookup_batch(
            [("000800", "SomeMod.esp"), ("000801", "OtherMod.esp")]
        )
        assert [outcome.kind for outcome in outcomes] == ["missing", "missing"]

    asyncio.run(run())
