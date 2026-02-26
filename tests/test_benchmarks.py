"""Benchmark tests for sqlparse.format(reindent=True) on large SQL queries.

Run with:
    uv run --with pytest --with pytest-benchmark pytest tests/test_benchmarks.py -v
"""

import pytest
import sqlparse

pytest.importorskip("pytest_benchmark")


# ---------------------------------------------------------------------------
# Query generators — deterministic, no randomness
# ---------------------------------------------------------------------------

def _wide_select_sql(n_cols=5000):
    cols = ', '.join(f'col_{i}' for i in range(n_cols))
    return f'SELECT {cols} FROM t'


def _large_in_list_sql(n=100000):
    values = ', '.join(str(i) for i in range(n))
    return f'SELECT * FROM t WHERE id IN ({values})'


def _large_insert_sql(n_rows=25000):
    rows = ', '.join(f'({i}, {i+1})' for i in range(n_rows))
    return f'INSERT INTO t VALUES {rows}'


def _deep_subqueries_sql(depth=12):
    q = 'SELECT * FROM t'
    for i in range(depth):
        q = f'SELECT * FROM ({q}) s{i}'
    return q


def _many_joins_sql(n=500):
    joins = ' '.join(
        f'JOIN t{i} ON t{i}.id = t{i-1}.id' for i in range(1, n + 1))
    return f'SELECT * FROM t0 {joins}'


def _complex_where_sql(depth=8, breadth=3):
    def _build(d, idx=0):
        if d == 0:
            return f'col_{idx} = {idx}'
        conn = 'AND' if d % 2 == 0 else 'OR'
        parts = []
        for i in range(breadth):
            parts.append(_build(d - 1, idx * breadth + i))
        return '(' + f' {conn} '.join(parts) + ')'
    return f'SELECT * FROM t WHERE {_build(depth)}'


def _mixed_batch_sql(n=50):
    stmts = []
    for i in range(n):
        if i % 4 == 0:
            cols = ', '.join(f'col_{j} INT' for j in range(20))
            stmts.append(f'CREATE TABLE t_{i} ({cols})')
        elif i % 4 == 1:
            rows = ', '.join(f'({j}, {j+1})' for j in range(100))
            stmts.append(f'INSERT INTO t_{i} VALUES {rows}')
        elif i % 4 == 2:
            cols = ', '.join(f't.col_{j}' for j in range(20))
            stmts.append(f'SELECT {cols} FROM t_{i} t WHERE t.col_0 > 0')
        else:
            stmts.append(
                f'UPDATE t_{i} SET col_0 = col_0 + 1 WHERE col_1 > 0')
    return '; '.join(stmts)


def _heavy_formatting_sql():
    cases = ', '.join(
        f'CASE WHEN col_{i} > 0 THEN col_{i} ELSE 0 END AS c_{i}'
        for i in range(200))
    return (
        f'WITH cte AS (SELECT {cases} FROM t) '
        f'SELECT * FROM cte WHERE c_0 > 0 ORDER BY c_1'
    )


# ---------------------------------------------------------------------------
# Reindent benchmarks (one per PR table row)
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="reindent")
def test_wide_select(benchmark):
    sql = _wide_select_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_large_in_list(benchmark):
    sql = _large_in_list_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_large_insert(benchmark):
    sql = _large_insert_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_deep_subqueries(benchmark):
    sql = _deep_subqueries_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_many_joins(benchmark):
    sql = _many_joins_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_complex_where(benchmark):
    sql = _complex_where_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_mixed_batch(benchmark):
    sql = _mixed_batch_sql()
    benchmark(sqlparse.format, sql, reindent=True)


@pytest.mark.benchmark(group="reindent")
def test_heavy_formatting(benchmark):
    sql = _heavy_formatting_sql()
    benchmark(sqlparse.format, sql, reindent=True)


# ---------------------------------------------------------------------------
# INSERT scaling benchmarks (_process_values)
# ---------------------------------------------------------------------------

@pytest.mark.benchmark(group="insert-scaling")
@pytest.mark.parametrize("n_rows", [5000, 10000, 25000], ids=["5k", "10k", "25k"])
def test_insert_scaling(benchmark, n_rows):
    sql = _large_insert_sql(n_rows)
    benchmark(sqlparse.format, sql, reindent=True)
