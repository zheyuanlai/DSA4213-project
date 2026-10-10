"""Deterministic evidence store and tool behaviour."""
import json

from src.tools import (
    NO_TEST_MSG, TOOL_SCHEMAS, compare_numbers, execute_tool, get_test_metadata, lookup_table, observation_to_message,
    retrieve_passage,
)


def test_evidence_ids(store):
    for eid in ["T1", "T1.r1", "T1.r1.acc", "T1.r2.wer", "S1", "P1", "P2", "exp1/cmp1", "exp1/cmp2"]:
        assert store.has(eid), eid
    assert store.get("T1.r1.acc").value == 83.7
    assert store.get("T1.r1.acc").spread == 1.2
    assert store.get("T1.r1.wer").higher_is_better is False
    assert not store.has("T1.r9.acc")


def test_lookup_whole_row_column(store):
    o = lookup_table(store, "T1")
    assert o.status == "FOUND" and len(o.data["cells"]) == 6
    o = lookup_table(store, "T1", row_id="r2")
    assert {c["evidence_id"] for c in o.data["cells"]} == {"T1.r2.wer", "T1.r2.acc", "T1.r2.lat"}
    o = lookup_table(store, "T1", column="Accuracy (%)")  # header match
    assert [c["value"] for c in o.data["cells"]] == [83.7, 82.9]
    o = lookup_table(store, "T1", row_id="r1", column="acc")
    assert o.returned_ids == ["T1", "T1.r1.acc"] and o.data["cells"][0]["text"] == "83.7 ± 1.2"


def test_lookup_not_found(store):
    assert lookup_table(store, "T9").status == "NOT_FOUND"
    o = lookup_table(store, "T1", row_id="r7")
    assert o.status == "NOT_FOUND" and "r1=Ours" in o.message
    assert lookup_table(store, "T1", column="bleu").status == "NOT_FOUND"


def test_test_metadata_found_absent_unknown(store):
    o = get_test_metadata(store, "exp1", "cmp1")
    assert o.status == "FOUND" and o.returned_ids == ["S1"] and o.data["tests"][0]["p_value"] == 0.0137
    o = get_test_metadata(store, "exp1", "cmp2")
    assert o.status == "NOT_FOUND" and o.returned_ids == ["absent:test:exp1/cmp2"] and o.message == NO_TEST_MSG
    o = get_test_metadata(store, "exp9", "cmp1")
    assert o.status == "NOT_FOUND" and o.returned_ids == []


def test_retrieve_passage(store):
    assert retrieve_passage(store, "P2").returned_ids == ["P2"]
    assert retrieve_passage(store, "Okafor").returned_ids == ["P1"]
    o = retrieve_passage(store, "label noise accuracy degradation")
    assert o.status == "FOUND" and o.returned_ids[0] == "P2"
    o = retrieve_passage(store, "zzzz qqqq")
    assert o.status == "NOT_FOUND" and o.returned_ids == ["absent:passage"]


def test_compare_numbers_value_and_tolerance(store):
    o = compare_numbers(store, 83.7, "T1.r1.acc")
    assert o.data["match"] is True and o.data["tolerance"] == 0.05
    assert compare_numbers(store, 83.8, "T1.r1.acc").data["match"] is False
    assert compare_numbers(store, "83.7%", "T1.r1.acc").data["match"] is True


def test_compare_numbers_difference_direction(store):
    o = compare_numbers(store, 0.8, "T1.r1.acc", "T1.r2.acc", mode="difference")
    assert o.data["match"] is True and o.data["better_entry"] == "T1.r1.acc"
    # lower-is-better: Ours has lower WER -> Ours is better even though the difference is negative
    o = compare_numbers(store, 1.5, "T1.r1.wer", "T1.r2.wer", mode="difference")
    assert o.data["match"] is False and o.data["sign_mismatch"] is True and o.data["better_entry"] == "T1.r1.wer"
    o = compare_numbers(store, -16.9, "T1.r1.wer", "T1.r2.wer", mode="percent_change")
    assert o.data["match"] is True


def test_compare_numbers_errors(store):
    assert compare_numbers(store, "abc", "T1.r1.acc").status == "TOOL_ERROR"
    assert compare_numbers(store, 1, "T1.r2.lat").status == "NOT_APPLICABLE"  # 'n/a' cell has no value
    assert compare_numbers(store, 1, "S1").status == "NOT_APPLICABLE"
    assert compare_numbers(store, 1, "T1.r1.acc", mode="difference").status == "TOOL_ERROR"
    assert compare_numbers(store, 1, "nope").status == "NOT_FOUND"
    # does not convert truth into the model's estimate
    o = compare_numbers(store, 99.0, "T1.r1.acc")
    assert o.data["actual"] == 83.7


def test_execute_tool_validation(store):
    o = execute_tool(store, "lookup_table", {}, "c1")
    assert o.status == "TOOL_ERROR" and "missing" in o.message and o.call_id == "c1"
    o = execute_tool(store, "lookup_table", {"table_id": "T1", "foo": 1}, "c2")
    assert o.status == "FOUND" and "ignored unknown args" in o.message
    assert execute_tool(store, "rm_rf", {}, "c3").status == "TOOL_ERROR"
    assert execute_tool(store, "lookup_table", "notadict", "c4").status == "TOOL_ERROR"
    msg = json.loads(observation_to_message(execute_tool(store, "get_test_metadata",
                                                         {"experiment_id": "exp1", "comparison_id": "cmp2"}, "c5")))
    assert msg["citable_ids"] == ["absent:test:exp1/cmp2"]


def test_tool_schemas_wellformed():
    for name, s in TOOL_SCHEMAS.items():
        assert s["type"] == "function" and s["function"]["name"] == name
        assert set(s["function"]["parameters"]["required"]) <= set(s["function"]["parameters"]["properties"])
