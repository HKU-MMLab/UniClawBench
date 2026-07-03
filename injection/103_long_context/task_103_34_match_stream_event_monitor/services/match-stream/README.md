Host-only video asset directory. Do not declare this as a container service.

`ops/stream_server.py` transcodes this obfuscated processed excerpt into a
per-connection MJPEG feed. The server skips the long static halftime-card
lead-in and starts a few seconds before second-half action, so a normal watch
session sees motion quickly while preserving the same event window. Executor
containers should only see the public stream URL and must not receive this
asset directory or the server code.
