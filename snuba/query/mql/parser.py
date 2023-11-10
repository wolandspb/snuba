from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple, Union

import sentry_sdk
from parsimonious.nodes import Node, NodeVisitor
from snuba_sdk.conditions import OPERATOR_TO_FUNCTION, Op
from snuba_sdk.dsl.dsl import EXPRESSION_OPERATORS, GRAMMAR, TERM_OPERATORS
from snuba_sdk.timeseries import Metric

from snuba.datasets.dataset import Dataset
from snuba.query import SelectedExpression
from snuba.query.composite import CompositeQuery
from snuba.query.conditions import binary_condition, combine_and_conditions
from snuba.query.data_source.simple import Entity as QueryEntity
from snuba.query.exceptions import InvalidQueryException
from snuba.query.expressions import Column, Expression, FunctionCall, Literal
from snuba.query.logical import Query as LogicalQuery
from snuba.query.query_settings import QuerySettings

logger = logging.getLogger("snuba.mql.parser")


class MQLVisitor(NodeVisitor):
    """
    Builds Snuba AST expressions from the MQL Parsimonious parse tree.
    """

    def visit(self, node: Node) -> Any:
        """Walk a parse tree, transforming it into a MetricsQuery object.

        Recursively descend a parse tree, dispatching to the method named after
        the rule in the :class:`~parsimonious.grammar.Grammar` that produced
        each node. If, for example, a rule was... ::

            bold = '<b>'

        ...the ``visit_bold()`` method would be called.
        """
        method = getattr(self, "visit_" + node.expr_name, self.generic_visit)
        try:
            result = method(node, [self.visit(n) for n in node])
            return result
        except Exception as e:
            raise e

    def visit_expression(self, node: Node, children: Sequence[Any]) -> LogicalQuery:
        """
        Top level node, simply returns the expression.
        """
        args, zero_or_more_others = children
        return args

    def visit_expr_op(self, node: Node, children: Sequence[Any]) -> Any:
        raise InvalidQueryException("Arithmetic function not supported yet")
        return EXPRESSION_OPERATORS[node.text]

    def visit_term(self, node: Node, children: Sequence[Any]) -> Any:
        """
        Checks if the current node contains two term children, if so
        then merge them into a single Formula with the operator.
        """
        term, zero_or_more_others = children
        if zero_or_more_others:
            raise InvalidQueryException("Arithmetic function not supported yet")
        return term

    def visit_term_op(self, node: Node, children: Sequence[Any]) -> Any:
        raise InvalidQueryException("Arithmetic function not supported yet")
        return TERM_OPERATORS[node.text]

    def visit_coefficient(self, node: Node, children: Any) -> Any:
        return children[0]

    def visit_number(self, node: Node, children: Sequence[Any]) -> float:
        return float(node.text)

    def visit_filter(self, node: Node, children: Sequence[Any]) -> Mapping[str, Any]:
        """ """
        args, packed_filters, packed_groupbys, *_ = children
        assert isinstance(args, dict)
        if packed_filters:
            _, _, first, zero_or_more_others, *_ = packed_filters[0]
            new_filters = combine_and_conditions(
                [first, *(v for _, _, _, v in zero_or_more_others)]
            )
            if "filters" in args:
                args["filters"] = combine_and_conditions([args["filters"], new_filters])
            else:
                args["filters"] = new_filters

        if packed_groupbys:
            group_by = packed_groupbys[0]
            if not isinstance(group_by, list):
                group_by = [group_by]
            if "groupby" in args:
                args["groupby"] = args["groupby"] + group_by
            else:
                args["groupby"] = group_by

        return args

    def visit_condition(self, node: Node, children: Sequence[Any]) -> Expression:
        condition_op, lhs, _, _, _, rhs = children
        op = Op.EQ
        if not condition_op and isinstance(rhs, list):
            op = Op.IN
        elif len(condition_op) == 1 and condition_op[0] == Op.NOT:
            if isinstance(rhs, str):
                op = Op.NEQ
            elif isinstance(rhs, list):
                op = Op.NOT_IN
        return binary_condition(
            OPERATOR_TO_FUNCTION[op].value, lhs[0], Literal(alias=None, value=rhs)
        )

    def visit_function(self, node: Node, children: Sequence[Any]) -> Mapping[str, Any]:
        """ """
        target, packed_groupbys = children
        if packed_groupbys:
            group_by = packed_groupbys[0]
            if not isinstance(group_by, list):
                group_by = [group_by]
            target["groupby"] = group_by

        return target

    def visit_group_by(self, node: Node, children: Sequence[Any]) -> Any:
        *_, groupby = children
        columns = groupby[0]
        return columns

    def visit_condition_op(self, node: Node, children: Sequence[Any]) -> Op:
        return Op(node.text)

    def visit_tag_key(self, node: Node, children: Sequence[Any]) -> Column:
        return Column(alias=None, table_name=None, column_name=node.text)

    def visit_tag_value(
        self, node: Node, children: Sequence[Union[str, Sequence[str]]]
    ) -> Any:
        tag_value = children[0]
        return tag_value

    def visit_quoted_string(self, node: Node, children: Sequence[Any]) -> str:
        return str(node.text[1:-1])

    def visit_quoted_string_tuple(
        self, node: Node, children: Sequence[Any]
    ) -> Sequence[str]:
        _, _, first, zero_or_more_others, _, _ = children
        return [first, *(v for _, _, _, v in zero_or_more_others)]

    def visit_group_by_name(
        self, node: Node, children: Sequence[Any]
    ) -> SelectedExpression:
        return SelectedExpression(
            name=None,
            expression=Column(alias=None, table_name=None, column_name=node.text),
        )

    def visit_group_by_name_tuple(
        self, node: Node, children: Sequence[Any]
    ) -> Sequence[SelectedExpression]:
        _, _, first, zero_or_more_others, _, _ = children
        return [first, *(v for _, _, _, v in zero_or_more_others)]

    def visit_target(self, node: Node, children: Sequence[Any]) -> Any:
        target = children[0]
        if isinstance(children[0], list):
            target = children[0][0]
        return target

    def visit_variable(self, node: Node, children: Sequence[Any]) -> Any:
        raise InvalidQueryException("Variables are not supported yet")
        return None

    def visit_nested_expression(self, node: Node, children: Sequence[Any]) -> Any:
        return children[2]

    def visit_aggregate(self, node: Node, children: Sequence[Any]) -> FunctionCall:
        aggregate_name, zero_or_one = children
        _, _, target, zero_or_more_others, *_ = zero_or_one
        target["aggregate"] = SelectedExpression(
            name=None,
            expression=FunctionCall(
                alias=None,
                function_name=aggregate_name,
                parameters=[Column(alias=None, table_name=None, column_name="value")],
            ),
        )

        return target

    def visit_aggregate_name(self, node: Node, children: Sequence[Any]) -> str:
        return node.text

    def visit_quoted_mri(self, node: Node, children: Sequence[Any]) -> Metric:
        return {"metric_name": {"mri": str(node.text[1:-1]), "public_name": ""}}

    def visit_unquoted_mri(self, node: Node, children: Sequence[Any]) -> Metric:
        return {"metric_name": {"mri": str(node.text), "public_name": ""}}

    def visit_quoted_public_name(self, node: Node, children: Sequence[Any]) -> Metric:
        return {"metric_name": {"mri": "", "public_name": str(node.text[1:-1])}}

    def visit_unquoted_public_name(self, node: Node, children: Sequence[Any]) -> Metric:
        return {"metric_name": {"mri": "", "public_name": str(node.text)}}

    def visit_identifier(self, node: Node, children: Sequence[Any]) -> str:
        return node.text

    def generic_visit(self, node: Node, children: Sequence[Any]) -> Any:
        """The generic visit method."""
        return children


def parse_mql_query_initial(
    body: str,
) -> Union[CompositeQuery[QueryEntity], LogicalQuery]:
    """
    Parses the query body MQL generating the AST. This only takes into
    account the initial query body. Extensions are parsed by extension
    processors and are supposed to update the AST.
    """
    try:
        exp_tree = GRAMMAR.parse(body)
        parsed = MQLVisitor().visit(exp_tree)
    except Exception as e:
        raise e

    return parsed


CustomProcessors = Sequence[
    Callable[[Union[CompositeQuery[QueryEntity], LogicalQuery]], None]
]


def parse_mql_query(
    body: str,
    dataset: Dataset,
    custom_processing: Optional[CustomProcessors] = None,
    settings: QuerySettings | None = None,
) -> Tuple[Union[CompositeQuery[QueryEntity], LogicalQuery], str]:
    with sentry_sdk.start_span(op="parser", description="parse_mql_query_initial"):
        parse_mql_query_initial(body)

    # TODO: Create post processors for adding mql context fields into the query.
