import io
import os
import random
import string

import pandas as pd

from src.main.tablebeautifier.utils.table_formatter import TableFormatter


def _csv_to_df(csv_str: str) -> pd.DataFrame:
    if not csv_str:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(csv_str))


def test_detects_basic_csv_and_adds_index_and_columns():
    text = (
        "Product,Category,Price,In Stock,Rating\n"
        '"Laptop, Pro",Electronics,1200.00,Yes,4.5\n'
        '"Wireless Mouse",Accessories,25.50,Yes,4.8\n'
    )
    f = TableFormatter()
    processed, final_ctx = f.process_all_inputs(text)
    assert final_ctx == ""
    assert len(processed) == 1
    ctx, csv_str, rows, cols = processed[0]
    assert ctx == ""
    df = _csv_to_df(csv_str)
    # Index + 5 columns
    assert list(df.columns)[0] == "Index"
    assert rows == len(df)
    assert cols == len(df.columns)


def test_detects_tsv_and_preserves_context_order():
    text = (
        "Hello, please find the data below\n"
        "Today's data\n"
        "Employee ID\tFirst Name\tLast Name\tDepartment\tHire Date\n"
        "101\tAnika\tSharma\tEngineering\t2022-08-15\n"
        "102\tBen\tCarter\tSales\t2021-11-20\n"
        "Thanks!\n"
    )
    f = TableFormatter()
    processed, final_ctx = f.process_all_inputs(text)
    assert len(processed) == 1
    ctx, csv_str, rows, cols = processed[0]
    assert "Hello, please find the data below" in ctx
    assert "Today's data" in ctx
    assert final_ctx.strip() == "Thanks!"
    df = _csv_to_df(csv_str)
    assert "Index" in df.columns


def test_semicolon_csv_headerless_creates_Column_names():
    text = (
        "alpha-01;150;true\n"
        "beta-05;2300;true\n"
        "gamma-12;85;false\n"
    )
    f = TableFormatter()
    processed, _ = f.process_all_inputs(text)
    assert len(processed) == 1
    _, csv_str, _, _ = processed[0]
    df = _csv_to_df(csv_str)
    assert list(df.columns)[0] == "Index"
    # headerless -> Column1..ColumnN
    assert "Column1" in df.columns and "Column2" in df.columns and "Column3" in df.columns


def test_pipe_markdown_table():
    text = (
        "| User ID | Username | Role | Last Login |\n"
        "|---------|----------|------|------------|\n"
        "| usr_01 | alice_j | Admin | 2025-08-01 |\n"
        "| usr_02 | bob_smith | Editor | 2025-08-03 |\n"
    )
    f = TableFormatter()
    processed, _ = f.process_all_inputs(text)
    assert len(processed) == 1
    _, csv_str, rows, cols = processed[0]
    assert rows == 2
    df = _csv_to_df(csv_str)
    assert "Index" in df.columns
    assert {"User ID", "Username", "Role", "Last Login"}.issubset(set(df.columns))


def test_mixed_multispace_delim_and_thousands():
    text = (
        "exchange_name  requestsWithInvalidViewability  requestsWithValidViewability  requests\n"
        "adx   -    62,336,048   62,336,048\n"
        "pubmatic  132,813   164,118,605   164,251,418\n"
    )
    f = TableFormatter()
    processed, _ = f.process_all_inputs(text)
    assert len(processed) == 1
    _, csv_str, _, _ = processed[0]
    df = _csv_to_df(csv_str)
    assert "Index" in df.columns
    assert "requests" in df.columns


def test_avoid_false_positive_on_normal_text():
    text = (
        "Hello team, this is not a table. Commas, words, etc.\n"
        "Another line of plain text without consistent delimiters.\n"
    )
    f = TableFormatter()
    processed, final_ctx = f.process_all_inputs(text)
    # No tables; everything is trailing context
    assert processed == []
    assert "Hello team" in final_ctx


def test_large_csv_parsing_is_supported_rows_and_cols():
    # build a 300x50 CSV
    rows = 300
    cols = 50
    header = ",".join([f"C{i+1}" for i in range(cols)])
    lines = [header]
    for r in range(rows):
        vals = [str((r+1)*(i+1)) for i in range(cols)]
        lines.append(",".join(vals))
    text = "\n".join(lines)

    f = TableFormatter()
    processed, _ = f.process_all_inputs(text)
    assert len(processed) == 1
    _, csv_str, out_rows, out_cols = processed[0]
    assert out_rows == rows  # number of data rows remains
    assert out_cols == cols + 1  # plus Index column


