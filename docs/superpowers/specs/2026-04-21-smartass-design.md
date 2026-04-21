# Smartass — Design Spec

- Date: 2026-04-21
- Author: Saurabh Khanduja
- Status: Approved (brainstorm phase); implementation plan to follow

## 1. Summary

A desktop smart-assistant app for Ubuntu. Installed via `apt` from a `.deb`,
runs as a user-session daemon + a tray client. Icon lives in the GNOME Shell
top panel (via AppIndicator). Clicking the tray icon toggles a window with
tabs: a **Settings** tab is always visible; each **enabled plugin** contributes
a tab. Plugins are dropped into a directory and discovered at startup.

MVP ships: the app scaffold, the `PluginInterface` abstract contract, and a
**Weather** plugin (Open-Meteo, user-typed city, 7-day forecast). The design
also describes (but does not yet implement): **QuickNotes**, **ClipboardHistory**,
**LLMChat**, **PluginBuilderUsingAI**.

## 2. High-Level Architecture

Three processes, one session D-Bus:

```
┌─────────────────────────────────┐
│  GNOME Shell top bar (tray)     │
│      🤖  smartass-tray icon     │
└───────────────┬─────────────────┘
                │ left-click toggles window
                ▼
┌─────────────────────────────────┐
│  smartass-tray  (Qt6 / PySide6) │
│  - QSystemTrayIcon              │
│  - Main window (QTabWidget)     │
│  - Settings tab (always on)     │
│  - One tab per enabled plugin   │
└───────────────┬─────────────────┘
                │ D-Bus session: ai.talonic.Smartass
                ▼
┌─────────────────────────────────┐
│  smartass-daemon (systemd user) │
│  - PluginManager                │
│  - ConfigStore (TOML)           │
│  - D-Bus Core service           │
│  - Per-plugin SQLite dirs       │
│                                 │
│  ┌─ Plugin (in-proc) ────────┐  │
│  │ Weather / QuickNotes / ...│  │
│  │ implements PluginInterface│  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 2.1 Lifecycle

- **Daemon** — `smartass-daemon.service` (systemd *user* unit) starts on login.
  Owns D-Bus name `ai.talonic.Smartass`. Hosts plugins and their background work.
- **Tray** — `smartass-tray.desktop` in `/etc/xdg/autostart/` launches the
  Qt6 tray after GNOME Shell is up. Connects to the daemon via D-Bus. If the
  daemon is not running, the tray runs `systemctl --user start smartass-daemon`
  and waits for the well-known name to appear.
- **Main window** — hidden by default; only the tray icon shows. Left-click
  toggles the window. Right-click menu: **Show**, **Quit tray**,
  **Restart daemon**.

### 2.2 Why split

Plugins do background work without the window open (Weather polling,
ClipboardHistory watching, LLMChat streaming). A tray-process crash must not
lose in-flight work; a daemon crash must not kill the tray (tray shows
"daemon offline", offers retry). This matches the decision in Q1 (option B).

### 2.3 Robot icon

A bundled SVG line-art robot face: `assets/icons/smartass.svg`. Installed as a
themed icon at
`/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg` so GNOME
shows it in both the top bar and app launcher.

### 2.4 Target Python

`>=3.10` (Ubuntu 22.04 ships 3.10, 24.04 ships 3.12). `pyproject.toml`'s
current `>=3.9` is raised to `>=3.10`.

## 3. `PluginInterface` Contract

A plugin is a directory:

```
<plugin_root>/<id>/
    manifest.toml
    plugin.py           # module declared in manifest `entry`
    ui.py               # optional; typically defines the tab widget
    <any private modules, assets>
