from typing import cast

import yaml

from snuba.clusters.storage_sets import StorageSetKey
from snuba.datasets.configuration.utils import parse_columns
from snuba.migrations.columns import MigrationModifiers
from snuba.migrations.operations import AddColumn, DropColumn, OperationTarget
from snuba.utils.schemas import Column, ColumnType, SchemaModifiers

"""
This file is for autogenerating the migration for adding a column to your storage.
"""


def is_valid_add_column(oldstorage: str, newstorage: str) -> tuple[bool, str]:
    """
    Input:
        old_storage, the old storage yaml in str format
        new_storage, the modified storage yaml in str format

    Returns true if the changes to the storage is valid column addition, false otherwise,
    along with a reasoning.
    """
    oldstorage_dict = yaml.safe_load(oldstorage)
    newstorage_dict = yaml.safe_load(newstorage)
    if oldstorage_dict == newstorage_dict:
        return True, "storages are the same"

    # nothing changed but the columns
    t1 = oldstorage_dict["schema"].pop("columns")
    t2 = newstorage_dict["schema"].pop("columns")
    if not (oldstorage_dict == newstorage_dict):
        return (
            False,
            "Expected the only change to the storage to be the columns, but that is not true",
        )
    oldstorage_dict["schema"]["columns"] = t1
    newstorage_dict["schema"]["columns"] = t2

    # only changes to columns is additions
    oldstorage_cols = oldstorage_dict["schema"]["columns"]
    newstorage_cols = newstorage_dict["schema"]["columns"]

    colnames_old = set(e["name"] for e in oldstorage_cols)
    colnames_new = set(e["name"] for e in newstorage_cols)
    if not colnames_old.issubset(colnames_new):
        return (False, "Column removal is not supported")

    pold, pnew = 0, 0
    while pold < len(oldstorage_cols) and pnew < len(newstorage_cols):
        curr_old = oldstorage_cols[pold]
        curr_new = newstorage_cols[pnew]

        if curr_old == curr_new:
            pold += 1
            pnew += 1
        elif curr_new["name"] in colnames_old:
            return (
                False,
                f"Modification to columns in unsupported, column '{curr_new['name']}' was modified or reordered",
            )
        else:
            if pold == 0:
                return (
                    False,
                    "Adding a column to the beginning is currently unsupported, please add it anywhere else.",
                )
            else:
                pnew += 1
    assert pold == len(oldstorage_cols)  # should always hold
    return True, ""


def _schema_column_to_migration_column(
    column: Column[SchemaModifiers],
) -> Column[MigrationModifiers]:
    """
    Given SchemaModifiers returns equivalent MigrationModifiers.
    Only nullable is supported, throws error if conversion cant be made.
    """
    newtype = cast(ColumnType[MigrationModifiers], column.type.get_raw())
    mods = column.type.get_modifiers()
    if not mods:
        return Column(column.name, newtype)

    # convert schema modifiers to migration modifiers
    if mods.readonly:
        raise ValueError("readonly modifier is not supported")
    newtype = newtype.set_modifiers(MigrationModifiers(nullable=mods.nullable))
    return Column(column.name, newtype)


def generate_migration_ops(
    oldstorage: str, newstorage: str
) -> tuple[list[AddColumn], list[DropColumn]]:
    """
    Input:
        old_storage, the old storage yaml in str format
        new_storage, the modified storage yaml in str format

    Returns a tuple (forwardops, backwardsops) this are the forward and backward migration
    operations required to migrate the storage as described in the given yaml files.

    Only supports adding columns, throws error for anything else.
    """
    valid, reason = is_valid_add_column(oldstorage, newstorage)
    if not valid:
        raise ValueError(reason)

    oldcol_names = set(
        col["name"] for col in yaml.safe_load(oldstorage)["schema"]["columns"]
    )
    newstorage_dict = yaml.safe_load(newstorage)
    newcols = newstorage_dict["schema"]["columns"]

    forwardops: list[AddColumn] = []
    for i, col in enumerate(newcols):
        if col["name"] not in oldcol_names:
            column = _schema_column_to_migration_column(parse_columns([col])[0])
            after = newcols[i - 1]["name"]
            storage_set = StorageSetKey(newstorage_dict["storage"]["set_key"])
            forwardops += [
                AddColumn(
                    storage_set=storage_set,
                    table_name=newstorage_dict["schema"]["local_table_name"],
                    column=column,
                    after=after,
                    target=OperationTarget.LOCAL,
                ),
                AddColumn(
                    storage_set=storage_set,
                    table_name=newstorage_dict["schema"]["dist_table_name"],
                    column=column,
                    after=after,
                    target=OperationTarget.DISTRIBUTED,
                ),
            ]
    return (forwardops, [op.get_reverse() for op in reversed(forwardops)])
