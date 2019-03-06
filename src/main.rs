#[macro_use]
extern crate serde_derive;
extern crate rusoto_core;
extern crate rusoto_s3;
extern crate serde;
extern crate serde_json;
extern crate shellexpand;

use rusoto_core::Region;
use rusoto_s3::{S3, ListObjectsRequest, S3Client};

static CLOUDHOME_CONFIG_PATH: &'static str = "~/.cloudhome.json";

#[derive(Debug, Deserialize)]
struct Config {
    cloudhome: String,
    credential_profile: String,
    log_file: String,
    bucket_names: Vec<String>
}

fn main() {
    let config = read_configuration();
    let s3 = S3Client::new(Region::UsWest2);
    // configure logging
    // spawn_log_rotator()
    poll_for_changes(config);
}

fn poll_for_changes(config: Config) {
    // notify poll config.cloudhome
}

fn read_configuration() -> Config {
    let path = shellexpand::tilde(CLOUDHOME_CONFIG_PATH).to_string();
    let config_data: String = std::fs::read_to_string(path).expect("Bad file.");
    return serde_json::from_str(&config_data).expect("Bad json.");
}
