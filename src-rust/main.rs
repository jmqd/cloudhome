#[macro_use]
extern crate serde_derive;
extern crate rusoto_core;
extern crate rusoto_s3;
extern crate serde_json;
extern crate shellexpand;

mod cloud;
mod config;
mod local;
pub mod manifest;

use manifest::*;
use rusoto_core::Region;
use rusoto_s3::S3Client;
use std::time::Duration;

/// Cloudhome does two things, which are symmetrical to each other, in pursuit of
/// the singular goal: synchronizing your local and cloud-storage state.
///
/// 1. Polls tracked file system directory roots for changes, relaying changes
///    to the cloud storage.
/// 2. Polls the cloud storage for changes, and relays those changes to the
///    local file system.
fn main() {
    let config = config::Config::read();
    let s3 = S3Client::new(Region::UsWest2);
    // TODO(mcqueenjordan): configure logging

    // TODO(mcqueenjordan): We'll want to spawn a thread for this.
    local::poll_changes(config.cloudhome_paths().as_ref());

    // TODO(mcqueenjordan):
    config.cloudhome_paths().iter().for_each(|path| {
        cloud::poll_changes(s3, path, Duration::from_secs(15))
        cloud::poll_changes(&s3, path, Duration::from_secs(15))
    });
}
