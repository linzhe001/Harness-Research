# Bundled cc-connect Source

This directory contains the bundled `cc-connect` source tree used by the
current repository for local builds.

Use it only through the repository-local workflow:

- build with `tooling/remote_control/scripts/build_patched_cc_connect.sh`
- start with `tooling/remote_control/bin/cc-connect`
- configure with `tooling/remote_control/config/cc_connect.local.toml`

Do not replace this directory with another source tree during normal setup.
