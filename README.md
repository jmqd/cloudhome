# cloudhome

## design

`cloudhome` aims to be a background daemon process that listens to changes
to `~` and backs up to a cloud location. S3 is chosen as the cloud-backed
storage location.

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