```

Where `<plugin_root>` is one of:

- `/usr/share/smartass/plugins/` (system, bundled by the .deb)
- `~/.local/share/smartass/plugins/` (user-installed via Settings tab)

### 3.1 `manifest.toml`

```toml
[plugin]
id            = "weather"                # unique, matches directory name
name          = "Weather"                # display name (tab title)
version       = "0.1.0"
api_version   = 1                        # PluginInterface contract version
description   = "Current conditions + 7-day forecast"
author        = "Saurabh Khanduja"
entry         = "plugin:WeatherPlugin"   # "<module>:<class>"
icon          = "weather-clear-symbolic" # themed icon name or bundled path
permissions   = ["net.http"]             # net.http, fs.data, clipboard, ipc.dbus
```

### 3.2 Abstract class (sketch)

```python
class PluginInterface(ABC):
    id: str                              # set by loader from manifest
    api_version: ClassVar[int] = 1

    def __init__(self, ctx: "PluginContext") -> None:
        self.ctx = ctx

    # --- Lifecycle (daemon side only) ---
    def on_load(self) -> None: ...       # sync init; open DB, read config
    async def on_start(self) -> None: ...# begin background work
    async def on_stop(self) -> None: ... # stop tasks; flush
    def on_unload(self) -> None: ...     # release resources

    # --- UI side (tray process only) ---
    @abstractmethod
    def build_tab(self, parent: "QWidget") -> "QWidget": ...

    # --- Settings (both sides) ---
    @abstractmethod
    def settings_schema(self) -> "SettingsSchema": ...
    def on_settings_changed(self, new: dict) -> None: ...

    # --- Import/export ---
    def export_state(self) -> dict: ...  # default {}, opt-in portable state
    def import_state(self, data: dict) -> None: ...

    # --- D-Bus (optional plugin-specific surface) ---
    def dbus_interface(self) -> Optional[type]:
        return None
```

### 3.3 `PluginContext`

Host-provided, per-side:

- `config: PluginConfig` — typed getter/setter for this plugin's TOML section
- `data_dir: Path` — `~/.local/share/smartass/plugin_data/<id>/`
- `log: logging.Logger`
- `http: AsyncHttpClient | None` — present iff `net.http` permission granted
- `bus: SessionBus | None` — present iff `ipc.dbus` permission granted
- `signals: Signals` — `settings_changed`, `export_requested`, `enabled_changed`

### 3.4 Dual instantiation

The same `PluginInterface` subclass is instantiated in **both** daemon and
tray processes. `on_load/on_start/on_stop/on_unload` only fire in the daemon.
`build_tab` only fires in the tray. The host injects a different
`PluginContext` per side (e.g., tray context has no `data_dir` writes).
Cross-process communication happens via the plugin's own D-Bus interface
(`dbus_interface()`) — the daemon-side instance publishes methods and signals;
the tray-side proxy consumes them.

### 3.5 `SettingsSchema`

Declarative, Qt-free:

```python
class SettingsSchema:
    fields: list[Field]      # StringField, IntField(min, max),
                             # BoolField, SelectField(options),
                             # SecretField
