import boto3
from botocore.exceptions import EndpointConnectionError
import logging
import hashlib
import time
import sys
from config import Config
from calendar import timegm
import json
import watchdog
import os

CLOUDHOME_CONFIG = os.path.expanduser("~/.cloudhome.json")
LOG_FILENAME = "/tmp/cloudhome.log"
SYNC_FREQUENCY_IN_HERTZ = 1/5


def main():
    continuously_sync()


def continuously_sync():
    while True:
        sync_cloudhome()

        # we get the inverse of the hertz to determine the seconds to sleep
        time.sleep(int(SYNC_FREQUENCY_IN_HERTZ ** -1))


def sync_cloudhome():
    config = Config(read_json(CLOUDHOME_CONFIG))
    configure_logging(config.log_file)
    session = boto3.Session(profile_name = config.credential_profile)
    s3 = session.client('s3')

    bucket_manifest_filenames = config.bucket_manifests()
    logging.info("Opened config file {}, proceeding to sync {} buckets".format(
        CLOUDHOME_CONFIG, len(bucket_manifest_filenames)))

    try:
        sync_all_buckets(s3, bucket_manifest_filenames)
    except Exception as e:
        logging.error("Fatal crash: {}".format(e))
        sys.exit(1)

    logging.info("Finished syncing...".format(CLOUDHOME_CONFIG))


def sync_all_buckets(s3, bucket_manifest_filenames):
    for bucket_manifest in (read_json(fn) for fn in bucket_manifest_filenames):
        sync_bucket(s3, bucket_manifest)


def sync_bucket(s3, manifest):
    logging.debug("Beginning sync for {}".format(manifest.get('root')))
    conditional_bidirectional_sync(s3, manifest)
    logging.debug("Done with sync for {}".format(manifest.get('root')))


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
    sync_manifest(manifest_filename, bucket, s3, root)

    for key, metadata in manifest['items'].items():
        sync_down_metadata(s3, manifest, key, metadata, bucket, root, manifest_filename)

        # small weirdness here -- can pull false metadata info from s3 (refreshing manfiest)
        # then "correct" it here. This is necessary regardless, but important to call out the
        # abstract "race condition"
        record_local_stats(root, key, metadata)
        bidirectionally_sync_file(key, metadata, bucket, root, s3)


def bidirectionally_sync_file(key, metadata, bucket, root, s3):
        if remote_and_local_hashes_are_equal(metadata):
            logging.debug("Short circuiting: The remote and local hashes for {} were equal.".format(key))
        else:
            sync_file_down_if_stale(s3, key, metadata, bucket, root)
            sync_file_up_if_newer(s3, key, metadata, bucket, root)
        logging.debug("Completed bi-directional sync for {}".format(key))


def sync_manifest(manifest_filename, bucket, s3, root):
    '''
    Note:
        Syncing the metadata also gets all of the locally cached information,
        possibly reflecting the local state of another machine. Since we never
        trust this cached info and always re-caclulate the local stats when syncing,
        should we consider simply removing that cache of the local stats? Technically
        speaking, it's only ever possible for it to be inaccurate while this program
        is running, after syncing the remote manifest but before re-writing the manifest.
    '''
    remote_metadata = get_remote_metadata(s3, os.path.basename(manifest_filename), bucket)
    metadata = {'s3_metadata': remote_metadata}
    record_local_stats(root, manifest_filename, metadata)
    bidirectionally_sync_file(os.path.basename(manifest_filename), metadata, bucket, root, s3)


def sync_down_metadata(s3, manifest, k, v, bucket, root, manifest_filename):
    latest_metadata = get_remote_metadata(s3, k, bucket)

    if latest_metadata is None:
        return
    elif latest_metadata != v.get('s3_metadata', None):
        v['s3_metadata'] = latest_metadata
        write_json(manifest, manifest_filename)
        logging.info("Wrote new manifest data for {}.".format(k))
    else:
        logging.debug("Metadata unchanged for {}. Wrote nothing locally.".format(k))


def get_remote_metadata(s3, key, bucket):
    try:
        metadata = s3.head_object(Bucket = bucket, Key = key)
    except EndpointConnectionError as e:
        logging.error("Cannot make a connection: {}".format(e))
        return
    except Exception as e:
        logging.error("Issue HEADing {} from {}; error {}, code {}".format(key, bucket, e, e.response['Error']['Code']))
        return

    return {
        'last-modified': timegm(time.strptime(metadata['ResponseMetadata']['HTTPHeaders']['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')),
        'etag': metadata['ResponseMetadata']['HTTPHeaders']['etag'].strip("'\""),
        'content-length': metadata['ResponseMetadata']['HTTPHeaders']['content-length']
        }


def record_local_stats(root, key, metadata):
    mtime, st_size, local_etag = calculate_local_stats(root, key)
    metadata['local_last_modified'], metadata['local_size'] = mtime, st_size
    metadata['local_etag'] = local_etag


def calculate_local_stats(root, key):
    try:
        local_stats = os.stat(os.path.join(root, key))
        return local_stats.st_mtime, local_stats.st_size, calculate_local_etag(os.path.join(root, key))
    except FileNotFoundError as e:
        logging.warn("Local file wasn't found. Returning 0, 0, None. It's probably a new file to download.")
        return 0, 0, None


def sync_file_down_if_stale(s3, k, v, bucket, root):
    if v.get('local_last_modified', 0) < v['s3_metadata']['last-modified']:
        try:
            object = s3.download_file(bucket, k, os.path.join(root, k))
            logging.info("Downloaded object {}. Remote timestamp is {}, local was {}.".format(
                k, v['s3_metadata']['last-modified'], v['local_last_modified']))
        except Exception as e:
            logging.error("Error downloading {}: {}".format(k, e))

def sync_file_up_if_newer(s3, k, v, bucket, root):
    remote_modified_at = v['s3_metadata'].get('last-modified', 0)
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


def remote_and_local_hashes_are_equal(metadata):
    return metadata['s3_metadata']['etag'] == metadata.get('local_etag')


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
