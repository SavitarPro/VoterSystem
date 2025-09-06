import pytest
from models import validate_unique_id

def test_validate_unique_id_valid():
    valid_uuid = "1a348cc9-1f2a-47b6-951a-f9075f0c19ce"
    assert validate_unique_id(valid_uuid) is True

def test_validate_unique_id_invalid():
    invalid_uuid = "not-a-real-uuid"
    assert validate_unique_id(invalid_uuid) is False

def test_validate_unique_id_none():
    assert validate_unique_id(None) is False