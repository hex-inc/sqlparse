import itertools


JOIN_TYPES = (
    'CROSS',
    'POSITIONAL',
    [
        ('', 'NATURAL', 'ASOF'),
        ('', 'INNER', [('LEFT', 'RIGHT', 'FULL'), ('', 'OUTER')]),
    ],
)


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


def types_as_regex(join_types=JOIN_TYPES):
    if isinstance(join_types, str):
        return join_types + r'\s+'
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