```

The Settings tab renders the form from this schema. Plugins never touch Qt
for settings — only for their own tab content.

### 3.6 Permissions

Enforced at `PluginContext` construction. A plugin without `net.http` gets
`ctx.http = None`; accessing raises `PermissionError`. This models the eventual
subprocess-sandbox story (option C from Q3) without implementing it yet.

### 3.7 Enable / disable

`config.toml` holds `enabled_plugins = [...]`. Toggling in the Settings tab
drives `EnablePlugin` / `DisablePlugin` on D-Bus. Daemon runs
`on_stop` → `on_unload` (disable) or `on_load` → `on_start` (enable). Tray
adds/removes the plugin tab on the corresponding signals.

## 4. D-Bus Surface

Session bus only. No system bus, no polkit. No D-Bus service activation —
systemd supervises the daemon.

### 4.1 Core

```
Service: ai.talonic.Smartass
Object:  /ai/talonic/Smartass
Interface: ai.talonic.Smartass.Core

  Methods:
    Ping()                                 → s        # "pong <version>"
    ListPlugins()                          → a(sssbb) # id, name, version,
                                                      # description, installed, enabled
    EnablePlugin(id: s)                    → ()
    DisablePlugin(id: s)                   → ()
    InstallPlugin(source_path: s)          → s        # returns plugin_id
    UninstallPlugin(id: s)                 → ()
    GetConfig(plugin_id: s)                → a{sv}    # flat values
    SetConfig(plugin_id: s, values: a{sv}) → ()
    GetSettingsSchema(plugin_id: s)        → s        # JSON-encoded schema
    ExportAll()                            → s        # TOML blob
    ImportAll(toml_blob: s, strategy: s)   → ()       # "replace" | "merge"
    ReloadDaemon()                         → ()

  Signals:
    PluginEnabled(id: s)
    PluginDisabled(id: s)
    PluginInstalled(id: s)
    PluginUninstalled(id: s)
    SettingsChanged(plugin_id: s, values: a{sv})
    PluginStateUpdated(plugin_id: s, payload: a{sv})
```

### 4.2 Per-plugin

```
Object:    /ai/talonic/Smartass/plugins/<id>
Interface: ai.talonic.Smartass.Plugin     # common to all plugins
    Properties: Id (s), Version (s), Enabled (b)
    Methods:
        GetState() → a{sv}

Interface: ai.talonic.Smartass.Plugin.<PascalId>   # plugin-specific
    # Weather example:
    Methods:
        RefreshNow() → ()
        GetCurrent() → a{sv}
        GetForecast() → aa{sv}
    Signals:
        WeatherUpdated(payload: a{sv})
```

### 4.3 Type strategy

- Flat settings: `a{sv}` (dict of variants).
- Complex values (schemas, forecasts): JSON-encoded strings. Keeps D-Bus
  signatures stable as schemas evolve.

### 4.4 Client

Tray uses a thin `DaemonClient` wrapping `QtDBus`. It converts D-Bus signals
into Qt signals so tabs bind naturally. Each tab holds a plugin-specific
D-Bus proxy.

### 4.5 Introspection

Full `org.freedesktop.DBus.Introspectable` support. Debug via
`busctl --user introspect ai.talonic.Smartass /ai/talonic/Smartass`.

## 5. Config & Data Layout

### 5.1 Paths (XDG-compliant)

```
~/.config/smartass/config.toml              # portable settings
~/.local/share/smartass/
    plugins/<id>/                           # user-installed plugin dirs
    plugin_data/<id>/data.db                # per-plugin SQLite runtime data
    exports/                                # timestamped export bundles
~/.cache/smartass/                          # logs, http cache
/usr/share/smartass/plugins/<id>/           # bundled plugins (read-only)
/usr/share/smartass/schemas/config.schema.json
```

### 5.2 `config.toml` shape

```toml
[smartass]
version            = 1
enabled_plugins    = ["weather"]
window_start_hidden = true   # tray icon shown; main window opens on click
theme              = "system"

