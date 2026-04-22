# Manual QA Checklist — Smartass MVP

Run the .deb install, then log out + back in before starting these checks.

## Install

- [ ] `sudo apt-get install -y ./smartass_0.1.0-1_amd64.deb` completes without error
- [ ] `/etc/xdg/autostart/smartass-tray.desktop` exists
- [ ] `/usr/lib/systemd/user/smartass-daemon.service` exists
- [ ] `/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg` exists
- [ ] `/usr/share/smartass/plugins/weather/manifest.toml` exists

## Daemon

- [ ] `systemctl --user status smartass-daemon.service` shows `active (running)`
- [ ] `busctl --user call ai.talonic.Smartass /ai/talonic/Smartass ai.talonic.Smartass.Core Ping` returns `s "pong 0.1.0"`
- [ ] `~/.cache/smartass/daemon.log` shows "daemon ready" after boot

## Tray

- [ ] Robot icon visible in the GNOME top bar (requires the AppIndicator extension)
- [ ] Left-clicking the tray icon toggles the main window
- [ ] Right-click menu shows: Show / Hide, Restart daemon, Quit tray

## Settings tab

- [ ] Settings tab is always visible and selected by default
- [ ] Plugin list shows `Weather (0.1.0)` with tooltip "Current conditions and 7-day forecast via Open-Meteo"
- [ ] Selecting Weather shows a form with fields: City (string, required), Units (metric/imperial), Refresh every (minutes)
- [ ] Enable button text toggles between "Enable" and "Disable"
- [ ] Clicking Enable causes a Weather tab to appear
- [ ] Clicking Disable removes the Weather tab

## Weather tab

- [ ] With city=Berlin, units=metric: within ~60s shows current temperature + condition + humidity + wind
- [ ] 7-day forecast grid shows Date / High / Low / Conditions columns
- [ ] Refresh button triggers an immediate re-fetch
- [ ] Changing city to Munich and clicking Save (Settings tab) updates the Weather tab within one poll interval
- [ ] Switching units from metric to imperial updates the deg label (°C → °F) and wind units (km/h → mph)

## Import / Export

- [ ] Settings tab → Export… → save to `~/Desktop/smartass-export.toml`
- [ ] Exported file contains `[config.smartass]` with `enabled_plugins = ["weather"]` and `[config.plugins.weather]` with your city
- [ ] Change units, then Import the saved export → units revert to the exported value

## Persistence

- [ ] Daemon restart (`systemctl --user restart smartass-daemon.service`) keeps the enabled-plugins list and Weather settings
- [ ] Log out + log in: tray icon reappears, daemon auto-starts, Weather tab still enabled

## Uninstall

- [ ] `sudo apt-get remove -y smartass` stops the daemon
- [ ] `systemctl --user status smartass-daemon.service` reports the unit file is missing
- [ ] `sudo apt-get purge -y smartass` removes icon + desktop entries; tray is gone after logout
- [ ] User data under `~/.config/smartass/` and `~/.local/share/smartass/` is preserved (XDG data is not removed on purge)
