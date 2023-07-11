extern crate chrono;

use crate::manifest::*;
use chrono::DateTime;
use rusoto_s3::{HeadObjectRequest, S3Client, S3};
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

// TODO(mcqueenjordan): remove `pub`. it's just there for dev purposes.
pub fn sync_down_changes(s3: &S3Client, path: &String) {
    // TODO(mcqueenjordan)
    // compare hashes...
    // for any local files whose timestamp is less than the remote timestamp:
    //   download
    // write the in-memory manifest which was fetched
    let local_manifest = Manifest::from_local(path);
    let cloud_manifest = local_manifest.from_cloud(s3);
    println!("{:?}", local_manifest);
    println!("{:?}", cloud_manifest);
    println!(
        "{:?}",
        get_remote_file_metadata(
            &s3,
            &local_manifest,
            &"manifest_v2.json".to_owned()
        )
    );
}

fn get_remote_file_metadata(
    s3: &S3Client,
    manifest: &Manifest,
    key: &String,
) -> FileMetadata {
    let request = HeadObjectRequest {
        bucket: manifest.bucket_name.to_owned(),
        key: key.to_owned(),
        ..Default::default()
    };

    let response = s3.head_object(request).sync().expect("HEAD object failed");
    println!(
        "{}",
        response.clone().last_modified.expect("whatever").to_owned()
    );
    let last_modified = DateTime::parse_from_str(
        &response
            .last_modified
            .expect("Last-Modified issue")
            .to_owned(),
        // TODO(mcqueenjordan) found bug in chrono crate here. Will submit upstream pull request.
        // https://github.com/chronotope/chrono/issues/288
        "%a, %d %b %Y %H:%M:%S %Z",
    )
    .expect("Issue parsing DateTime")
    .timestamp();

    FileMetadata {
        key: key.to_owned(),
        hash: response
            .e_tag
            .expect("e-tag problem")
            .trim_matches(|c| c == '/' || c == '"')
            .to_owned(),
        content_length: response
            .content_length
            .expect("Content-Length problem"),
        last_modified: last_modified,
    }
}
