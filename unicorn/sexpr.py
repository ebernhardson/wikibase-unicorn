# https://rosettacode.org/wiki/S-Expressions#Python
# Content is available under GNU Free Documentation License 1.2

import re
from unicorn.model import Token, ExpressionToken, StringToken
from typing import List


term_regex = re.compile(r'''(?mx)
    \s*(?:
        (?P<brackl>\()|
        (?P<brackr>\))|
        (?P<sq>"[^"]*")|
        (?P<s>[^(^)\s]+)
       )''')


def parse(expression: str) -> Token:
    stack: List[List[Token]] = []
    out: List[Token] = []
    for termtypes in term_regex.finditer(expression):
        term, value = [(t, v) for t, v in termtypes.groupdict().items() if v][0]
        if term == 'brackl':
            stack.append(out)
            out = []
        elif term == 'brackr':
            assert stack, "Trouble with nesting of brackets"
            tmpout, out = out, stack.pop(-1)
            out.append(ExpressionToken(tmpout))
        elif term == 'sq':
            out.append(StringToken(value[1:-1], quoted=True))
        elif term == 's':
            out.append(StringToken(value))
        else:
            raise NotImplementedError("Unreachable: %s" % term)
    assert not stack, "Trouble with nesting of brackets"
    return out[0]
