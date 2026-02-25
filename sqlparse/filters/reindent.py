#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import sql, tokens as T
from sqlparse.utils import offset, indent


class ReindentFilter:
    def __init__(self, width=2, char=' ', wrap_after=0, n='\n',
                 comma_first=False, indent_after_first=False,
                 indent_columns=False, compact=False):
        self.n = n
        self.width = width
        self.char = char
        self.indent = 1 if indent_after_first else 0
        self.offset = 0
        self.wrap_after = wrap_after
        self.comma_first = comma_first
        self.indent_columns = indent_columns
        self.compact = compact
        self._curr_stmt = None
        self._last_stmt = None
        self._last_func = None

    def _reverse_leaves_before(self, target_leaf, known_parent_and_idx=None):
        """Yield leaf token values in reverse order before target_leaf."""
        current = target_leaf
        while current is not self._curr_stmt and current.parent is not None:
            parent = current.parent
            if known_parent_and_idx is not None \
                    and parent is known_parent_and_idx[0]:
                idx = known_parent_and_idx[1]
            else:
                try:
                    idx = parent.tokens.index(current)
                except ValueError:
                    break
            for i in range(idx - 1, -1, -1):
                sibling = parent.tokens[i]
                if sibling.is_group:
                    yield from self._reverse_flatten(sibling)
                else:
                    yield sibling.value
            current = parent

    def _reverse_flatten(self, token_list):
        """Yield all leaf token values in a TokenList in reverse order."""
        for i in range(len(token_list.tokens) - 1, -1, -1):
            child = token_list.tokens[i]
            if child.is_group:
                yield from self._reverse_flatten(child)
            else:
                yield child.value

    @property
    def leading_ws(self):
        return self.offset + self.indent * self.width

    def _get_offset(self, token, known_parent_and_idx=None):
        if token.is_group:
            token = next(token.flatten())

        column = 0
        for value in self._reverse_leaves_before(token, known_parent_and_idx):
            newline_pos = value.rfind('\n')
            if newline_pos != -1:
                column += len(value) - newline_pos - 1
                break
            column += len(value)

        return column - len(self.char * self.leading_ws)

    def nl(self, offset=0):
        return sql.Token(
            T.Whitespace,
            self.n + self.char * max(0, self.leading_ws + offset))

    def _next_token(self, tlist, idx=-1):
        split_words = ('FROM', 'STRAIGHT_JOIN$', 'JOIN$', 'AND', 'OR',
                       'GROUP BY', 'ORDER BY', 'UNION', 'VALUES',
                       'SET', 'BETWEEN', 'EXCEPT', 'HAVING', 'LIMIT')
        m_split = T.Keyword, split_words, True
        tidx, token = tlist.token_next_by(m=m_split, idx=idx)

        if token and token.normalized == 'BETWEEN':
            tidx, token = self._next_token(tlist, tidx)

            if token and token.normalized == 'AND':
                tidx, token = self._next_token(tlist, tidx)

        return tidx, token

    def _split_kwds(self, tlist):
        # Pass 1: scan unmodified list for all keyword positions
        inserts = {}   # idx -> token to insert before
        deletes = set()

        tidx, token = self._next_token(tlist)
        while token:
            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            uprev = str(prev_)

            if prev_ and prev_.is_whitespace:
                deletes.add(pidx)

            if not (uprev.endswith('\n') or uprev.endswith('\r')):
                inserts[tidx] = self.nl()

            tidx, token = self._next_token(tlist, tidx)

        # Pass 2: rebuild token list in O(n)
        if inserts or deletes:
            new_tokens = []
            for i, tok in enumerate(tlist.tokens):
                if i in inserts:
                    nl_tok = inserts[i]
                    nl_tok.parent = tlist
                    new_tokens.append(nl_tok)
                if i not in deletes:
                    new_tokens.append(tok)
            tlist.tokens = new_tokens

    def _split_statements(self, tlist):
        ttypes = T.Keyword.DML, T.Keyword.DDL
        inserts = {}
        deletes = set()

        tidx, token = tlist.token_next_by(t=ttypes)
        while token:
            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            if prev_ and prev_.is_whitespace:
                deletes.add(pidx)
            # only break if it's not the first token
            if prev_ is not None:
                inserts[tidx] = self.nl()
            tidx, token = tlist.token_next_by(t=ttypes, idx=tidx)

        if inserts or deletes:
            new_tokens = []
            for i, tok in enumerate(tlist.tokens):
                if i in inserts:
                    nl_tok = inserts[i]
                    nl_tok.parent = tlist
                    new_tokens.append(nl_tok)
                if i not in deletes:
                    new_tokens.append(tok)
            tlist.tokens = new_tokens

    def _process(self, tlist):
        func_name = f'_process_{type(tlist).__name__}'
        func = getattr(self, func_name.lower(), self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        tidx, token = tlist.token_next_by(m=(T.Keyword, 'WHERE'))
        if not token:
            return
        # issue121, errors in statement fixed??
        tlist.insert_before(tidx, self.nl())
        with indent(self):
            self._process_default(tlist)

    def _process_parenthesis(self, tlist):
        ttypes = T.Keyword.DML, T.Keyword.DDL
        _, is_dml_dll = tlist.token_next_by(t=ttypes)
        fidx, first = tlist.token_next_by(m=sql.Parenthesis.M_OPEN)
        if first is None:
            return

        with indent(self, 1 if is_dml_dll else 0):
            tlist.tokens.insert(0, self.nl()) if is_dml_dll else None
            with offset(self, self._get_offset(first) + 1):
                self._process_default(tlist, not is_dml_dll)

    def _process_function(self, tlist):
        self._last_func = tlist[0]
        self._process_default(tlist)

    def _process_identifierlist(self, tlist):
        identifiers = list(tlist.get_identifiers())
        if self.indent_columns:
            first = next(identifiers[0].flatten())
            num_offset = 1 if self.char == '\t' else self.width
        else:
            first = next(identifiers.pop(0).flatten())
            num_offset = 1 if self.char == '\t' else self._get_offset(first)

        if not tlist.within(sql.Function) and not tlist.within(sql.Values):
            # Build index mapping for O(1) lookups instead of O(n)
            # token_index calls
            token_to_idx = {id(t): i
                            for i, t in enumerate(tlist.tokens)}
            with offset(self, num_offset):
                position = 0
                shift = 0
                for token in identifiers:
                    # Add 1 for the "," separator
                    position += len(str(token)) + 1
                    if position > (self.wrap_after - self.offset):
                        adjust = 0
                        tidx = token_to_idx[id(token)] + shift
                        if self.comma_first:
                            adjust = -2
                            pidx, comma = tlist.token_prev(tidx)
                            if comma is None:
                                continue
                            tlist.insert_before(
                                pidx, self.nl(offset=adjust))
                            shift += 1
                            # comma is now at pidx + 1
                            _, ws = tlist.token_next(
                                pidx + 1, skip_ws=False)
                            if (ws is not None
                                    and ws.ttype is not
                                    T.Text.Whitespace):
                                tlist.insert_after(
                                    pidx + 1,
                                    sql.Token(T.Whitespace, ' '))
                                shift += 1
                        else:
                            tlist.insert_before(
                                tidx, self.nl(offset=adjust))
                            shift += 1
                        position = 0
        else:
            # ensure whitespace
            token_to_idx = {id(t): i
                            for i, t in enumerate(tlist.tokens)}
            ws_shift = 0
            for token in list(tlist.tokens):
                if token.value == ',':
                    adj_i = token_to_idx[id(token)] + ws_shift
                    _, next_ws = tlist.token_next(
                        adj_i, skip_ws=False)
                    if (next_ws is not None
                            and not next_ws.is_whitespace):
                        tlist.insert_after(
                            adj_i, sql.Token(T.Whitespace, ' '))
                        ws_shift += 1

            end_at = self.offset + sum(len(str(i)) + 1 for i in identifiers)
            adjusted_offset = 0
            if (self.wrap_after > 0
                    and end_at > (self.wrap_after - self.offset)
                    and self._last_func):
                adjusted_offset = -len(str(self._last_func)) - 1

            # Rebuild index mapping after whitespace insertions
            token_to_idx = {id(t): i
                            for i, t in enumerate(tlist.tokens)}
            with offset(self, adjusted_offset), indent(self):
                shift = 0
                if adjusted_offset < 0:
                    idx0 = token_to_idx[id(identifiers[0])] + shift
                    tlist.insert_before(idx0, self.nl())
                    shift += 1
                position = 0
                for token in identifiers:
                    # Add 1 for the "," separator
                    position += len(str(token)) + 1
                    if (self.wrap_after > 0
                            and position > (self.wrap_after - self.offset)):
                        tidx = token_to_idx[id(token)] + shift
                        tlist.insert_before(
                            tidx, self.nl(offset=0))
                        shift += 1
                        position = 0
        self._process_default(tlist)

    def _process_case(self, tlist):
        iterable = iter(tlist.get_cases())
        cond, _ = next(iterable)
        first = next(cond[0].flatten())

        with offset(self, self._get_offset(tlist[0])):
            with offset(self, self._get_offset(first)):
                for cond, value in iterable:
                    str_cond = ''.join(str(x) for x in cond or [])
                    str_value = ''.join(str(x) for x in value)
                    end_pos = self.offset + 1 + len(str_cond) + len(str_value)
                    if (not self.compact and end_pos > self.wrap_after):
                        token = value[0] if cond is None else cond[0]
                        tlist.insert_before(token, self.nl())

                # Line breaks on group level are done. let's add an offset of
                # len "when ", "then ", "else "
                with offset(self, len("WHEN ")):
                    self._process_default(tlist)
            end_idx, end = tlist.token_next_by(m=sql.Case.M_CLOSE)
            if end_idx is not None and not self.compact:
                tlist.insert_before(end_idx, self.nl())

    def _process_values(self, tlist):
        tlist.insert_before(0, self.nl())
        tidx, token = tlist.token_next_by(i=sql.Parenthesis)
        first_token = token

        if self.comma_first and first_token:
            cf_offset = self._get_offset(first_token) - 2

        while token:
            ptidx, ptoken = tlist.token_next_by(m=(T.Punctuation, ','),
                                                idx=tidx)
            if ptoken:
                if self.comma_first:
                    tlist.insert_before(ptidx, self.nl(cf_offset))
                else:
                    nl_offset = self._get_offset(
                        token, known_parent_and_idx=(tlist, tidx))
                    tlist.insert_after(ptidx, self.nl(nl_offset))
            tidx, token = tlist.token_next_by(i=sql.Parenthesis, idx=tidx)

    def _process_default(self, tlist, stmts=True):
        self._split_statements(tlist) if stmts else None
        self._split_kwds(tlist)
        for sgroup in tlist.get_sublists():
            self._process(sgroup)

    def process(self, stmt):
        self._curr_stmt = stmt
        self._process(stmt)

        if self._last_stmt is not None:
            nl = '\n' if str(self._last_stmt).endswith('\n') else '\n\n'
            stmt.tokens.insert(0, sql.Token(T.Whitespace, nl))

        self._last_stmt = stmt
        return stmt
