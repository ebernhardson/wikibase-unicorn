from elasticsearch import Elasticsearch
import hug
from jinja2 import FileSystemLoader, Environment
import json
import os
from typing import Any, Dict

from unicorn.qb import BasicQueryBuilder
from unicorn.qe import BasicQueryExecutor
from unicorn.utils import timer
from unicorn import parser, sexpr

# There isn't a particularly convenient way to keep application
# specific state, it has to be module level. For a demo app
# that seems acceptable.

config: Dict[str, Any] = {
    'index_name': os.environ.get('UNICORN_INDEX', 'wikidatawiki_content'),
    'elasticsearch': {
        'hosts': os.environ.get('UNICORN_ELASTIC', None)
    },
    'query_builder': {
        'id_source': 'title',
        'id_field': 'title.keyword',
        'edge_field': 'statement_keywords',
        'edge_kind_field': 'statement_keywords.property',
        'sort': {'sitelink_count': {'order': 'desc'}},
    },
    'templates_path': os.environ.get('UNICORN_TEMPLATES', 'templates'),
}

config_path = os.environ.get('UNICORN_CONFIG', None)
if config_path:
    with open(config_path, 'rb') as f:
        config.update(json.load(f))


qb = BasicQueryBuilder(**config['query_builder'])
template_engine = Environment(loader=FileSystemLoader(config['templates_path']))
elastic = Elasticsearch(**config['elasticsearch'])


def make_executor():
    """Per-request query executor"""
    return BasicQueryExecutor(elastic, qb, config['index_name'])


def get_template(name):
    return template_engine.get_template(name)


def output_format_html_template(name):
    handler = hug.output_format.html

    def output_type(content, **kwargs):
        return handler(content=get_template(name).render(content))

    output_type.content_type = handler.content_type
    output_type.__doc__ = "@TODO"
    return output_type


@hug.get('/', output=output_format_html_template('index.html'))
def root():
    return {}


@hug.get('/search', output=hug.output_format.accept({
    'application/json': hug.output_format.json,
    'text/html': output_format_html_template('search.html'),
}))
def search(q: str, size: int = 1000, lang: str = 'en'):
    executor = make_executor()
    with timer() as took:
        result = executor(
            parser.parse(sexpr.parse(q)),
            size=size,
            source=['title', 'labels.' + lang],
            sort=qb.sort,
        )

    result_truncated = result.total_hits - len(result.hits)
    return {
        'q': q,
        'hits': [{
            'id': hit.id,
            'label': hit.label(lang, ''),
        } for hit in result.hits],
        'total_hits': result.total_hits,
        'debug': {
            'inner_truncated': executor.truncated - result_truncated,
            'result_truncated': result_truncated,
            'es_took_ms': executor.es_took_ms,
            'net_took_ms': executor.took_ms - executor.es_took_ms,
            'unicorn_took_ms': took.ms - executor.took_ms,
            'total_took_ms': took.ms,
        }
    }
