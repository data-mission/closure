"""Generation fixtures (0001): schema validation + model-identity halt.

generate.py is provider-agnostic (a generate callable is injected). A row whose provider-
reported model id differs from the pin halts the run (the model-identity guard). The schema
validator rejects malformed structured output.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from closure_harness.config import CONFIG
from closure_harness.generate import ModelIdentityError, generate_row
from closure_harness.schema import parse_output


@dataclass
class FakeResponse:
    output: dict
    model: str


VALID = {
    "claims": [{"id": 1, "text": "a claim", "source_ids": [0]}],
    "conclusion": "a conclusion",
}


def test_valid_row_parses_and_records_model():
    def gen(prompt):
        return FakeResponse(output=VALID, model=CONFIG.generation.model_pin)

    row = generate_row(gen, "prompt")
    assert row.reported_model == CONFIG.generation.model_pin
    assert row.output.conclusion == "a conclusion"
    assert row.output.claims[0].source_ids == (0,)


def test_spoofed_model_halts():
    def gen(prompt):
        return FakeResponse(output=VALID, model="some-other-model")

    with pytest.raises(ModelIdentityError):
        generate_row(gen, "prompt")


def test_missing_model_halts():
    @dataclass
    class NoModel:
        output: dict

    def gen(prompt):
        return NoModel(output=VALID)

    with pytest.raises(ModelIdentityError):
        generate_row(gen, "prompt")


def test_schema_rejects_bad_rows():
    bad_cases = [
        {"claims": [], "conclusion": 5},  # non-str conclusion
        {"claims": "nope", "conclusion": "c"},  # claims not a list
        {"claims": [{"id": "x", "text": "t", "source_ids": [0]}], "conclusion": "c"},  # id not int
        {"claims": [{"id": 1, "text": 2, "source_ids": [0]}], "conclusion": "c"},  # text not str
        {"claims": [{"id": 1, "text": "t", "source_ids": ["0"]}], "conclusion": "c"},  # sids not int
        {"claims": [{"id": 1, "text": "t", "source_ids": [0]}]},  # missing conclusion
        {"claims": [{"id": 1, "text": "t", "source_ids": [0], "extra": 1}], "conclusion": "c"},  # extra key
        {"claims": [{"id": 1, "text": "a"}, {"id": 1, "text": "b"}], "conclusion": "c"},  # dup id
    ]
    for case in bad_cases:
        with pytest.raises(ValueError):
            parse_output(case)


def test_schema_defaults_missing_source_ids_to_empty():
    out = parse_output({"claims": [{"id": 1, "text": "t"}], "conclusion": "c"})
    assert out.claims[0].source_ids == ()
