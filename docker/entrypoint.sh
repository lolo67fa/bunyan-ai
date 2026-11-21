#!/bin/sh
# Start BUNYAN as the unprivileged "bunyan" user.
# Cloud volumes are often mounted as root: when started as root, make /data writable
# for bunyan first, then drop privileges for the server itself.
set -eu
if [ "$(id -u)" = "0" ]; then
  mkdir -p "${BUNYAN_DATA_DIR:-/data}"
  chown -R bunyan:bunyan "${BUNYAN_DATA_DIR:-/data}"
  exec setpriv --reuid=bunyan --regid=bunyan --init-groups --inh-caps=-all -- "$@"
fi
exec "$@"
