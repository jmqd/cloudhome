#!/usr/bin/env python3
import boto3
import logging
import hashlib
import time
from calendar import timegm
import json
import os

LOCAL_DIR = os.path.expanduser("~/cloud/mcqueen.jordan")
LOCAL_MANIFEST = os.path.join(LOCAL_DIR, ".manifest.json")
session = boto3.Session(profile_name = 'mcqueen.jordan')

def main():
    logging.basicConfig(filename="/tmp/cloudhome.log", level = logging.INFO)
    s3 = session.client('s3')
    manifest = read_json(LOCAL_MANIFEST)
    conditional_bidirectional_sync(s3, manifest)


def conditional_bidirectional_sync(s3, manifest):
    bucket = manifest['bucket_name']
    for k, v in manifest['items'].items():
        sync_down_metadata(s3, manifest, k, v, bucket)

        if v['local_etag'] == v['s3_metadata']['etag']:
            logging.info("Short circuiting: The remote and local hashes for {} were equal.".format(k))
        else:
            sync_file_down_if_stale(s3, k, v, bucket)
            sync_file_up_if_newer(s3, k, v, bucket)

        logging.info("Completed bi-directional sync for {}".format(k))


def sync_down_metadata(s3, manifest, k, v, bucket):
    try:
        metadata = s3.head_object(Bucket = bucket, Key = k)
    except Exception as e:
        logging.error("Issue HEADing {} from {}; error {}, code {}".format(k, bucket, e, e.response['Error']['Code']))
        return

    latest_metadata = {
        'last-modified': timegm(time.strptime(metadata['ResponseMetadata']['HTTPHeaders']['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')),
        'etag': metadata['ResponseMetadata']['HTTPHeaders']['etag'].strip("'\""),
        'content-length': metadata['ResponseMetadata']['HTTPHeaders']['content-length']
        }

    if latest_metadata != v['s3_metadata']:
        v['s3_metadata'] = latest_metadata
        write_json(manifest, LOCAL_MANIFEST)
        logging.info("Wrote new manifest data for {}.".format(k))
    else:
        logging.info("Metadata unchanged for {}. Wrote nothing locally.".format(k))

    local_stats = os.stat(os.path.join(LOCAL_DIR, k))
    v['local_last_modified'], v['local_size'] = local_stats.st_mtime, local_stats.st_size
    v['local_etag'] = calculate_local_etag(os.path.join(LOCAL_DIR, k))


def sync_file_down_if_stale(s3, k, v, bucket):
    if v['local_last_modified'] < v['s3_metadata']['last-modified']:
        try:
            object = s3.download_file(bucket, k, os.path.join(LOCAL_DIR, k))
            logging.info("Downloaded object {}. Remote timestamp is {}, local was {}.".format(
                k, v['s3_metadata']['last-modified'], v['local_last_modified']))
        except Exception as e:
            logging.error("Error downloading {}: {}".format(k, e))


def sync_file_up_if_newer(s3, k, v, bucket):
    remote_modified_at = v['s3_metadata']['last-modified']
    local_modified_at = v['local_last_modified']

    if remote_modified_at < local_modified_at:
        try:
            s3.upload_file(os.path.join(LOCAL_DIR, k), bucket, k)
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
