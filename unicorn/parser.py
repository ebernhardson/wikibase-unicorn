"""Transformed parsed s-expr into the query language"""

from typing import Dict, Optional, Protocol, Sequence, TypeVar

from unicorn.model import (
    # unicorn query
    ApplyNode, BoolKind, BoolNode, ExtractNode,
    QueryNode, TermNode,
    # sexpr
    Token, ExpressionToken, StringToken)


class ParseError(Exception):
    def __init__(self, msg: str, node: Optional[Token] = None):
        super().__init__(msg)
        self.node = node


class InvalidExpression(ParseError):
    pass


class VisitorFn(Protocol):
    def __call__(
        self,
        token: Sequence[Token],
        **kwargs
    ) -> QueryNode: ...


class _VisitorFn(Protocol):
    def __call__(
        self,
        token: Sequence[Token],
    ) -> QueryNode: ...


T = TypeVar('T', bound=VisitorFn)


class ExpressionVisitors:
    def __init__(self):
        self.commands: Dict[str, _VisitorFn] = {}

    def register(self, name: str, **kwargs):
        def wrapper(fn: T) -> T:
            self.commands[name] = lambda token: fn(token, **kwargs)
            return fn
        return wrapper

    def visit(self, token: ExpressionToken) -> QueryNode:
        if len(token.tokens) == 0:
            raise InvalidExpression("expression must contain at least one value", token)
        command_token = token.tokens[0]
        if not isinstance(command_token, StringToken):
            raise InvalidExpression("expression first argument must be a string", command_token)
        name = command_token.value.lower()
        try:
            visitor = self.commands[name]
        except KeyError:
            raise InvalidExpression("unknown expression command", command_token)
        try:
            return visitor(token.tokens[1:])
        except ParseError as e:
            if e.node is None:
                e.node = token
            raise


expr_visitors = ExpressionVisitors()


@expr_visitors.register('and', kind=BoolKind.MUST)
@expr_visitors.register('or', kind=BoolKind.SHOULD)
@expr_visitors.register('not', kind=BoolKind.MUST_NOT)
def visit_bool(args: Sequence[Token], kind: BoolKind) -> QueryNode:
    if len(args) == 0:
        raise ParseError('no arguments provided to boolean')
    return BoolNode(**{
        kind.name.lower(): [parse(x) for x in args]
    })


@expr_visitors.register('term')
def visit_term(args: Sequence[Token]) -> QueryNode:
    if len(args) != 1 or not isinstance(args[0], StringToken):
        raise ParseError('term requires single string argument')
    return TermNode(args[0].value)


@expr_visitors.register('apply')
def visit_apply(args: Sequence[Token]) -> QueryNode:
    if len(args) != 2:
        raise ParseError('apply must have two arguments')
    prefix, query = args
    if not isinstance(prefix, StringToken):
        raise ParseError('first argument to apply must be a string')
    return ApplyNode(prefix.value, parse(query))


@expr_visitors.register('extract')
def visit_extract(args: Sequence[Token]) -> ExtractNode:
    if len(args) != 2:
        raise ParseError('extract requires two arguments')
    key, query = args
    if not isinstance(key, StringToken):
        raise ParseError('first argument to extract must be a string')
    return ExtractNode(key.value, parse(query))


@expr_visitors.register('difference')
def visit_difference(args: Sequence[Token]) -> BoolNode:
    if len(args) < 2:
        raise ParseError('difference requires at least two arguments')
    must, must_not = parse(args[0]), [parse(x) for x in args[1:]]
    return BoolNode(must=[must], must_not=must_not)


def parse(token: Token) -> QueryNode:
    if isinstance(token, ExpressionToken):
        return expr_visitors.visit(token)
    elif isinstance(token, StringToken):
        # Bare string interpreted as (term value)
        return visit_term([token])
    else:
        raise NotImplementedError('Unreachable')
