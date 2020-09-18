from elasticsearch import Elasticsearch
from pprint import pprint
from typing import Optional, Sequence, Union

from unicorn.model import ElasticSort, Query, QueryBuilder, QueryNode, Result
from unicorn.utils import timer


class BasicQueryExecutor:
    debug = False

    def __init__(
        self,
        client: Elasticsearch,
        qb: QueryBuilder,
        index: str,
        limit: int = 10000
    ):
        self.client = client
        self.qb = qb
        self.index = index
        self.limit = limit
        self.clear_counters()

    def clear_counters(self):
        self.took_ms = 0
        self.es_took_ms = 0
        self.truncated = 0

    # TODO: Distinguish inner and outer execution?
    def __call__(
        self,
        query_node: Union[Query, QueryNode],
        sort: ElasticSort,
        size: int = 10,
        source: Optional[Sequence[str]] = None,
    ) -> Result:
        if isinstance(query_node, Query):
            query = query_node
        else:
            # can't isinstance against a Union type, just
            # assume mypy caught all wrong callers...
            query = self.qb(query_node, self)

        request = {
            'query': query.es_query,
            'size': min(size, self.limit),
            '_source': source or False,
            'sort': sort,
        }
        if self.debug:
            pprint(request)
        with timer() as took:
            es_result = self.client.search(
                index=self.index,
                body=request)
        result = Result(es_result, took.ms)
        try:
            print('es took: {}ms took: {}ms hits: {} total_hits: {}'.format(
                result.es_took_ms,
                took.ms,
                len(result.hits),
                result.total_hits))
            self.took_ms += took.ms
            self.es_took_ms += result.es_took_ms
            self.truncated += result.total_hits - len(result.hits)
        except KeyError:
            # TODO: Error result
            print(es_result)
            raise
        return result