[plugins.weather]
city         = "Berlin"
country      = "DE"
units        = "metric"
poll_minutes = 15
```

### 5.3 `ConfigStore`

- Atomic write (tmpfile + `rename`), `fsync`.
- No external-edit watch: mutations go through `SetConfig`. `ReloadDaemon`
  forces a re-read.
- Validated against each plugin's `settings_schema` on write.
- Secrets (API keys): stored in GNOME Keyring via the `secretstorage`
  library. `SecretField` values in TOML hold a keyring handle string; the
  actual secret is fetched on demand.

### 5.4 Import / export

- **Export** (`ExportAll`): produces a TOML blob:

  ```toml
  [meta]
  exported_at      = "2026-04-21T15:08:00Z"
  smartass_version = "0.1.0"
  config_schema    = 1

  [config]
  # verbatim config.toml sections

  [plugin_state.quicknotes]
  notes = [...]

  [plugin_state.clipboard]
  history = [...]
  ```

  Secrets excluded by default. `ExportAll(include_secrets=True)` overrides.

- **Import** (`ImportAll(blob, strategy)`):
  - `replace`: wipe current state, write imported state.
  - `merge`: shallow-merge per plugin section.
  - Affected plugins hot-reload
    (`on_stop` → `on_unload` → `on_load` → `on_start`).

- UI: `Export…` / `Import…` buttons on the Settings tab use a file dialog;
  exports default to
  `~/.local/share/smartass/exports/smartass-export-YYYYMMDD-HHMMSS.toml`.

### 5.5 Schema versioning

`[smartass].version` is an integer. Migrations live in
`smartass.core.config.migrations` and run at daemon start.

## 6. Packaging, Install, Systemd

### 6.1 Repo layout (target)

```
smartass/
  __init__.py
  core/
    manifest.py
    plugin_interface.py
    config.py
    paths.py
    dbus_names.py
  daemon/
    __init__.py
    __main__.py
    service.py
    plugin_manager.py
    http.py
  tray/
    __init__.py
    __main__.py
    app.py
    tray_icon.py
    main_window.py
    settings_tab.py
    daemon_client.py
    schema_form.py
  plugins/
    weather/
      manifest.toml
      plugin.py
      ui.py
      api.py
      __init__.py
assets/
  icons/
    smartass.svg
    weather-*.svg
debian/
  control
  rules
  compat
  smartass.install
  smartass.dirs
  smartass.links
  smartass.postinst
  smartass.prerm
  smartass-daemon.service
  smartass-tray.desktop
  ai.talonic.smartass.desktop
  ai.talonic.smartass.svg
docs/
  superpowers/specs/
pyproject.toml
```

### 6.2 Systemd user unit

`debian/smartass-daemon.service` → `/usr/lib/systemd/user/smartass-daemon.service`:

```ini
[Unit]
Description=Smartass daemon (plugin host + D-Bus service)
After=graphical-session.target

[Service]
Type=dbus
BusName=ai.talonic.Smartass
ExecStart=/opt/smartass/venv/bin/python -m smartass.daemon
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

### 6.3 Autostart + launcher

`/etc/xdg/autostart/smartass-tray.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Smartass
Exec=/opt/smartass/venv/bin/python -m smartass.tray
Icon=ai.talonic.smartass
X-GNOME-Autostart-enabled=true
OnlyShowIn=GNOME;Unity;
```

Also installs `/usr/share/applications/ai.talonic.smartass.desktop` so
GNOME Activities can launch the tray manually.

### 6.4 Packaging approach

`dh-virtualenv`: bundles a venv containing PySide6, dbus-next, httpx, etc.
into `/opt/smartass/venv`. Uses the system Python. Produces a single
`smartass_<version>_amd64.deb` artifact. PPA setup deferred to post-MVP.

### 6.5 postinst

```bash
systemctl --global enable smartass-daemon.service || true
update-desktop-database -q || true
gtk-update-icon-cache -q /usr/share/icons/hicolor || true
```

### 6.6 prerm

Stops the user unit for active users, removes icon cache entry on purge.

### 6.7 AppIndicator dependency

On vanilla GNOME Shell the tray requires the AppIndicator extension. On
Ubuntu Desktop this is enabled by default. The postinst prints a warning if
`gnome-shell-extension-appindicator` /
`gnome-shell-extension-ubuntu-appindicators` is missing.

### 6.8 Install

```
sudo apt install ./smartass_0.1.0-1_amd64.deb
# log out + back in → tray icon appears; daemon running as user service
```

## 7. Testing & Error Handling

### 7.1 Unit tests (pytest)

- `core/plugin_interface` — schema validation, permission gating,
  context injection.
- `core/config` — TOML roundtrip, migrations, atomic write, invalid-value
  rejection, secret handle roundtrip (keyring mocked).
