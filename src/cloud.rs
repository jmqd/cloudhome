use crate::manifest::*;
use rusoto_s3::S3Client;
use std::time::Duration;

/// The state of synchronization between cloud storage and local storage.
enum SyncState {
    /// The local storage and cloud storage have identical state.
    Equilibrium,

    /// The cloud storage has state that the local storage should have.
    CloudAhead,

    /// The local storage has state that the cloud storage should have.
    LocalAhead,
}

impl SyncState {
    fn determine(s3: &S3Client, path: &String) -> SyncState {
        // TODO(mcqueenjordan)
        // compare remote and local hashes of the manifest
        // return Equilibrium if true
        // else return
        // CloudAhead if Cloud has more recent ts
        // else return CloudBehind
        return SyncState::Equilibrium; // temp to compile
    }
}

pub fn poll_changes(
    s3: &S3Client,
    path: &String,
    sleep_duration_between_polls: Duration,
) {
    loop {
        match SyncState::determine(s3, path) {
            SyncState::Equilibrium => (),
            SyncState::CloudAhead => sync_down_changes(s3, path),

            // We're not going to do anything here. That's the responsibility
            // of the filesystem poller. It's probably uploading these changes.
            SyncState::LocalAhead => (),
        }

        std::thread::sleep(sleep_duration_between_polls);
    }
}

fn sync_down_changes(s3: &S3Client, path: &String) {
    // TODO(mcqueenjordan)
    // compare hashes...
    // for any local files whose timestamp is less than the remote timestamp:
    //   download
    // write the in-memory manifest which was fetched
    let local_manifest = Manifest::from_local(path);
    let cloud_manifest = local_manifest.from_cloud(s3);
}
