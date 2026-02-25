#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""SQL Lexer"""
import re
from threading import Lock

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.

from io import TextIOBase

from sqlparse import tokens, keywords


class Lexer:
    """The Lexer supports configurable syntax.
    To add support for additional keywords, use the `add_keywords` method."""

    _default_instance = None
    _lock = Lock()

    # Development notes:
    # - This class is prepared to be able to support additional SQL dialects
    #   in the future by adding additional functions that take the place of
    #   the function default_initialization().
    # - The lexer class uses an explicit singleton behavior with the
    #   instance-getter method get_default_instance(). This mechanism has
    #   the advantage that the call signature of the entry-points to the
    #   sqlparse library are not affected. Also, usage of sqlparse in third
    #   party code does not need to be adapted. On the other hand, the current
    #   implementation does not easily allow for multiple SQL dialects to be
    #   parsed in the same process.
    #   Such behavior can be supported in the future by passing a
    #   suitably initialized lexer object as an additional parameter to the
    #   entry-point functions (such as `parse`). Code will need to be written
    #   to pass down and utilize such an object. The current implementation
    #   is prepared to support this thread safe approach without the
    #   default_instance part needing to change interface.

    @classmethod
    def get_default_instance(cls):
        """Returns the lexer instance used internally
        by the sqlparse core functions."""
        with cls._lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
                cls._default_instance.default_initialization()
        return cls._default_instance

    def default_initialization(self):
        """Initialize the lexer with default dictionaries.
        Useful if you need to revert custom syntax settings."""
        self.clear()
        self.set_SQL_REGEX(keywords.SQL_REGEX)
        self.add_keywords(keywords.KEYWORDS_COMMON)
        self.add_keywords(keywords.KEYWORDS_ORACLE)
        self.add_keywords(keywords.KEYWORDS_MYSQL)
        self.add_keywords(keywords.KEYWORDS_PLPGSQL)
        self.add_keywords(keywords.KEYWORDS_HQL)
        self.add_keywords(keywords.KEYWORDS_MSACCESS)
        self.add_keywords(keywords.KEYWORDS_SNOWFLAKE)
        self.add_keywords(keywords.KEYWORDS_BIGQUERY)
        self.add_keywords(keywords.KEYWORDS)

    def clear(self):
        """Clear all syntax configurations.
        Useful if you want to load a reduced set of syntax configurations.
        After this call, regexps and keyword dictionaries need to be loaded
        to make the lexer functional again."""
        self._SQL_REGEX = []
        self._keywords = []

    def set_SQL_REGEX(self, SQL_REGEX):
        """Set the list of regex that will parse the SQL."""
        FLAGS = re.IGNORECASE | re.UNICODE

        # Build combined alternation regex for single-pass tokenization.
        # The dollar-quoted string pattern uses a backreference (\1) which
        # breaks in a combined alternation, so it's handled separately.
        self._dollar_quote_re = None
        self._dollar_quote_action = None

        combined_parts = []
        actions = []
        group_idx = 0
        for rx, action in SQL_REGEX:
            if r'\1' in rx or r'\2' in rx:
                self._dollar_quote_re = re.compile(rx, FLAGS)
                self._dollar_quote_action = action
                continue
            combined_parts.append(f'(?P<g{group_idx}>{rx})')
            actions.append(action)
            group_idx += 1

        self._combined_re = re.compile('|'.join(combined_parts), FLAGS)
        self._actions = actions

        # Keep legacy list for external code that accesses _SQL_REGEX
        self._SQL_REGEX = [
            (re.compile(rx, FLAGS).match, tt) for rx, tt in SQL_REGEX
        ]

    def add_keywords(self, keywords):
        """Add keyword dictionaries. Keywords are looked up in the same order
        that dictionaries were added."""
        self._keywords.append(keywords)

    def is_keyword(self, value):
        """Checks for a keyword.

        If the given value is in one of the KEYWORDS_* dictionary
        it's considered a keyword. Otherwise, tokens.Name is returned.
        """
        val = value.upper()
        for kwdict in self._keywords:
            if val in kwdict:
                return kwdict[val], value
        else:
            return tokens.Name, value

    def get_tokens(self, text, encoding=None):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.

        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the initial stack (default: ``['root']``)
        """
        if isinstance(text, TextIOBase):
            text = text.read()

        if isinstance(text, str):
            pass
        elif isinstance(text, bytes):
            if encoding:
                text = text.decode(encoding)
            else:
                try:
                    text = text.decode("utf-8")
                except UnicodeDecodeError:
                    text = text.decode("unicode-escape")
        else:
            raise TypeError(
                "Expected text or file-like object, got {!r}".format(
                    type(text))
            )

        combined_re = self._combined_re
        actions = self._actions
        dollar_re = self._dollar_quote_re
        dollar_action = self._dollar_quote_action
        text_len = len(text)
        _PROCESS_AS_KEYWORD = keywords.PROCESS_AS_KEYWORD
        _TokenType = tokens._TokenType
        is_keyword = self.is_keyword
        pos = 0

        while pos < text_len:
            # Dollar-quoted strings: backreference pattern handled separately
            if dollar_re is not None and text[pos] == '$':
                m = dollar_re.match(text, pos)
                if m:
                    yield dollar_action, m.group(), pos
                    pos = m.end()
                    continue

            m = combined_re.match(text, pos)
            if m is None:
                yield tokens.Error, text[pos], pos
                pos += 1
                continue

            idx = int(m.lastgroup[1:])  # 'g12' -> 12
            action = actions[idx]
            value = m.group()

            if isinstance(action, _TokenType):
                yield action, value, pos
            elif action is _PROCESS_AS_KEYWORD:
                yield (*is_keyword(value), pos)

            pos = m.end()


def tokenize(sql, encoding=None):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 3-tuple stream
    of ``(token type, value, position)`` items.
    """
    return Lexer.get_default_instance().get_tokens(sql, encoding)
