extern crate serde;
extern crate serde_json;

use std::fs::read_to_string;

static CLOUDHOME_CONFIG_PATH: &'static str = "~/.cloudhome.json";

/// Represent the cloudhome configuration state (read from ~/.cloudhome.json)
#[derive(Debug, Deserialize)]
pub struct Config {
    cloudhome: String,
    credential_profile: String,
    log_file: String,
    bucket_names: Vec<String>,
}

impl Config {
    /// A utility function to read and marshal the cloudhome configuration.
    pub fn read() -> Config {
        let path = shellexpand::tilde(CLOUDHOME_CONFIG_PATH).to_string();
        let config_data: String = read_to_string(path).expect("Bad file.");
        return serde_json::from_str(&config_data).expect("Bad json.");
    }

    pub fn cloudhome_paths(&self) -> Vec<String> {
        return self
            .bucket_names
            .iter()
            .map(|name| {
                format!("{}/{}", shellexpand::tilde(&self.cloudhome), name)
            })
            .collect();
    }
}
