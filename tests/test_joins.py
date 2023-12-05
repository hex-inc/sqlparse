from sqlparse import joins


def test_enumerate_join_types():
    expected_join_types = {
        ('JOIN',),
        ('STRAIGHT_JOIN',),
        ('CROSS', 'JOIN'),
        ('POSITIONAL', 'JOIN'),
        ('NATURAL', 'JOIN'),
        ('NATURAL', 'INNER', 'JOIN'),
        ('NATURAL', 'LEFT', 'JOIN'),
        ('NATURAL', 'LEFT', 'OUTER', 'JOIN'),
        ('NATURAL', 'RIGHT', 'JOIN'),
        ('NATURAL', 'RIGHT', 'OUTER', 'JOIN'),
        ('NATURAL', 'FULL', 'JOIN'),
        ('NATURAL', 'FULL', 'OUTER', 'JOIN'),
        ('ASOF', 'JOIN'),
        ('ASOF', 'INNER', 'JOIN'),
        ('ASOF', 'LEFT', 'JOIN'),
        ('ASOF', 'LEFT', 'OUTER', 'JOIN'),
        ('ASOF', 'RIGHT', 'JOIN'),
        ('ASOF', 'RIGHT', 'OUTER', 'JOIN'),
        ('ASOF', 'FULL', 'JOIN'),
        ('ASOF', 'FULL', 'OUTER', 'JOIN'),
        ('INNER', 'JOIN'),
        ('LEFT', 'JOIN'),
        ('LEFT', 'OUTER', 'JOIN'),
        ('RIGHT', 'JOIN'),
        ('RIGHT', 'OUTER', 'JOIN'),
        ('FULL', 'JOIN'),
        ('FULL', 'OUTER', 'JOIN'),
    }
    assert set(joins.enumerate_types()) == expected_join_types
