enum SyncState {
    Equilibrium,
    CloudAhead,
    CloudBehind
}

impl SyncState {
    fn determine(s3: S3Client, local_path: &String) -> SyncState {
        // compare remote and local hashes of the manifest
        // return Equilibrium if true
        // else return
        // CloudAhead if Cloud has more recent ts
        // else return CloudBehind
    }
}

pub fn poll_changes(s3: S3Client) {
    // TODO
}
