"""Build elasticsearch queries from query language"""
from __future__ import annotations
from typing import Callable, Dict, Mapping, Sequence, Type, TypeVar
from unicorn.model import (
    Query, QueryBuilder, QueryExecutor, QueryNode,
    ApplyNode, BoolNode, ExtractNode, TermNode,
    ElasticSort,
)


T = TypeVar('T', bound=Callable)


class ExactTypeDispatch:
    def __init__(self, fns: Dict[Type, Callable] = None):
        self.fns: Dict[Type, Callable] = fns or {}

    def register(self, type: Type):
        """Returns decorator method to register handler for type

        Type could be derived from fn, but taking it explicitly
        seemed more straight forward than using inspect.
        """
        def wrapper(fn: T) -> T:
            self.fns[type] = fn
            return fn
        return wrapper

    def using(self, fn_self, sort: ElasticSort) -> QueryBuilder:
        def qb(node: QueryNode, qe: QueryExecutor) -> Query:
            return self.fns[type(node)](fn_self, node, qe)  # type: ignore
        return qb

    def __call__(self, node: QueryNode, qe: QueryExecutor) -> Query:
        """Call function register for type of node"""
        return self.fns[type(node)](node, qe)


class BasicQueryBuilder:
    dispatch = ExactTypeDispatch()

    def __init__(
        self,
        id_source: str,
        id_field: str,
        edge_field: str,
        edge_kind_field: str,
        sort: ElasticSort,
        inner_limit: int = 900,
    ):
        self.id_source = id_source
        self.id_field = id_field
        self.edge_field = edge_field
        self.edge_kind_field = edge_kind_field
        self.build = self.dispatch.using(self, sort)
        self.sort = sort
        self.inner_limit = inner_limit

    def __call__(self, node: QueryNode, qe: QueryExecutor) -> Query:
        return self.build(node, qe)

    @dispatch.register(ApplyNode)
    def build_apply(self, node: ApplyNode, qe: QueryExecutor) -> Query:
        results = qe(
            node.query,
            size=self.inner_limit,
            source=[self.id_source],
            sort=self.sort,
        )
        return Query({
            'bool': {
                # TODO: search analyzer that can split on spaces only
                'should': [{
                    'match': {
                        self.edge_field: {
                            'query': node.prefix + hit.id
                        }
                    }
                } for hit in results.hits]
            }
        })

    @dispatch.register(BoolNode)
    def build_bool(self, node: BoolNode, qe: QueryExecutor) -> Query:
        def build(queries: Sequence[QueryNode]) -> Sequence[Mapping]:
            return [self.build(q, qe).es_query for q in queries]

        queries = {}
        if node.must:
            queries['must'] = build(node.must)
        if node.must_not:
            queries['must_not'] = build(node.must_not)
        if node.should:
            queries['should'] = build(node.should)
        if not queries:
            raise Exception('empty bool node')
        return Query({'bool': queries})

    @dispatch.register(ExtractNode)
    def build_extract(self, node: ExtractNode, qe: QueryExecutor) -> Query:
        # TODO: Should parsing provide this structure?
        es_query = {
            'bool': {
                'must': [
                    {
                        'match': {
                            self.edge_kind_field: node.key[:-1]
                        }
                    },
                    self.build(node.query, qe).es_query,
                ]
            }
        }

        # TODO: Executor needs to specialize on ExtractNode and
        # ApplyNode, or the queries will be silly inefficient.
        # Maybe an early transformation pass should do something.
        results = qe(
            Query(es_query),
            size=self.inner_limit,
            source=[self.edge_field],
            sort=self.sort,
        )
        hit_ids = []
        for hit in results.hits:
            for edge in hit.edges:
                if edge.startswith(node.key):
                    hit_ids.append(edge[len(node.key):])
        if not hit_ids:
            return Query({'match_none': {}})

        es_query = {
            'bool': {
                # TODO: search analyzer that can split on spaces only
                'should': [{
                    'match': {self.id_field: hit_id}
                } for hit_id in hit_ids]
            }
        }

        return Query(es_query, hit_ids)

    @dispatch.register(TermNode)
    def build_term(self, node: TermNode, qe: QueryExecutor) -> Query:
        if node.is_edge_query:
            field = self.edge_field
        else:
            field = self.edge_kind_field
        return Query({
            'match': {field: node.value}
        })
