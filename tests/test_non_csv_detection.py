from tabulate.utils.table_formatter import TableFormatter


def test_plain_text_is_not_detected_as_table():
    text = (
        "Hello there, this message contains commas, periods, and numbers like 1, 2, 3,"
        " but it is not structured as a table.\n"
        "Please do not convert this into a CSV snippet.\n"
    )
    f = TableFormatter()
    processed, final_ctx = f.process_all_inputs(text)
    assert processed == []
    assert "Please do not convert" in final_ctx


def test_code_block_should_not_trigger_detection():
    text = (
        "```"
        "for i in range(10):\n"
        "    print(i)\n"
        "```\n"
    )
    f = TableFormatter()
    assert not f.is_table_like(text)
    processed, _ = f.process_all_inputs(text)
    assert processed == []


def test_prose_with_commas_is_not_detected():
    text = (
        "This is a sentence, with several commas, and numbers 1, 2, 3, but no table.\n"
        "Another sentence follows, still no consistent column structure.\n"
        "Final line without delimiters.\n"
    )
    f = TableFormatter()
    assert not f.is_table_like(text)
    processed, final_ctx = f.process_all_inputs(text)
    assert processed == []
    assert "Final line" in final_ctx


def test_small_valid_csv_detects_fast_and_correctly():
    text = (
        "A,B,C\n"
        "1,2,3\n"
        "4,5,6\n"
    )
    f = TableFormatter()
    assert f.is_table_like(text)
    processed, _ = f.process_all_inputs(text)
    assert len(processed) == 1
    _, csv_str, rows, cols = processed
    # Row column + 3 data columns
    assert rows == 2
    assert cols == 4
