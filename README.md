<!-- Tip - Pycharm supports easy updating Table of Comment (TOC) using Alt+Enter -->
<!-- TOC -->
* [Smartass](#smartass)
  * [What it does](#what-it-does)
  * [Architecture at a glance](#architecture-at-a-glance)
  * [Install](#install)
    * [Option A — prebuilt `.deb`](#option-a--prebuilt-deb)
    * [Option B — build from source](#option-b--build-from-source)
    * [After install](#after-install)
  * [Using the app](#using-the-app)
    * [Settings tab](#settings-tab)
    * [Weather plugin](#weather-plugin)
    * [Import / export](#import--export)
  * [Uninstall](#uninstall)
  * [Configuration and data paths](#configuration-and-data-paths)
  * [Troubleshooting](#troubleshooting)
    * [Tray icon doesn't appear](#tray-icon-doesnt-appear)
    * [Daemon not reachable](#daemon-not-reachable)
    * [Weather tab shows "stale"](#weather-tab-shows-stale)
  * [Development](#development)
    * [Developer dependencies](#developer-dependencies)
    * [Running tests](#running-tests)
    * [Local iteration without reinstalling](#local-iteration-without-reinstalling)
  * [License](#license)
<!-- TOC -->

# Smartass

A desktop smart-assistant app for Ubuntu. It lives as a robot icon in the
GNOME top panel; clicking it opens a tabbed window with an always-visible
**Settings** tab plus one tab per enabled plugin.

## What it does

- **Tray-resident app.** An AppIndicator-style icon sits in the GNOME top
  bar. Left-click toggles the main window; right-click offers Show/Hide,
  Restart daemon, and Quit tray.
- **Plugin system.** Each plugin is a directory with a `manifest.toml` and a
  Python module. Plugins are discovered from `/usr/share/smartass/plugins/`
  (system / bundled) and `~/.local/share/smartass/plugins/` (user-installed).
  Enabling a plugin in the Settings tab adds its tab to the window;
  disabling removes it.
- **Settings forms.** Each plugin declares a typed settings schema
  (strings, ints with bounds, booleans, dropdowns, secrets). The Settings
  tab auto-renders the form — plugins never touch Qt for their settings.
- **Import / export.** The Settings tab can export your whole config
  (including enabled plugins + per-plugin values) to a TOML file and
  import one back, with `merge` or `replace` strategies.
- **Split daemon + tray.** A `smartass-daemon` user service hosts the
  plugins and does all the work (polling, data fetching, persistence).
  The tray is a separate Qt6 process that talks to the daemon over the
  session D-Bus at `ai.talonic.Smartass`. The daemon keeps running even
  when the window is closed, and survives a tray crash.
- **Bundled: Weather.** Current conditions + 7-day forecast via
  [Open-Meteo](https://open-meteo.com/) (no API key, user-typed city).
  Hero card shows large emoji + temperature + feels-like, with a
  details grid (humidity, wind, precipitation, cloud cover, sunrise,
  sunset, UV index, rain probability) and a 7-day grid.
- **Theme-aware.** Symbolic tray icon auto-recolors for dark / light
  panels. All UI text colors follow the active Qt palette.
- **Autostart.** The daemon is a systemd *user* service, enabled
  globally at install time and started on login. The tray is launched
  via XDG autostart from `/etc/xdg/autostart/smartass-tray.desktop`.

## Architecture at a glance

```
  GNOME top bar
        │ left-click
        ▼
  smartass-tray (PySide6/Qt6)
        │ session D-Bus: ai.talonic.Smartass
        ▼
  smartass-daemon (systemd --user)
        │
        └── PluginManager
              ├── weather (bundled)
              └── …your plugins…
```

Data lives under your XDG directories; see
[Configuration and data paths](#configuration-and-data-paths) below.

## Install

### Option A — prebuilt `.deb`

If someone's handed you a `smartass_<version>_amd64.deb`:

```bash
sudo apt-get install -y /path/to/smartass_0.1.0-1_amd64.deb
```

The `.deb` bundles its own Python venv at `/opt/smartass/` (includes
PySide6, dbus-next, httpx, etc.), so the only runtime system-level
dependencies are Qt6 shared libraries and the GNOME AppIndicator
extension.

### Option B — build from source

You need Ubuntu 22.04+ and the Debian build tools:

```bash
sudo apt-get install -y devscripts dh-virtualenv python3-dev build-essential debhelper
```

Clone this repo, then:

```bash
# one-time: install poetry + the dev dependencies
poetry install

# build the .deb (produces ../smartass_<version>_amd64.deb; takes 5-10 min,
# downloads PySide6 wheels into the bundled venv)
task build-deb

# install the fresh .deb + enable the service + launch the tray
task install-service
```

`task install-service` calls `sudo dpkg -i` under the hood, so you'll get
a sudo password prompt.

### After install

- The **daemon** is enabled as a systemd user service — it starts on every
  login from now on. You can inspect it with:
  ```bash
  systemctl --user status smartass-daemon.service
  journalctl --user -u smartass-daemon.service
  ```
- The **tray** launches automatically on login via XDG autostart. On the
  current session, `task install-service` also launches it immediately so
  you don't need to log out and back in.
- The **tray icon** is a small robot in the top bar. On vanilla GNOME
  Shell you need the AppIndicator extension — on Ubuntu Desktop it's
  enabled by default. If the icon doesn't appear, see
  [Troubleshooting](#troubleshooting).

## Using the app

### Settings tab

Always visible. Lists every plugin discovered from the system and user
plugin directories. For each plugin:

- **Enable / Disable** button toggles whether the plugin runs and shows
  its tab in the window. The change takes effect immediately.
- Clicking a plugin in the list opens its settings form. Typed fields,
  required-field validation, bounds-checking, and secret masking are
  all handled by the form renderer.
- **Save** persists to `~/.config/smartass/config.toml` and notifies
  the running plugin, which reacts immediately (e.g. Weather re-fetches
  for the new city rather than waiting for the next poll).

### Weather plugin

Enabled by default after install? No — you opt in via Settings.

Once enabled:
- Hero card: big weather emoji + large current temperature + "Feels like
  …" + condition label.
- Details: humidity, wind speed, precipitation, cloud cover, sunrise,
  sunset, UV index (max), rain chance today.
- 7-day grid: day-of-week + emoji + high / low + rain % + condition.
- **Refresh** button forces an immediate re-fetch (via the daemon's
  `RefreshNow` D-Bus method); it does not wait for the `poll_minutes`
  interval.

Settings:
- `City` (string, required) — any city name Open-Meteo's geocoder
  recognizes.
- `Units` (`metric` / `imperial`) — controls temp and wind units.
- `Refresh every (minutes)` (1 – 240) — default 15.

### Import / export

In the Settings tab:
- **Export…** writes your whole config to a TOML file of your choice.
- **Import…** loads a TOML file back. By default the import is a
  *merge* (your current config is updated in place); running plugins
  reload with the new values.

Exports default to `~/.local/share/smartass/exports/`.

## Uninstall

The repo ships two uninstall tasks:

```bash
# Remove the package but keep your user config + data (safe for re-install)
task remove-service-keep-data

# Remove the package and delete ~/.config/smartass, ~/.local/share/smartass,
# and ~/.cache/smartass (permanent; asks for confirmation)
task remove-service-with-all-data
```

Under the hood these are `sudo apt-get remove smartass` and
`sudo apt-get purge smartass` respectively, plus stop of the systemd
user service and the running tray process.

## Configuration and data paths

| Path | Purpose |
| --- | --- |
| `~/.config/smartass/config.toml` | Global + per-plugin settings (portable) |
| `~/.local/share/smartass/plugin_data/<id>/` | Per-plugin SQLite / runtime data |
| `~/.local/share/smartass/plugins/<id>/` | User-installed plugin directories |
| `~/.local/share/smartass/exports/` | Auto-named export bundles |
| `~/.cache/smartass/daemon.log` | Rotating daemon log (5 × 1 MB) |
| `~/.cache/smartass/tray.log` | Tray log |
| `/usr/share/smartass/plugins/weather/` | Bundled Weather plugin |
| `/opt/smartass/` | The dh-virtualenv that bundles Python + PySide6 + deps |
| `/usr/lib/systemd/user/smartass-daemon.service` | systemd user unit |
| `/etc/xdg/autostart/smartass-tray.desktop` | Tray autostart entry |

## Troubleshooting

### Tray icon doesn't appear

1. Confirm the tray process is running:
   ```bash
   pgrep -af smartass.tray
   ```
2. Confirm the GNOME AppIndicator extension is enabled:
   ```bash
   gnome-extensions list --enabled | grep -i appindicator
   ```
   If empty:
   ```bash
   sudo apt-get install -y gnome-shell-extension-appindicator
   gnome-extensions enable ubuntu-appindicators@ubuntu.com
   ```
   (a logout/login may be required the first time the extension is
   enabled).
3. Verify Smartass registered itself as a StatusNotifierItem:
   ```bash
   busctl --user call org.kde.StatusNotifierWatcher /StatusNotifierWatcher \
     org.freedesktop.DBus.Properties Get ss \
     org.kde.StatusNotifierWatcher RegisteredStatusNotifierItems
   ```
   You should see an entry whose properties include `Id = "Smartass"`.

### Daemon not reachable

```bash
systemctl --user status smartass-daemon.service
systemctl --user restart smartass-daemon.service
busctl --user call ai.talonic.Smartass /ai/talonic/Smartass \
  ai.talonic.Smartass.Core Ping
```

Expected Ping reply: `s "pong <version>"`.

### Weather tab shows "stale"

The daemon couldn't reach Open-Meteo (or geocoding) for the last poll.
The tab falls back to the last good snapshot from SQLite. Check:
```bash
tail ~/.cache/smartass/daemon.log
```

Common causes: offline network, DNS issue, or an unreachable city name
(the geocoder returned no results).

## Development

### Developer dependencies

```bash
sudo snap install task --classic      # for Taskfile
poetry install                         # runtime + dev deps in a poetry venv
pre-commit install                     # optional: ruff check/format on commit
```

### Running tests

Most tests run under the normal pytest runner; the D-Bus integration tests
need a private session bus, so run them under `dbus-run-session`:

```bash
poetry run pytest tests/core tests/plugins tests/daemon/test_http.py \
                  tests/daemon/test_plugin_manager_discovery.py \
                  tests/daemon/test_plugin_manager_lifecycle.py

dbus-run-session -- poetry run pytest \
  tests/daemon/test_service_core.py tests/integration/
```

### Local iteration without reinstalling

When you're changing daemon or plugin code, you can skip the full `.deb`
rebuild cycle:

```bash
# Spin a private bus, run the daemon from the working tree, exercise it
dbus-run-session -- poetry run python -m smartass.daemon &
# (then use busctl --user call … to poke the D-Bus API)
```

When tray-side code changes, the fastest way to test without a rebuild is
to `sudo rsync` the changed files into `/opt/smartass/lib/python3.10/site-packages/smartass/`
and relaunch the tray — see `Taskfile.yml` for patterns. For production
use, always `task build-deb && task install-service`.

## License

Distributed under the terms of the `MIT license`.
