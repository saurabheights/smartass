import pytest

from smartass.core.manifest import Manifest, ManifestError, load_manifest


def test_load_valid_manifest(tmp_path):
    plugin_dir = tmp_path / "weather"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "Weather"
version = "0.1.0"
api_version = 1
description = "Forecast"
author = "Saurabh Khanduja"
entry = "plugin:WeatherPlugin"
icon = "weather-clear-symbolic"
permissions = ["net.http"]
"""
    )
    m = load_manifest(plugin_dir)
    assert isinstance(m, Manifest)
    assert m.id == "weather"
    assert m.name == "Weather"
    assert m.version == "0.1.0"
    assert m.api_version == 1
    assert m.entry_module == "plugin"
    assert m.entry_class == "WeatherPlugin"
    assert m.permissions == frozenset({"net.http"})
    assert m.root == plugin_dir


def test_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError, match="manifest.toml not found"):
        load_manifest(tmp_path)


def test_missing_required_field(tmp_path):
    plugin_dir = tmp_path / "x"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text("[plugin]\nid = \"x\"\n")
    with pytest.raises(ManifestError, match="missing required field"):
        load_manifest(plugin_dir)


def test_unknown_permission_rejected(tmp_path):
    plugin_dir = tmp_path / "x"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text(
        """
[plugin]
id = "x"
name = "X"
version = "0.1.0"
api_version = 1
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = ["net.evil"]
"""
    )
    with pytest.raises(ManifestError, match="unknown permission"):
        load_manifest(plugin_dir)


def test_id_must_match_dir_name(tmp_path):
    plugin_dir = tmp_path / "clipboard"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "X"
version = "0.1.0"
api_version = 1
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = []
"""
    )
    with pytest.raises(ManifestError, match="id 'weather' does not match directory 'clipboard'"):
        load_manifest(plugin_dir)


def test_api_version_mismatch_rejected(tmp_path):
    plugin_dir = tmp_path / "weather"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "Weather"
version = "0.1.0"
api_version = 99
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = []
"""
    )
    with pytest.raises(ManifestError, match="incompatible api_version"):
        load_manifest(plugin_dir)
