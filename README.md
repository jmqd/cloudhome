# cloudhome

## design

`cloudhome` aims to be a background daemon process that listens to changes
to a confgiruable list of source directories and backs up to a cloud location.
S3 is chosen as the cloud-backed storage location. In addition, it will
"backwards sync" if the storage has newer bits.

### requirements

1. async event-based backup daemon, requiring no user interaction
2. on load, correctly syncs from remote with latest files
(i.e. provides value in a multi-device use case)
3. keeps a revision history over time
4. minimizes file transfer to only files with a diff

### anti-requirements

1. Support for non-UNIX systems

## project management

### Phase 1

1. Naive syncing.
2. Not daemon based

### Phase 2

1. Smart syncing
2. Daemonize

## concrete choices

### libraries

- [Watchdog][] seems like the correct library to listen to system events
and trigger a backup event

### architecture

#### daemon strategy

Unclear is this is best solved in code or thru the system.

[Watchdog]: https://pythonhosted.org/watchdog/
