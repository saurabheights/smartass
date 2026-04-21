import pytest

from smartass.core.plugin_interface import (
    BoolField,
    IntField,
    SchemaError,
    SecretField,
    SelectField,
    SettingsSchema,
    StringField,
)


def test_string_field_validates_type():
    f = StringField(key="city", label="City", default="Berlin")
    assert f.validate("Munich") == "Munich"
    with pytest.raises(SchemaError):
        f.validate(123)


def test_string_field_required():
    f = StringField(key="city", label="City", required=True)
    with pytest.raises(SchemaError, match="required"):
        f.validate("")


def test_int_field_bounds():
    f = IntField(key="poll", label="Poll", default=15, min=1, max=60)
    assert f.validate(30) == 30
    with pytest.raises(SchemaError, match="out of range"):
        f.validate(120)
    with pytest.raises(SchemaError, match="out of range"):
        f.validate(0)


def test_bool_field():
    f = BoolField(key="x", label="X", default=False)
    assert f.validate(True) is True
    with pytest.raises(SchemaError):
        f.validate("true")


def test_select_field_restricts_options():
    f = SelectField(key="units", label="Units", default="metric", options=("metric", "imperial"))
    assert f.validate("imperial") == "imperial"
    with pytest.raises(SchemaError, match="not in options"):
        f.validate("kelvin")


def test_secret_field_is_string_with_redacted_repr():
    f = SecretField(key="api_key", label="API Key")
    assert f.validate("s3cret") == "s3cret"
    assert "s3cret" not in repr(f)


def test_schema_validate_dict_returns_cleaned_values():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin"),
            IntField(key="poll", label="Poll", default=15, min=1, max=60),
        )
    )
    cleaned = schema.validate({"city": "Munich", "poll": 20})
    assert cleaned == {"city": "Munich", "poll": 20}


def test_schema_applies_defaults_for_missing():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin"),
            IntField(key="poll", label="Poll", default=15, min=1, max=60),
        )
    )
    cleaned = schema.validate({})
    assert cleaned == {"city": "Berlin", "poll": 15}


def test_schema_rejects_unknown_keys():
    schema = SettingsSchema(
        fields=(StringField(key="city", label="City", default="Berlin"),)
    )
    with pytest.raises(SchemaError, match="unknown field"):
        schema.validate({"city": "Munich", "trojan": "yes"})


def test_schema_to_json_serializable():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin", required=True),
            SelectField(key="units", label="Units", default="metric", options=("metric", "imperial")),
        )
    )
    data = schema.to_dict()
    assert data == {
        "fields": [
            {
                "type": "string",
                "key": "city",
                "label": "City",
                "default": "Berlin",
                "required": True,
                "description": "",
            },
            {
                "type": "select",
                "key": "units",
                "label": "Units",
                "default": "metric",
                "required": False,
                "description": "",
                "options": ["metric", "imperial"],
            },
        ]
    }
