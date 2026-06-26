import pandas as pd
from datasanity import audit_dataframe


def test_datasanity_detects_common_issues():
    df = pd.DataFrame({
        "patient_id": ["A", "A", "B", "C"],
        "age": [50, 121, -1, 60],
        "sex": ["Male", " male ", "F", "F"],
        "diagnosis_date": ["2024-01-01", "bad", "2024-03-01", None],
        "mostly_missing": [None, None, 1, None],
    })
    report = audit_dataframe(df)
    checks = {i.check for i in report.issues}
    assert "duplicate_ids" in checks
    assert "numeric_range" in checks
    assert "mixed_categories" in checks
    assert "invalid_dates" in checks
    assert "missingness" in checks
