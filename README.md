# Swift-Monitoring

Tools for external monitoring of Swift.

## Usage-Reports

The subfolder [usage-reports](./usage-reports) contains a Python package to create a
one-page usage report of the cluster.

## Memory-watch

The subfolder [memory-watch](./memory-watch) contains a Python package to find jobs
that used a lot less memory than what they requested.

## zfs-watch

The subfolder [zfs-watch](./zfs-watch) contains a Python package to find who should
own the data (tracked by zfs) of past users (whose accounts expired).
