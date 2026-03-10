from uq_runtime.utils.sql_parser import is_sql_statement, split_sql_clauses


def test_sql_statement_recognizer_rejects_explanatory_prose():
    assert is_sql_statement("select all users from a database") is False
    assert is_sql_statement("SELECT is the command used to retrieve data") is False


def test_sql_statement_recognizer_accepts_literal_queries():
    assert is_sql_statement("SELECT email FROM users") is True
    assert is_sql_statement("SELECT COUNT(*) FROM users") is True
    assert is_sql_statement("UPDATE users SET active = true") is True
    assert is_sql_statement("DELETE FROM users WHERE active = false") is True
    assert is_sql_statement("INSERT INTO users (email) VALUES ('a@example.com')") is True


def test_split_sql_clauses_ignores_keywords_in_strings_and_comments():
    clauses = split_sql_clauses(
        "SELECT 'FROM users' AS note FROM users -- WHERE hidden = true\nWHERE active = true LIMIT 10"
    )

    assert [name for name, _text, _start, _end in clauses] == ["SELECT", "FROM", "WHERE", "LIMIT"]
    assert clauses[0][1] == "SELECT 'FROM users' AS note"
