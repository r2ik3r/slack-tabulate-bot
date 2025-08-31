# /src/main/tablebeautifier/utils/table_formatter.py

import io
import re
import pandas as pd
from typing import List, Tuple

# Keep pandas imports minimal; heavy lifting delegated to pandas efficiently.


class TableFormatter:
    """
    Robust, fast table detector + parser.

    Guarantees:
    - process_all_inputs(text) -> (List[(context, csv_str, rows, cols)], trailing_context)
    - is_table_like(text) -> quick, cheap heuristic
    - format_as_text_table(df) -> textual pretty table (used for mentions)
    """

    ROW_COLUMN_NAMES = {"#", "row", "id"}  # normalized lowercase check
    # compiled regexes for speed (used heavily)
    _md_divider_re = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
    _leading_pipe_re = re.compile(r"^\s*\|\s*")
    _trailing_pipe_re = re.compile(r"\s*\|\s*$")
    _codeblock_re = re.compile(r"^```|```$")  # to strip block fences
    _inline_code_re = re.compile(r"`([^`]*)`")  # inline code removal (optional)

    def __init__(self):
        # small internal config to tune safety/limits
        self._min_columns_for_detection = 3  # require >=3 non-empty cells on a line
        self._min_delims_for_detection = 2   # require >=2 delimiter occurrences on a line
        # precompute delimiter candidates
        self._delimiters = [",", "\t", ";", "|"]
        # precompile simple delimiter counting regex for speed
        self._multi_space_re = re.compile(r"\s{2,}")

    # -------------------------
    # Public quick-check
    # -------------------------
    def is_table_like(self, text: str) -> bool:
        if not text or not text.strip():
            return False

        t = text.strip()
        # If entire message is fenced code, only allow markdown pipe tables inside
        if t.startswith("```") and t.endswith("```"):
            inner = t[3:-3].strip()
            inner_lines = [ln for ln in inner.splitlines() if ln.strip()]
            if len(inner_lines) >= 2 and "|" in inner_lines and self._md_divider_re.match(inner_lines[4]):
                return True
            return False

        lines = [ln for ln in t.splitlines() if ln.strip()]
        if len(lines) < 2:
            return False

        # Fast path: markdown pipe table with header divider
        if "|" in lines and self._md_divider_re.match(lines[4]):
            return True

        sample = lines[:6]

        # Delimiter consistency across lines
        best_support = 0
        best_counts = []
        for delim in self._delimiters:
            counts = [ln.count(delim) for ln in sample]
            qualifying = [c for c in counts if c >= self._min_delims_for_detection]
            support = len(qualifying)
            if support > best_support:
                best_support = support
                best_counts = qualifying

        # Require at least 3 lines with repeated delimiter and similar counts
        if best_support >= 3:
            mn, mx = min(best_counts), max(best_counts)
            if mn > 0 and mx <= mn * 2:
                return True

        # Multi-space columns: at least two lines that each split into >=3 parts
        ms_lines = [ln for ln in sample if self._multi_space_re.search(ln)]
        if len(ms_lines) >= 2:
            ok = 0
            for ln in ms_lines:
                parts = [p.strip() for p in re.split(self._multi_space_re, ln)]
                if len([p for p in parts if p]) >= 3:
                    ok += 1
            if ok >= 2:
                return True

        return False

    # -------------------------
    # Main extractor (used by handlers)
    # -------------------------
    def process_all_inputs(self, text: str) -> Tuple[List[Tuple[str, str, int, int]], str]:
        if not text:
            return [], ""

        top_text = text
        stripped_top = top_text.strip()
        if stripped_top.startswith("```") and stripped_top.endswith("```"):
            top_text = stripped_top[3:-3]

        lines = top_text.splitlines()

        tables = []
        current_table_lines: List[str] = []
        current_context_lines: List[str] = []
        trailing_context_lines: List[str] = []

        for idx, raw_line in enumerate(lines):
            line = raw_line.rstrip("\n")
            if self._looks_like_table_line(line):
                current_table_lines.append(line)
            else:
                if current_table_lines:
                    tables.append(("\n".join(current_table_lines), "\n".join(current_context_lines)))
                    current_table_lines = []
                    current_context_lines = []
                current_context_lines.append(line)

        if current_table_lines:
            tables.append(("\n".join(current_table_lines), "\n".join(current_context_lines)))
        else:
            trailing_context_lines.extend(current_context_lines)

        processed_tables = []
        for raw_table, context_before in tables:
            try:
                csv_str, rows, cols = self._clean_and_format_table(raw_table)
                # Skip empty parses; treat as plain text context
                if not csv_str or rows == 0 or cols == 0:
                    trailing_context_lines.append(raw_table)
                    continue
                processed_tables.append((context_before.strip(), csv_str, rows, cols))
            except Exception:
                trailing_context_lines.append(raw_table)
                continue

        final_context = "\n".join(trailing_context_lines).strip()
        return processed_tables, final_context

    # -------------------------
    # Cheap line-level detector
    # -------------------------
    def _looks_like_table_line(self, line: str) -> bool:
        """
        Stricter, fast determination whether a single line is table-like.
        returns True for:
          - markdown pipe rows: must contain at least two non-empty cells
          - lines with repeated delimiter occurrences (>= min occurrences)
          - lines with multi-space column separators (>= min columns)
        """
        if not line or not line.strip():
            return False
        s = line.strip()

        # Markdown pipe-style row: require at least two non-empty cells
        if s.startswith("|") or "|" in s:
            # quick soldier: strip outer pipes then split
            inner = self._leading_pipe_re.sub("", s)
            inner = self._trailing_pipe_re.sub("", inner)
            parts = [p.strip() for p in inner.split("|")]
            return len([p for p in parts if p]) >= 2

        # delimiter-based detection
        for delim in self._delimiters:
            count = s.count(delim)
            if count >= self._min_delims_for_detection:
                # robust split that tolerates spaces
                parts = [p.strip() for p in re.split(rf"\s*{re.escape(delim)}\s*", s)]
                if len([p for p in parts if p]) >= self._min_columns_for_detection:
                    return True

        # multi-space columns
        if self._multi_space_re.search(s):
            parts = [p.strip() for p in re.split(self._multi_space_re, s)]
            if len([p for p in parts if p]) >= self._min_columns_for_detection:
                return True

        return False

    # -------------------------
    # Table parsing & cleaning
    # -------------------------
    def _clean_and_format_table(self, raw_table: str) -> Tuple[str, int, int]:
        """
        Parse a detected raw_table block and return (csv_string, row_count, col_count).
        This function is the single place pandas is invoked.
        """
        # remove inline code markers and triple backticks if present inside block
        block = raw_table.strip()
        # strip code fence markers (only those that wrap entire block rows)
        block = re.sub(r"^```", "", block)
        block = re.sub(r"```$", "", block)
        # remove inline backticks (preserve inner text)
        block = self._inline_code_re.sub(r"\1", block)

        lines = [ln for ln in block.splitlines() if ln is not None]

        # Remove markdown divider rows (|-----|)
        cleaned_lines = [ln for ln in lines if not self._md_divider_re.match(ln)]

        # Strip outer starting/trailing pipes for each line to avoid empty edge columns
        cleaned_lines = [self._leading_pipe_re.sub("", ln) for ln in cleaned_lines]
        cleaned_lines = [self._trailing_pipe_re.sub("", ln) for ln in cleaned_lines]

        # Reconstruct text for pandas
        table_text = "\n".join(cleaned_lines).strip()
        if not table_text:
            return "", 0, 0

        # Detect delimiter robustly using first non-empty line.
        delim = self._detect_delimiter(table_text)

        # Choose engine: use C engine when separator is a simple single-char (performance)
        engine = "c" if (delim in {",", "\t", ";"}) else "python"

        # Attempt to parse with header=None (we'll decide header-ness afterward)
        try:
            df = pd.read_csv(io.StringIO(table_text),
                             sep=delim,
                             engine=engine,
                             header=None,
                             skip_blank_lines=True,
                             skipinitialspace=True,
                             dtype=str)  # read as strings for safe header detection
        except Exception:
            # fall back to python engine for tricky cases
            df = pd.read_csv(io.StringIO(table_text),
                             sep=delim,
                             engine="python",
                             header=None,
                             skip_blank_lines=True,
                             skipinitialspace=True,
                             dtype=str)

        # Drop fully empty columns created by stray separators
        df.dropna(axis=1, how="all", inplace=True)
        if df.shape[1] == 0 or df.shape[0] == 0:
            return "", 0, 0

        # Decide if first row is header-like
        if self._first_row_looks_like_header(df.iloc[0].tolist()):
            # set header from first row and drop it
            header_values = [str(v).strip() for v in df.iloc[0].tolist()]
            # fill blank header names with Column_n
            header_values = [h if h else f"Column_{i+1}" for i, h in enumerate(header_values)]
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = header_values
        else:
            # no header — synthesize Column_1..Column_n
            df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]

        # After header handling, drop any fully-empty columns again
        df.dropna(axis=1, how="all", inplace=True)

        # Detect existing row/index column (name or sequential numeric series)
        if not self._has_row_index_column(df):
            # insert Row column at front
            df.insert(0, "Row", range(1, len(df) + 1))
        else:
            # Normalize index column name if the user used 'Row' variants
            # (No action necessary; we keep existing column as-is)
            pass

        # Convert numeric-like columns where safe (strip thousand separators)
        for col in df.columns:
            # keep as string if the column contains unicode textual characters like Hindi or symbols
            try:
                # strip commas inside numbers and attempt numeric conversion
                cleaned = df[col].astype(str).str.strip().replace({"": pd.NA})
                # if many cells contain digits with commas, remove commas for conversion
                if cleaned.str.contains(r"\d,\d").any():
                    candidate = cleaned.str_replace(",", "", regex=True) if hasattr(cleaned, "str_replace") else cleaned.str.replace(",", "", regex=True)
                else:
                    candidate = cleaned
                numeric = pd.to_numeric(candidate, errors="coerce")
                # if a majority of non-empty cells converted to numeric, replace
                non_na = numeric.notna().sum()
                non_empty = cleaned.notna().sum()
                if non_empty > 0 and (non_na / non_empty) >= 0.6:
                    df[col] = numeric
                else:
                    df[col] = cleaned.fillna("")
            except Exception:
                # leave column as strings
                df[col] = df[col].astype(str).fillna("")

        # Final cleanup: drop columns that are still entirely empty
        df.dropna(axis=1, how="all", inplace=True)

        # Build CSV string with thousands separators for numeric columns
        df_out = df.copy()
        for col in df_out.columns:
            s = df_out[col]
            # Format floats with grouping and preserve decimals; ints as grouped
            if pd.api.types.is_integer_dtype(s):
                df_out[col] = s.map(lambda v: f"{int(v):,}" if pd.notna(v) else "")
            elif pd.api.types.is_float_dtype(s):
                df_out[col] = s.map(lambda v: f"{float(v):,}" if pd.notna(v) else "")
            else:
                # Attempt to coerce objects that are mostly numeric back to numbers for formatting
                try:
                    numeric = pd.to_numeric(s, errors="coerce")
                    non_na = numeric.notna().sum()
                    non_empty = s.astype(str).str.strip().replace({"": pd.NA}).notna().sum()
                    if non_empty > 0 and (non_na / non_empty) >= 0.6:
                        # Decide int vs float presentation by checking fractional part
                        if (numeric.dropna() % 1 == 0).all():
                            df_out[col] = numeric.map(lambda v: f"{int(v):,}" if pd.notna(v) else "")
                        else:
                            df_out[col] = numeric.map(lambda v: f"{float(v):,}" if pd.notna(v) else "")
                except Exception:
                    pass

        out = io.StringIO()
        df_out.to_csv(out, index=False)
        csv_str = out.getvalue().rstrip("\n")


        rows = len(df)
        cols = len(df.columns)
        return csv_str, rows, cols

    # -------------------------
    # Helpers
    # -------------------------
    def _detect_delimiter(self, text: str) -> str:
        non_empty = [ln.strip() for ln in text.splitlines() if ln.strip()]
        head = non_empty[:5] if non_empty else []
        if not head:
            return ","

        totals = {d: 0 for d in self._delimiters}
        for ln in head:
            for d in self._delimiters:
                totals[d] += ln.count(d)

        # If multi-space is present and no delimiter is prominent, use multi-space
        if any(self._multi_space_re.search(ln) for ln in head) and max(totals.values()) < 2:
            return r"\s{2,}"

        # Prefer tab, pipe, semicolon, then comma on ties
        preference = ["\t", "|", ";", ","]
        best = max(self._delimiters, key=lambda d: (totals[d], preference.index(d)))
        return best if totals[best] >= 1 else ","

    def _first_row_looks_like_header(self, first_row_values: List[str]) -> bool:
        """
        Decide if the first parsed row is a header row (mostly text) or data (mostly numeric/boolean).
        Conservative: require a majority of cells look non-numeric and non-empty.

        Change: treat a token as header-like only if it contains letters and does NOT contain digits.
        This avoids misclassifying identifiers like 'alpha-01' or mixed alnum codes as headers.
        """
        if not first_row_values:
            return False
        text_like = 0
        total = 0
        for v in first_row_values:
            s = str(v).strip()
            if s == "" or s.lower() in {"nan", "null"}:
                # blank cell — don't count
                continue
            total += 1

            has_letters = bool(re.search(r"[A-Za-z\u00C0-\u017F]", s))
            has_digits = bool(re.search(r"\d", s))

            # header-like if it has letters and no digits (e.g. "Product", "City", "Last Login")
            if has_letters and not has_digits:
                text_like += 1
            else:
                # also consider punctuation-only tokens (rare headers like "%", "€") as header-like if they
                # contain non-alphanumeric characters but no digits
                if not has_digits and re.search(r"[^\w\s]", s):
                    text_like += 1

        if total == 0:
            return False
        return (text_like / total) >= 0.5

    def _has_row_index_column(self, df: pd.DataFrame) -> bool:
        """
        Detect if the first column is an existing row/index column.
        Checks:
          - header name in ROW_COLUMN_NAMES (case-insensitive)
          - or first column values form a strict 1..n sequence (even if strings)
        """
        if df is None or df.shape[1] == 0:
            return False

        first_col_name = str(df.columns[0]).strip().lower()
        if first_col_name in self.ROW_COLUMN_NAMES:
            return True

        # try to coerce first column to ints and see if it forms 1..n
        try:
            cleaned = df.iloc[:, 0].astype(str).str.strip()
            numeric = pd.to_numeric(cleaned.str.replace(",", ""), errors="coerce").dropna().astype(int)
            if len(numeric) >= 1:
                seq = list(range(1, len(numeric) + 1))
                # consider it an index if they match exactly for non-null prefix
                if list(numeric) == seq[: len(numeric)]:
                    return True
        except Exception:
            pass

        return False

    def format_as_text_table(self, df: pd.DataFrame) -> str:
        """
        Simple textual representation for app_mention flow.
        Keep it minimal; callers supply DataFrame created from process_all_inputs csv.
        """
        try:
            return df.to_markdown(index=False)
        except Exception:
            return df.to_string(index=False)
