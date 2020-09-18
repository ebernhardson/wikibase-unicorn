"""Data values passed around unicorn

Must not import any other unicorn files
"""
from __future__ import annotations
from dataclasses import dataclass, field
import enum
from typing import Any, Mapping, Optional, Protocol, Sequence, Union


# Type helpers

ElasticSort = Union[str, Mapping[str, Any]]

# AST for representing an s-expression


@dataclass
class ExpressionToken:
    tokens: Sequence[Token]

    def __len__(self):
        return len(self.tokens)


@dataclass
class StringToken:
    value: str
    quoted: bool = False


Token = Union[StringToken, ExpressionToken]


# AST for representing a query


@dataclass
class ApplyNode:
    prefix: str
    query: QueryNode


@dataclass
class BoolKind(enum.Enum):
    MUST = enum.auto()
    MUST_NOT = enum.auto()
    SHOULD = enum.auto()

    def __repr__(self):
        # parent repr doesnt mention value due to auto,
        # this prints the class property.
        return str(self)


@dataclass
class BoolNode:
    must: Sequence[QueryNode] = field(default_factory=list)
    must_not: Sequence[QueryNode] = field(default_factory=list)
    should: Sequence[QueryNode] = field(default_factory=list)


@dataclass
class ExtractNode:
    key: str
    query: QueryNode


@dataclass
class TermNode:
    """Represents a query against a graph edge

    May query for entities containing an exact edge (ex: P1=Q1),
    or entities containing a particular kind of edge (ex: P1).
    """
    value: str

    @property
    def is_edge_type_query(self):
        return '=' not in self.value

    @property
    def is_edge_query(self):
        return '=' in self.value


QueryNode = Union[ApplyNode, BoolNode, ExtractNode, TermNode]


# Query execution phase

@dataclass
class Query:
    es_query: Mapping
    hit_ids: Optional[Sequence[str]] = None


# sigil default arg value indicating no value passed. allows
# to detect user provided None
no_arg = object()


@dataclass
class Hit:
    # TODO: what is type?
    es_hit: Any

    @property
    def id(self):
        return self.es_hit['_source']['title']

    @property
    def edges(self) -> Sequence[str]:
        # Only available when requested
        return self.es_hit['_source']['statement_keywords']

    def labels(self, lang: str, default=no_arg) -> str:
        try:
            return self.es_hit['_source']['labels'][lang]
        except KeyError:
            if default is no_arg:
                raise
            return default

    def label(self, lang: str, default=no_arg) -> str:
        try:
            return self.labels(lang)[0]
        except KeyError:
            if default is no_arg:
                raise
            return default


@dataclass
class Result:
    # TODO: what is type?
    es_result: Any
    took_ms: float

    @property
    def es_took_ms(self):
        return self.es_result['took']

    @property
    def hits(self) -> Sequence[Hit]:
        return [Hit(hit) for hit in self.es_result['hits']['hits']]

    @property
    def total_hits(self) -> int:
        return self.es_result['hits']['total']

    @property
    def truncated(self):
        return self.es_result['hits']['total'] \
                - len(self.es_result['hits']['hits'])


class QueryBuilder(Protocol):
    def __call__(
        self,
        node: QueryNode,
        qe: QueryExecutor
    ) -> Query: ...


class QueryExecutor(Protocol):
    def __call__(
        self,
        query_node: Union[Query, QueryNode],
        sort: ElasticSort,
        size: int = ...,
        source: Optional[Sequence[str]] = ...,
    ) -> Result: ...
