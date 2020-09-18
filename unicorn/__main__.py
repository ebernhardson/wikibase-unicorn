from argparse import ArgumentParser
from elasticsearch import Elasticsearch
from pprint import pprint
from textwrap import dedent
import sys

from unicorn import parser, sexpr
from unicorn.qe import BasicQueryExecutor
from unicorn.qb import BasicQueryBuilder
from unicorn.utils import timer


def line_in(val: str) -> str:
    return sys.stdin.read() if val == '-' else val


def arg_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('--dump-sexpr', action='store_true', default=False)
    parser.add_argument('--dump-parse', action='store_true', default=False)
    parser.add_argument('--elasticsearch', default=None)
    parser.add_argument('--index', default='wikidatawiki_content')
    parser.add_argument('--size', type=int, default=100)
    parser.add_argument('--report-lang', default='en')
    parser.add_argument('expression', type=line_in)
    return parser


def run(
    expression: str,
    report_lang: str,
    size: int,
    index: str,
    elasticsearch: str,
    dump_parse: bool,
    dump_sexpr: bool,
) -> int:
    root_token = sexpr.parse(expression)
    if dump_sexpr:
        pprint(root_token)
        return 0

    query = parser.parse(root_token)
    if dump_parse:
        pprint(query)
        return 0

    client = Elasticsearch(elasticsearch)
    qb = BasicQueryBuilder(
        id_source='title',
        id_field='title.keyword',
        edge_field='statement_keywords',
        edge_kind_field='statement_keywords.property',
        sort={'sitelink_count': {'order': 'desc'}},
    )
    executor = BasicQueryExecutor(client, qb, index)
    with timer() as took:
        result = executor(
            query,
            size=size,
            source=[
                'title',
                'labels.' + report_lang
            ],
            sort=qb.sort,
        )

    prefix_len = max(len(hit.id) for hit in result.hits)
    fmt = '{:%ss} - {}' % prefix_len
    for hit in result.hits:
        try:
            label = hit.label(report_lang)
        except KeyError:
            label = ''
        print(fmt.format(hit.id, label))

    net_took = executor.took_ms - executor.es_took_ms
    unicorn_took = took.ms - executor.took_ms
    inner_truncated = executor.truncated - result.truncated
    num_hits = len(result.hits)
    print(dedent("""
        totals:
            returned:     {num_hits: 4d} docs
            total:        {result.total_hits: 4d} docs
            inner trunc:  {inner_truncated: 4d} docs
            es took:      {executor.es_took_ms: 6.1f}ms
            net took:     {net_took: 6.1f}ms
            unicorn took: {unicorn_took: 6.1f}ms
            total took:   {took.ms: 6.1f}ms
    """.format(**locals())))
    return 0


def main():
    args = arg_parser().parse_args()
    sys.exit(run(**dict(vars(args))))
