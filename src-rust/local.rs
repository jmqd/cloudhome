extern crate crypto;

use crypto::digest::Digest;
use notify::{RecommendedWatcher, RecursiveMode, Watcher};
use std::io::{BufRead, BufReader};
use std::sync::mpsc::channel;
use std::time::Duration;

const S3_MD5_CHUNK_READ_LENGTH: usize = 10_240;

/// Polls the local file system for changes in the relevant cloudhome directory
/// paths. Upon receiving write events in the local filesystem, we spawn a task
/// to PUT those changes to the cloud storage.
pub fn poll_changes(paths: &Vec<String>) {
    // Create a channel to receive the events.
    let (tx, rx) = channel();

    // Automatically select the best implementation for your platform.
    // You can also access each implementation directly e.g. INotifyWatcher.
    let mut watcher: RecommendedWatcher =
        Watcher::new(tx, Duration::from_secs(2))
            .expect("Constructing watcher failed");

    // Watch all cloudhome paths. All files and directories in these paths and
    // below will be monitored for changes.
    paths.iter().for_each(|path| {
        watcher
            .watch(path, RecursiveMode::Recursive)
            .expect("Watching path failed.")
    });

    // The main loop to receive file-system events. Upon a new write event, we'll
    // trigger a write to S3. We'll probably want to submit a new task to a
    // SetQueue-backed ThreadPool on every Ok() pattern match to write to S3, to
    // avoid starvation of the rx channel. We can use a set-backed queue here
    // because there's no sense uploading a file twice -- we'd rather just
    // upload the most recent one.
    loop {
        match rx.recv() {
            // TODO(mcqueenjordan) yield the task to actually do the thing here
            Ok(event) => println!("{:?}", event),
            Err(e) => println!("watch error: {:?}", e),
        }
    }
}

/// This is an implementation of S3's MD5 e-tag hashing algorithm for local files.
///
/// Note that multi-part uploaded objects will hash differently than this
/// function on S3s service, so we cannot rely on hash comparisons if the
/// S3 object was multi-part uploaded. This generally only affects objects
/// larger than 5GB.
pub fn calculate_hash(file_path: &String) -> String {
    let file = match std::fs::File::open(file_path) {
        Ok(file) => file,
        Err(_) => panic!("Error opening file {}", file_path),
    };

    // S3 uses a specific chunk length for computing the MD5 hash.
    let mut reader = BufReader::with_capacity(S3_MD5_CHUNK_READ_LENGTH, file);
    let mut digest = crypto::md5::Md5::new();

    // Read sequential chunks of the file into a buffer, feeding the buffer
    // to the digest. Rinse and repeat until there's no more file left.
    loop {
        let buffer = reader.fill_buf().expect("Problem filling buffer");
        let length = buffer.len();
        digest.input(buffer);

        match length {
            0 => break,
            _ => reader.consume(length),
        }
    }

    digest.result_str()
}
