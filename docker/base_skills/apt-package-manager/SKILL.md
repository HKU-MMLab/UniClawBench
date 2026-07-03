---
name: apt-package-manager
description: Search, install, and verify Debian or Ubuntu packages with apt-get in the container.
---

# Apt Package Manager

Use this skill when a task requires installing or verifying Linux packages in this Ubuntu environment.

## Notes

1. Shell commands already run as `root`, so `sudo` is unnecessary.
2. Prefer `apt-get` over interactive frontends such as `apt`.
3. Install only the specific packages you need for the task.
4. Do not run broad upgrade commands such as `apt-get upgrade` or `dist-upgrade` unless the task explicitly requires them.

## Common commands

Refresh package metadata:

```bash
apt-get update
```

Search for package names:

```bash
apt-cache search "<keyword>"
apt-cache policy <package>
```

Install one or more packages:

```bash
apt-get install -y <package>
apt-get install -y <package1> <package2>
```

Verify installation:

```bash
command -v <binary>
dpkg -s <package>
<binary> --version
```

## Suggested workflow

1. Identify the package name with `apt-cache search` if needed.
2. Run `apt-get update` before the install if package metadata may be stale.
3. Install the minimal package set with `apt-get install -y`.
4. Verify the installed binary or package state before finishing.
