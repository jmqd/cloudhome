import boto3
from botocore.exceptions import EndpointConnectionError
import logging
import hashlib
import time
from config import Config
from calendar import timegm
import json
import os

CLOUDHOME_CONFIG = os.path.expanduser("~/.cloudhome.json")
LOG_FILENAME = "/tmp/cloudhome.log"


def main():
    continuously_sync()


def continuously_sync():
    while True:
        sync_cloudhome()
        time.sleep(15)


def sync_cloudhome():
    config = Config(read_json(CLOUDHOME_CONFIG))
    configure_logging(config.log_file)
    session = boto3.Session(profile_name = config.credential_profile)
    s3 = session.client('s3')

    bucket_manifest_filenames = config.bucket_manifests()
    logging.info("Opened config file {}, proceeding to sync {} buckets".format(
        CLOUDHOME_CONFIG, len(bucket_manifest_filenames)))

    for bucket_manifest in (read_json(fn) for fn in bucket_manifest_filenames):
        sync_bucket(s3, bucket_manifest)

    logging.info("Finished syncing...".format(CLOUDHOME_CONFIG))


def sync_bucket(s3, manifest):
    logging.info("Beginning sync for {}".format(manifest.get('root')))

    conditional_bidirectional_sync(s3, manifest)

    logging.info("Done with sync for {}".format(manifest.get('root')))


def configure_logging(log_file):
    logging.basicConfig(
        filename = log_file,
        level = logging.INFO,
        format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )


def conditional_bidirectional_sync(s3, manifest):
    bucket = manifest['bucket_name']
    root = os.path.expanduser(manifest.get('root'))
    manifest_filename = os.path.join(root, "manifest.json")

    for key, metadata in manifest['items'].items():
        sync_down_metadata(s3, manifest, key, metadata, bucket, root, manifest_filename)
        record_local_stats(root, key, metadata)

        if metadata.get('local_etag') == metadata['s3_metadata']['etag']:
            logging.info("Short circuiting: The remote and local hashes for {} were equal.".format(key))
        else:
            sync_file_down_if_stale(s3, key, metadata, bucket, root)
            sync_file_up_if_newer(s3, key, metadata, bucket, root)

        logging.info("Completed bi-directional sync for {}".format(key))


def sync_down_metadata(s3, manifest, k, v, bucket, root, manifest_filename):
    try:
        metadata = s3.head_object(Bucket = bucket, Key = k)
    except EndpointConnectionError as e:
        logging.error("Cannot make a connection: {}".format(e))
        return
    except Exception as e:
        logging.error("Issue HEADing {} from {}; error {}, code {}".format(k, bucket, e, e.response['Error']['Code']))
        return

    latest_metadata = {
        'last-modified': timegm(time.strptime(metadata['ResponseMetadata']['HTTPHeaders']['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')),
        'etag': metadata['ResponseMetadata']['HTTPHeaders']['etag'].strip("'\""),
        'content-length': metadata['ResponseMetadata']['HTTPHeaders']['content-length']
        }

    if latest_metadata != v.get('s3_metadata', None):
        v['s3_metadata'] = latest_metadata
        write_json(manifest, manifest_filename)
        logging.info("Wrote new manifest data for {}.".format(k))
    else:
        logging.info("Metadata unchanged for {}. Wrote nothing locally.".format(k))

def record_local_stats(root, key, metadata):
    local_stats = os.stat(os.path.join(root, key))
    metadata['local_last_modified'], metadata['local_size'] = local_stats.st_mtime, local_stats.st_size
    metadata['local_etag'] = calculate_local_etag(os.path.join(root, key))


def sync_file_down_if_stale(s3, k, v, bucket, root):
    if v.get('local_last_modified', 0) < v['s3_metadata']['last-modified']:
        try:
            object = s3.download_file(bucket, k, os.path.join(root, k))
            logging.info("Downloaded object {}. Remote timestamp is {}, local was {}.".format(
                k, v['s3_metadata']['last-modified'], v['local_last_modified']))
        except Exception as e:
            logging.error("Error downloading {}: {}".format(k, e))


def sync_file_up_if_newer(s3, k, v, bucket, root):
    remote_modified_at = v['s3_metadata']['last-modified']
    local_modified_at = v.get('local_last_modified', 0)

    if remote_modified_at < local_modified_at:
        try:
            s3.upload_file(os.path.join(root, k), bucket, k)
            logging.info("Uploaded new file: {} had been locally updated.".format(k))
        except Exception as e:
            logging.error("Problem uploading {}: {}".format(k, e))


def write_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent = 4)


def read_json(manifest_path):
    with open(manifest_path, 'r') as f:
        return json.load(f)


def calculate_local_etag(path):
    with open(path, 'rb') as f:
        m = hashlib.md5()
        while True:
            data = f.read(10240)
            if len(data) == 0:
                break
            m.update(data)
        return m.hexdigest()

if __name__ == '__main__':
    main()
