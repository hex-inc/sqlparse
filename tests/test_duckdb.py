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