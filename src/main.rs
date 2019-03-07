#[macro_use]
extern crate serde_derive;
extern crate notify;
extern crate rusoto_core;
extern crate rusoto_s3;
extern crate serde;
extern crate serde_json;
extern crate shellexpand;

use notify::{RecommendedWatcher, RecursiveMode, Watcher};
use rusoto_core::Region;
use rusoto_s3::S3Client;
use std::sync::mpsc::channel;
use std::time::Duration;

static CLOUDHOME_CONFIG_PATH: &'static str = "~/.cloudhome.json";

#[derive(Debug, Deserialize)]
struct Config {
    cloudhome: String,
    credential_profile: String,
    log_file: String,
    bucket_names: Vec<String>,
}

fn main() {
    let config = read_configuration();
    let s3 = S3Client::new(Region::UsWest2);
    // configure logging

    // spawn_log_rotator()

    // We'll want to spawn a thread for this.
    poll_for_changes(config, s3);
}

fn poll_for_changes(config: Config, s3: S3Client) {
    // Create a channel to receive the events.
    let (tx, rx) = channel();

    // Automatically select the best implementation for your platform.
    // You can also access each implementation directly e.g. INotifyWatcher.
    let mut watcher: RecommendedWatcher =
        Watcher::new(tx, Duration::from_secs(2)).expect("Constructing watcher failed");

    // Watch all cloudhome paths. All files and directories in these paths and
    // below will be monitored for changes.
    config
        .bucket_names
        .iter()
        .map(|name| format!("{}/{}", shellexpand::tilde(&config.cloudhome), name))
        .for_each(|path| {
            watcher
                .watch(path, RecursiveMode::Recursive)
                .expect("Watching path failed.")
        });

    // The main loop to receive file-system events. Upon a new write event, we'll
    // trigger a write to S3. We'll probably want to spawn a new thread on each
    // Ok() pattern match to write to S3, to avoid starvation of the rx channel.
    loop {
        match rx.recv() {
            Ok(event) => println!("{:?}", event),
            Err(e) => println!("watch error: {:?}", e),
        }
    }
}

fn read_configuration() -> Config {
    let path = shellexpand::tilde(CLOUDHOME_CONFIG_PATH).to_string();
    let config_data: String = std::fs::read_to_string(path).expect("Bad file.");
    return serde_json::from_str(&config_data).expect("Bad json.");
}
