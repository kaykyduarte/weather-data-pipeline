from src.json_validator import JSONValidator


def test_validate_json_returns_passed_for_valid_batch() -> None:
    schema = {
        "id": int,
        "name": str,
        "temperature_c": (int, float),
    }
    records = [
        {"id": 1, "name": "A", "temperature_c": 25.5},
        {"id": 2, "name": "b", "temperature_c": 22},
    ]
    validator = JSONValidator(schema)

    report = validator.validate_json(records)

    assert report["passed"] is True
    assert report["invalid_records"] == 0
    assert report["issues"] == []


def test_validate_json_records_missing_field() -> None:
    schema = {
        "id": int,
        "name": str,
    }
    records = [
        {"id": 1},
    ]
    validator = JSONValidator(schema)

    report = validator.validate_json(records)

    assert report["passed"] is False
    assert report["invalid_records"] == 1
    assert len(report["issues"]) == 1
    assert report["issues"][0]["category"] == "missing_field"


def test_validate_json_reports_null_value() -> None:
    schema = {
        "id": int,
        "name": str,
    }
    records = [
        {"id": 1, "name": None},
    ]
    validator = JSONValidator(schema)
    
    report = validator.validate_json(records)

    assert report["passed"] is False
    assert report["invalid_records"] == 1
    assert len(report["issues"]) == 1
    assert report["issues"][0]["category"] == "null_value"


def test_validate_json_reports_invalid_type_for_bool_when_expect_int() -> None:
    schema = {
            "id": int,
    }
    records = [
        {"id": True},
    ]
    validator = JSONValidator(schema)

    report = validator.validate_json(records)

    assert report["passed"] is False
    assert report["invalid_records"] == 1
    assert len(report["issues"]) == 1
    assert report["issues"][0]["category"] == "invalid_type"


def test_validate_json_reports_empty_batch() -> None:
    schema = {
            "id": int,
            "name": str,
    }
    records = []
    validator = JSONValidator(schema)

    report = validator.validate_json(records)

    assert report["passed"] is False
    assert report["total_records"] == 0
    assert report["invalid_records"] == 0
    assert len(report["issues"]) == 1
    assert report["issues"][0]["category"] == "empty_batch"


def test_validate_json_reports_two_issues_for_one_invalid_record() -> None:
    schema = {
            "id": int,
            "name": str,
    }
    records = [
        {"id": "abc"},
    ]
    validator = JSONValidator(schema)

    report = validator.validate_json(records)   
    categories = {issue["category"] for issue in report["issues"]}

    assert report["passed"] is False
    assert report["invalid_records"] == 1
    assert len(report["issues"]) == 2
    assert "missing_field" in categories
    assert "invalid_type" in categories

def test_validate_json_accepts_bool_when_schema_explicitly_allows_bool() -> None: 
    schema = {
        "flag": (int, bool),      
    }
    records = [
        {"flag": True},
    ]
    validator = JSONValidator(schema)

    report = validator.validate_json(records)

    assert report["passed"] is True
    assert report["invalid_records"] == 0
    assert report["issues"] == []