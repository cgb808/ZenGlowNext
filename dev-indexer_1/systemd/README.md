spool-watcher.service

Install (user service):

1) Copy unit file into user systemd dir and enable

```
mkdir -p ~/.config/systemd/user
cp systemd/spool-watcher.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now spool-watcher.service
```

2) Optional: set overrides via environment file

Create ~/.config/systemd/user/spool-watcher.env with lines like:

```
REDIS_URL=redis://127.0.0.1:6379/0
LIST_KEY=append:segments
DEST_DIR=/DEV_ZFS/spool/incoming
BRPOP_TIMEOUT=5
MAX_ITEMS=0
LIST_TTL=600
```

Then edit the unit ExecStart to reference that env file, or run:

```
systemctl --user edit spool-watcher.service
```

and add:

```
[Service]
EnvironmentFile=%h/.config/systemd/user/spool-watcher.env
```

Reload:

```
systemctl --user daemon-reload
systemctl --user restart spool-watcher.service
```
