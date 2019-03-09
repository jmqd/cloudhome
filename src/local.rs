use notify::{RecommendedWatcher, RecursiveMode, Watcher};
use std::sync::mpsc::channel;
use std::time::Duration;

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
