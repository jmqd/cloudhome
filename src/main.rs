#[macro_use]
extern crate serde_derive;
extern crate rusoto_core;
extern crate rusoto_s3;
extern crate shellexpand;

mod config;
mod local;

use rusoto_core::Region;
use rusoto_s3::S3Client;

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
    // configure logging

    // We'll want to spawn a thread for this.
    local::poll_changes(config.cloudhome_paths().as_ref());

    // In additional to polling the local file system, we'll want to poll the
    // cloud files somehow. The previous implementation simply HEADed the files
    // and computed the hashes of each, but I suspect there's a better solution.
    // However, if need be, that solution will work.
    // poll_for_remote_changes();
}
