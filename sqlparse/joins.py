import itertools


# this data structure is a kind of grammar for allowed SQL joins. it expands
# to a sequence of keyword tuples representing valid joins as follows:
# - tuples expand to a union of the types encoded in each element
#   - empty string element means the "group" is optional
# - lists represent product of the types encoded in each element
# - strings represent a literal option for an element of the type
#
# it is mainly modeled after the duckdb join syntax documented here:
#   https://duckdb.org/docs/sql/query_syntax/from#syntax
JOIN_TYPES = (
    'STRAIGHT_JOIN',
    [
        (
            'CROSS',
            'POSITIONAL',
            [
                ('', 'NATURAL', 'ASOF'),
                ('', 'INNER', [('LEFT', 'RIGHT', 'FULL'), ('', 'OUTER')]),
            ],
        ),
        'JOIN',
    ],
)


# generates all valid join types as a sequence of tuples of keywords
def enumerate_types(join_types=JOIN_TYPES):
    if isinstance(join_types, str):
        yield (join_types,) if join_types else ()
    elif isinstance(join_types, tuple):
        for type in join_types:
            yield from enumerate_types(type)
    else:
        combinations = itertools.product(*[
            enumerate_types(type) for type in join_types
        ])
        yield from sorted({
            tuple(itertools.chain.from_iterable(combo))
            for combo in combinations
        })


# transforms the `JOIN_TYPES` representation into a regex matching any valid'
# join type, in a format compatible with the lexer's `SQL_REGEX`
def types_as_regex(join_types=JOIN_TYPES):
    if isinstance(join_types, str):
        return join_types + (r'\b' if 'JOIN' in join_types else r'\s+')
    elif isinstance(join_types, tuple):
        is_optional = '' in join_types
        group = '|'.join(
            types_as_regex(type)
            for type in join_types
            if type != ''
        )
        return '(?:' + group + ')' + ('?' if is_optional else '')
    else:
        return ''.join(types_as_regex(type) for type in join_types)