- `daemon/plugin_manager` — discovery, enable/disable ordering, hot reload.
- `plugins/weather/api` — Open-Meteo client with recorded fixtures (`respx`);
  geocoding, forecast parsing, HTTP 5xx / timeout / malformed JSON.

### 7.2 Integration tests

- Run daemon on a private session bus (`dbus-run-session -- pytest …`).
- `DaemonClient` (tray-side) exercised without GUI (`QCoreApplication`).
- Export → import roundtrip with Weather enabled and configured.
- Enable/disable plugin: correct signals emitted, tab mount/unmount hooks
  fire.

### 7.3 GUI tests

Out of scope for MVP. Manual smoke-test checklist in `docs/manual_qa.md`.

### 7.4 Error handling

- Plugin exceptions in `on_load/on_start` → plugin marked `failed`, surfaced
  in Settings tab with a stack-trace snippet; daemon keeps running.
- Daemon D-Bus errors → tray shows "daemon offline" banner + retry button,
  reconnect with 2s-base exponential backoff.
- Network errors in Weather → last-good state from SQLite shown, marked
  stale.
- No bare `except:`. All error logs prefixed with plugin id.

### 7.5 Logging

- `logging` stdlib, JSON formatter.
- Daemon: `~/.cache/smartass/daemon.log` (rotating, 5 × 1 MB) + stderr
  (captured by systemd journal).
- Tray: `~/.cache/smartass/tray.log`.

## 8. MVP Scope & Milestones

**MVP = this spec implemented up to and including Weather end-to-end.**
Other named plugins (QuickNotes, ClipboardHistory, LLMChat,
PluginBuilderUsingAI) are post-MVP and are not built in this round.

Implementation order:

1. `core.paths`, `core.manifest`, `core.plugin_interface`, `core.config` +
   unit tests.
2. `daemon` skeleton: D-Bus Core service, `PluginManager`, logging, entry
   point + unit/integration tests.
3. `plugins/weather`: Open-Meteo client → `WeatherPlugin` (daemon-side
   behavior, persistence, D-Bus surface) + unit tests.
4. `tray`: QApplication bootstrap, tray icon, main window, Settings tab with
   schema-form renderer, `DaemonClient`.
5. `plugins/weather/ui`: `WeatherTab` bound to the plugin's D-Bus proxy.
6. `debian/`: packaging, systemd unit, autostart, icon install.
7. End-to-end smoke test: build `.deb`, `sudo apt install ./smartass_*.deb`,
   log out / log in, verify tray icon shows, open Settings tab, enable
   Weather, set city = "Berlin", verify tab appears with forecast.

## 9. Out of Scope (Explicit)

- Subprocess plugin isolation (Q3 option C) — future work; permission model
  is already defined.
- PPA / apt repository hosting — `.deb` artifact only for MVP.
- Wayland-specific tray behavior beyond what AppIndicator already provides.
- Non-GNOME desktops (KDE, XFCE). Might work, not tested.
- GUI (widget-level) automated tests.
- LLMChat / PluginBuilderUsingAI / QuickNotes / ClipboardHistory
  implementations.

## 10. Key Decisions (traceability)

| ID  | Decision                                                 |
| --- | -------------------------------------------------------- |
| Q1  | Split: daemon + tray client                              |
| Q2  | Qt6 / PySide6                                            |
| Q3  | In-process, directory-based plugin discovery             |
| Q4  | D-Bus session bus for daemon ↔ tray                      |
| Q5  | `dh-virtualenv` `.deb`; PPA later                        |
| Q6  | Target catalog: Weather, QuickNotes, ClipboardHistory,   |
|     | PluginBuilderUsingAI, LLMChat. MVP builds: Weather + the |
|     | `PluginInterface` class                                  |
| Q7  | TOML config + per-plugin SQLite runtime data             |
| Q8  | Open-Meteo + user-typed city (7-day forecast)            |
