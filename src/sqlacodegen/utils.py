from __future__ import annotations

from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.engine import Connectable
from sqlalchemy.sql import ClauseElement
from sqlalchemy.sql.schema import (
    CheckConstraint, ColumnCollectionConstraint, Constraint, ForeignKeyConstraint, Index, Table)


def get_column_names(constraint: ColumnCollectionConstraint) -> list[str]:
    return list(constraint.columns.keys())


def get_constraint_sort_key(constraint: Constraint) -> str:
    if isinstance(constraint, CheckConstraint):
        return f'C{constraint.sqltext}'
    elif isinstance(constraint, ColumnCollectionConstraint):
        return constraint.__class__.__name__[0] + repr(get_column_names(constraint))
    else:
        return str(constraint)


def get_compiled_expression(statement: ClauseElement, bind: Connectable) -> str:
    """Return the statement in a form where any placeholders have been filled in."""
    return str(statement.compile(bind, compile_kwargs={"literal_binds": True}))


def get_common_fk_constraints(table1: Table, table2: Table) -> set[ForeignKeyConstraint]:
    """Return a set of foreign key constraints the two tables have against each other."""
    c1 = {c for c in table1.constraints if isinstance(c, ForeignKeyConstraint) and
          c.elements[0].column.table == table2}
    c2 = {c for c in table2.constraints if isinstance(c, ForeignKeyConstraint) and
          c.elements[0].column.table == table1}
    return c1.union(c2)


def uses_default_name(constraint: Constraint | Index) -> bool:
    if not constraint.name or constraint.table is None:
        return True

    table = constraint.table
    values = {
        'table_name': table.name,
        'constraint_name': constraint.name
    }
    if isinstance(constraint, (Index, ColumnCollectionConstraint)):
        values.update({
            'column_0N_name': ''.join(col.name for col in constraint.columns),
            'column_0_N_name': '_'.join(col.name for col in constraint.columns),
            'column_0N_label': ''.join(col.label(col.name).name for col in constraint.columns),
            'column_0_N_label': '_'.join(col.label(col.name).name for col in constraint.columns),
            'column_0N_key': ''.join(col.key for col in constraint.columns),  # type: ignore[misc]
            'column_0_N_key': '_'.join(col.key  # type: ignore[misc]
                                       for col in constraint.columns)
        })
        if constraint.columns:
            values.update({
                'column_0_name': constraint.columns[0].name,  # type: ignore[index]
                'column_0_label': constraint.columns[0].label(  # type: ignore[index]
                    constraint.columns[0].name).name,  # type: ignore[index]
                'column_0_key': constraint.columns[0].key  # type: ignore[index]
            })

    if isinstance(constraint, Index):
        key = 'ix'
    elif isinstance(constraint, CheckConstraint):
        key = 'ck'
    elif isinstance(constraint, UniqueConstraint):
        key = 'uq'
    elif isinstance(constraint, PrimaryKeyConstraint):
        key = 'pk'
    elif isinstance(constraint, ForeignKeyConstraint):
        key = 'fk'
        values.update({
            'referred_table_name': constraint.referred_table,
            'referred_column_0_name': constraint.elements[0].column.name,
            'referred_column_0N_name': ''.join(fk.column.name for fk in constraint.elements),
            'referred_column_0_N_name': '_'.join(fk.column.name for fk in constraint.elements),
            'referred_column_0_label': constraint.elements[0].column.label(
                constraint.elements[0].column.name).name,
            'referred_fk.column_0N_label': ''.join(fk.column.label(fk.column.name).name
                                                   for fk in constraint.elements),
            'referred_fk.column_0_N_label': '_'.join(fk.column.label(fk.column.name).name
                                                     for fk in constraint.elements),
            'referred_fk.column_0_key': constraint.elements[0].column.key,
            'referred_fk.column_0N_key': ''.join(fk.column.key  # type: ignore[misc]
                                                 for fk in constraint.elements),
            'referred_fk.column_0_N_key': '_'.join(fk.column.key  # type: ignore[misc]
                                                   for fk in constraint.elements)
        })
    else:
        raise TypeError(f'Unknown constraint type: {constraint.__class__.__qualname__}')

    try:
        convention: str = table.metadata.naming_convention[key]
    except KeyError:
        return False

    return constraint.name == (convention % values)
