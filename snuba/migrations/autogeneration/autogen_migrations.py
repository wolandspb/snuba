import os

import requests
import yaml

from snuba.clickhouse.columns import Column, SchemaModifiers
from snuba.datasets.configuration.utils import parse_columns
from snuba.migrations.operations import AddColumn, DropColumn

"""
This file is for autogenerating the migration for adding a column to your storage.
"""


def dict_diff(d1: dict, d2: dict) -> dict:
    diff = {
        "in_d1_not_d2": set(),
        "in_d2_not_d1": set(),
        "different_values": {},
    }

    s1 = set(d1.keys())
    s2 = set(d2.keys())
    diff["in_d1_not_d2"] = s1 - s2
    diff["in_d2_not_d1"] = s2 - s1

    for key in d1:
        if key in d2 and d1[key] != d2[key]:
            diff["different_values"][key] = {"d1": d1[key], "d2": d2[key]}

    return diff


def get_added_columns(
    oldstorage: str, newstorage: str
) -> list[Column[SchemaModifiers]]:
    """
    Input:
        old_storage, this is the old storage yaml in str format
        new_storage, this is the new modified storage yaml in str format

    Validates that the changes to the storage are supported, and returns the columns that were added.
    """
    oldstorage_dict = yaml.safe_load(oldstorage)
    newstorage_dict = yaml.safe_load(newstorage)

    if oldstorage_dict == newstorage_dict:
        print("storages are the same, nothing to do")
        return []

    res, reason = _only_columns_changed(oldstorage_dict, newstorage_dict)
    if not res:
        raise ValueError(
            f"""Error: expected the only change in the storage to be columns but it wasnt.
Message: {reason}"""
        )

    # columns
    oldstorage_cols = oldstorage_dict["schema"]["columns"]
    newstorage_cols = newstorage_dict["schema"]["columns"]
    left, right = 0, 0
    addedcols = []
    while left < len(oldstorage_cols) and right < len(newstorage_cols):
        if oldstorage_cols[left] == newstorage_cols[right]:
            left += 1
            right += 1
        else:
            if oldstorage_cols[left]["name"] == newstorage_cols[right]["name"]:
                raise ValueError(
                    f"""Error: column modification is unsupported, {oldstorage_cols[left]["name"]} was modified"""
                )
            elif left == 0:
                raise ValueError(
                    "Error: Adding a column to the beginning is currently unsupported, please add it anywhere else."
                )
            else:
                addedcols += parse_columns([newstorage_cols[right]])
                right += 1
    if left != len(oldstorage_cols):
        raise ValueError(
            f"Error: only column addition is currently supported, no modification or removal. Could not find a match for {oldstorage_cols[left]}"
        )
    if right < len(newstorage_cols):
        addedcols += parse_columns(newstorage_cols[right : len(newstorage_cols)])
    return addedcols


def _only_columns_changed(old_storage: dict, new_storage: dict) -> tuple[bool, str]:
    if old_storage == new_storage:
        return True, "storages are the exact same"
    # validate yamls
    diff = dict_diff(old_storage, new_storage)
    if diff["in_d1_not_d2"] or diff["in_d2_not_d1"]:
        return (
            False,
            f"""
Old and new storages to have different key sets:
in_old_not_new: {diff["in_d1_not_d2"]}
in_new_not_old: {diff["in_d2_not_d1"]}
""",
        )
    assert diff["different_values"]  # otherwise they are the exact same
    if (
        len(diff["different_values"].keys()) > 1
        or list(diff["different_values"].keys())[0] != "schema"
    ):
        return (
            False,
            f"expected only schema field to change, but got {diff['different_values'].keys()}",
        )
    # validate schemas
    schema_diff = dict_diff(
        diff["different_values"]["schema"]["d1"],
        diff["different_values"]["schema"]["d2"],
    )
    if schema_diff["in_d1_not_d2"] or schema_diff["in_d2_not_d1"]:
        return (
            False,
            f"""
Old and new schemas have different keysets
in_old_not_new: {schema_diff["in_d1_not_d2"]}
in_new_not_old: {schema_diff["in_d2_not_d1"]}
""",
        )
    assert schema_diff["different_values"]  # otherwise exact same
    if (
        len(schema_diff["different_values"].keys()) > 1
        or list(schema_diff["different_values"].keys())[0] != "columns"
    ):
        return (
            False,
            f"Expected the only changed field to be columns, but got {schema_diff['different_values'].keys()}",
        )
    return True, ""


"""
def column_to_addcolumn_migration(list[Column] | Column) -> list[AddColumn] | AddColumn:
    storage_set = StorageSetKey(old_storage["storage"]["set_key"])
    newcol = parse_columns([newcols[r]])[0]
    after = None if l == len(oldcols) else oldcols[l - 1]["name"]
    col_migrations = [
        AddColumn(
            storage_set=storage_set,
            table_name=old_storage["schema"]["local_table_name"],
            column=newcol,
            after=after,
            target=OperationTarget.LOCAL,
        ),
        AddColumn(
            storage_set=storage_set,
            table_name=old_storage["schema"]["dist_table_name"],
            column=newcol,
            after=after,
            target=OperationTarget.DISTRIBUTED,
        ),
    ]
    return []
"""


def build_add_col_migrations(
    colsToAdd: Column[SchemaModifiers],
) -> tuple[list[AddColumn], list[DropColumn]]:
    """
    Given the columns to add to add to the storage,
    builds and return the forward and backwards ops as a tuple.
    """
    return ([], [])


STORAGE_YAML = "snuba/datasets/configuration/events/storages/errors.yaml"
with open(os.path.abspath(os.path.expanduser(STORAGE_YAML)), "r") as f:
    local_storage = yaml.safe_load(f)

SNUBA_REPO = "https://raw.githubusercontent.com/getsentry/snuba/master"
res = requests.get(f"{SNUBA_REPO}/{STORAGE_YAML}")
origin_storage = yaml.safe_load(res.text)

# colsToAdd = get_added_columns(origin_storage, local_storage)
# forwardops, backwardsops = build_add_col_migrations(colsToAdd)
print("hi")


'''
oldcols = {}
    for e in schema_diff["different_values"]["columns"]["d1"]:
        if e["name"] in oldcols:
            raise ValueError(
                f"Error: duplicate column name \"{e['name']}\" in oldstorage"
            )
        oldcols[e["name"]] = e
    newcols = {}
    for e in schema_diff["different_values"]["columns"]["d2"]:
        if e["name"] in newcols:
            raise ValueError(
                f"Error: duplicate column name \"{e['name']}\" in new storage"
            )
        newcols[e["name"]] = e

    col_diff = dict_diff(oldcols, newcols)
    if col_diff["different_values"]:
        raise ValueError(
            f"""Error: column modification unsupported, only column addition is
schema.columns different_values: {schema_diff['different_values']['columns']}
"""
        )
    if col_diff["in_d1_not_d2"]:
        raise ValueError(
            f"""
Error: column removal unsupported, only column addition
in_old_not_new: {col_diff["in_d1_not_d2"]}
"""
        )
    assert col_diff["in_d2_not_d1"]
    return parse_columns([newcols[k] for k in col_diff["in_d2_not_d1"]])
'''
