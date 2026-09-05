from app.core.prompts import SYSTEM_PROMPT, build_problem_prompt


def test_build_problem_prompt_includes_system_prompt():
    prompt = build_problem_prompt("Some statement", "N <= 10^5")
    assert prompt.startswith(SYSTEM_PROMPT)
    assert "[PROBLEM STATEMENT]" in prompt
    assert "[CONSTRAINTS]" in prompt


def test_build_problem_prompt_embeds_statement_and_constraints():
    prompt = build_problem_prompt("Count paths in a grid.", "N, M <= 1000")
    assert "Count paths in a grid." in prompt
    assert "N, M <= 1000" in prompt


def test_build_problem_prompt_allows_empty_constraints():
    prompt = build_problem_prompt("Only a statement.")
    assert "[CONSTRAINTS]" in prompt