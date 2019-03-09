use rusoto_s3::GetObjectRequest;

static MANIFEST_KEY: &'static str = "manifest.json";

#[derive(Debug, Deserialize)]
pub struct Manifest {
    files: Vec<FileMetadata>,
}

impl Manifest {
    pub fn from_cloud(s3: S3Client, bucket_name: &String) -> Manifest {
        // TODO(mcqueenjordan): finish impl here
        let request = GetObjectRequest {
            bucket: bucket_name,
            key: MANIFEST_KEY,
        };
        return s3.get_object(request);
    }

    pub fn from_local(path: &String) -> Manifest {
        // TODO(mcqueenjordan)
    }
}

pub struct FileMetadata {
    key: String,
    hash: String,
    last_modified: u64,
}
