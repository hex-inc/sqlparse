import sqlparse

def test_from_first():
    statement = sqlparse.parse("""
from dataframe
""")[0]
    assert statement.get_type() == "SELECT"

def test_pivot():
    statement = sqlparse.parse("""
PIVOT
    dataframe
ON 'value_' || value
USING sum(value_count)
GROUP BY value_id
""")[0]
    assert statement.get_type() == "SELECT"


def test_pivot_with_cte():
    statement = sqlparse.parse("""
with my_cte as (
    select * from df
)
PIVOT my_cte ON date USING SUM(number)
""")[0]
    assert statement.get_type() == "SELECT"