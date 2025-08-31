from src.main.tablebeautifier.utils.table_formatter import TableFormatter

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
        "```\n"
        "for i in range(10):\n"
        "    print(i)\n"
        "```\n"
    )
    f = TableFormatter()
    # is_table_like on a fenced code block should be false in most cases
    assert not f.is_table_like(text)
    processed, _ = f.process_all_inputs(text)
    assert processed == []


test_plain_text_is_not_detected_as_table()
test_code_block_should_not_trigger_detection()


