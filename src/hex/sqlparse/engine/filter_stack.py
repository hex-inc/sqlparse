#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""filter"""

from hex.sqlparse import lexer
from hex.sqlparse.engine import grouping
from hex.sqlparse.engine.statement_splitter import StatementSplitter
from hex.sqlparse.filters import StripTrailingSemicolonFilter


class FilterStack:
    def __init__(self, strip_semicolon=False):
        self.preprocess = []
        self.stmtprocess = []
        self.postprocess = []
        self._grouping = False
        if strip_semicolon:
            self.stmtprocess.append(StripTrailingSemicolonFilter())

    def enable_grouping(self):
        self._grouping = True

    def run(self, sql, encoding=None):
        stream = lexer.tokenize(sql, encoding)
        # Process token stream
        for filter_ in self.preprocess:
            stream = filter_.process(stream)

        stream = StatementSplitter().process(stream)

        # Output: Stream processed Statements
        for stmt in stream:
            if self._grouping:
                stmt = grouping.group(stmt)

            for filter_ in self.stmtprocess:
                filter_.process(stmt)

            for filter_ in self.postprocess:
                stmt = filter_.process(stmt)

            yield stmt
