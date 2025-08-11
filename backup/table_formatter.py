import io
import re
import pandas as pd


class TableFormatter:
    ROW_COLUMN_NAMES = {"#", "row", "id"}  # case-insensitive match

    def __init__(self):
        pass

    def is_table_like(self, text: str) -> bool:
        """
        Quick heuristic to determine if text looks like a table.
        """
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            return False

        # Must contain a delimiter in most lines
        delimiter_patterns = [",", "\t", r"\|", ";", r"\s{2,}"]
        for pattern in delimiter_patterns:
            if sum(bool(re.search(pattern, line)) for line in lines) >= len(lines) // 2:
                return True
        return False

    def process_all_inputs(self, text: str):
        """
        Detect and process all tables from given text.
        Returns: (list of tuples: (context, csv_content, rows, cols), remaining_context)
        """
        tables = []
        remaining_context_parts = []
        current_table_lines = []
        current_context_parts = []

        lines = text.splitlines()
        for line in lines:
            if self._looks_like_table_line(line):
                current_table_lines.append(line)
            else:
                if current_table_lines:
                    # store the current table with its preceding context
                    tables.append(("\n".join(current_table_lines), "\n".join(current_context_parts)))
                    current_table_lines = []
                    current_context_parts = []
                current_context_parts.append(line)

        # If last block was a table
        if current_table_lines:
            tables.append(("\n".join(current_table_lines), "\n".join(current_context_parts)))
        else:
            # No table in last block — treat as trailing context
            remaining_context_parts.extend(current_context_parts)

        processed_tables = []
        for raw_table, ctx in tables:
            csv_str, rows, cols = self._clean_and_format_table(raw_table)
            processed_tables.append((ctx.strip(), csv_str, rows, cols))

        remaining_context = "\n".join(remaining_context_parts).strip()
        return processed_tables, remaining_context

    def _looks_like_table_line(self, line: str) -> bool:
        """
        Determines if a line appears to be part of a table.
        Uses stricter rules to avoid detecting normal sentences as tables.
        """
        line = line.strip()
        if not line:
            return False

        # Markdown-style full row: starts/ends with pipes
        if re.match(r"^\|.*\|$", line):
            # Require at least 2 cells after split
            parts = [p.strip() for p in line.strip("|").split("|")]
            return len([p for p in parts if p]) >= 2

        # Detect main delimiter candidates
        delimiters = [",", "\t", "|", ";"]
        for delim in delimiters:
            if line.count(delim) >= 2:  # Require at least 2 delimiters for safety
                # Split and check if at least 3 cells are non-empty
                parts = [p.strip() for p in re.split(rf"\s*{re.escape(delim)}\s*", line)]
                if len([p for p in parts if p]) >= 3:
                    return True

        # Detect multi-space separated columns
        if re.search(r"\s{2,}", line):
            parts = [p.strip() for p in re.split(r"\s{2,}", line)]
            return len([p for p in parts if p]) >= 3

        return False

    def _clean_and_format_table(self, raw_table: str):
        """
        Takes raw table text and outputs:
        - clean CSV string
        - number of rows
        - number of columns
        """
        # Remove Markdown table dividers
        lines = [
            line for line in raw_table.splitlines()
            if not re.match(r"^\s*\|?\s*:?-+:?\s*\|", line)
        ]

        # Strip leading/trailing pipes and spaces to avoid NaN columns
        lines = [re.sub(r'^\s*\|\s*', '', line) for line in lines]
        lines = [re.sub(r'\s*\|\s*$', '', line) for line in lines]

        table_text = "\n".join(lines)

        delimiter = self._detect_delimiter(table_text)
        df = pd.read_csv(
            io.StringIO(table_text),
            sep=delimiter,
            engine="python",
            header=None,
            skip_blank_lines=True
        )

        # If first row is header-like, set it as header
        if self._detect_header(df):
            df.columns = df.iloc[0].astype(str).str.strip()
            df = df.drop(df.index[0]).reset_index(drop=True)
        else:
            df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]

        # Detect if row index column exists
        if not self._has_row_index_column(df):
            df.insert(0, "Row", range(1, len(df) + 1))

        # Fill missing values
        df = df.fillna("")

        output = io.StringIO()
        df.to_csv(output, index=False)

        # Return CSV, row count, col count
        return output.getvalue().strip(), len(df), len(df.columns)

    def _detect_delimiter(self, text: str) -> str:
        """
        Detect delimiter from text.
        """
        if re.search(r"\|", text):
            return r"\|"
        elif re.search(r"\t", text):
            return "\t"
        elif re.search(r";", text):
            return ";"
        elif re.search(r"\s{2,}", text):
            return r"\s{2,}"
        else:
            return ","

    def _detect_header(self, df: pd.DataFrame) -> bool:
        """
        Detects if the first row is a header row.
        """
        if df.empty:
            return False
        first_row = df.iloc[0].tolist()
        string_like_count = sum(
            isinstance(v, str) and not v.strip().isdigit() and v.strip() != "" for v in first_row
        )
        return string_like_count >= len(first_row) / 2

    def _has_row_index_column(self, df: pd.DataFrame) -> bool:
        """
        Checks if a DataFrame already has a row/index column.
        """
        return any(str(col).strip().lower() in self.ROW_COLUMN_NAMES for col in df.columns)

    def format_as_text_table(self, df: pd.DataFrame) -> str:
        """
        Formats DataFrame as a plain text table (pretty print).
        """
        return df.to_markdown(index=False)
