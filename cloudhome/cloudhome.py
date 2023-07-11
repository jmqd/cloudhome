#!/usr/bin/env python3

import boto3
from botocore.exceptions import EndpointConnectionError
import logging
import threading
import logging.handlers
import hashlib
import time
import sys
from cloudhome.config import Config
from cloudhome.log_rotation import passively_rotate_logs
from calendar import timegm
import json
import os

APP_NAME = "cloudhome"
CLOUDHOME_CONFIG = os.path.expanduser("~/.cloudhome.json")
LOG_FILENAME = "/tmp/cloudhome.log"
SYNC_FREQUENCY_IN_HERTZ = 1
MANIFEST_FILE_BASENAME = "manifest.json"
S3_ETAG_HASHING_BLOCK_SIZE = 10240


def main():
    config = Config(read_json(CLOUDHOME_CONFIG))
    configure_app(config)
    spawn_background_tasks(config)
    continuously_sync(config)


def spawn_background_tasks(config):
    log_rotation = threading.Thread(
        target=passively_rotate_logs, args=(config.log_file, APP_NAME)
    )

    log_rotation.start()


def continuously_sync(config):
    while True:
        sync_cloudhome(config)

        # we get the inverse of the hertz to determine the seconds to sleep
        time.sleep(int(SYNC_FREQUENCY_IN_HERTZ**-1))


def configure_app(config):
    configure_logging(config.log_file)


def sync_cloudhome(config):
    """The main routine. Finds all "cloudhomes" and syncs them."""
    session = boto3.Session(profile_name=config.credential_profile)
    s3 = session.client("s3")

    # Gross. Factor it out later.
    global log
    log = logging.getLogger(APP_NAME)

    bucket_manifest_filenames = config.bucket_manifests()
    log.debug(
        "Opened config file {}, proceeding to sync {} buckets".format(
            CLOUDHOME_CONFIG, len(bucket_manifest_filenames)
        )
    )

    try:
        sync_all_buckets(s3, bucket_manifest_filenames)
        log.debug(
            "Successfully synchronized all buckets ({}).".format(
                bucket_manifest_filenames
            )
        )
    except EndpointConnectionError as e:
        log.warn(
            "Constant back-off of 10 seconds sleeping. Cannot reach AWS: {}".format(e)
        )
        time.sleep(10)
    except Exception as e:
        log.error("Fatal crash: {}".format(e))
        sys.exit(1)


def sync_all_buckets(s3, bucket_manifest_filenames):
    # TODO: These IO-driven tasks (syncing buckets) are all done serially.
    # TODO: Consider submitting these tasks to a threadpool to concurrently execute?
    for bucket_manifest in (read_json(fn) for fn in bucket_manifest_filenames):
        sync_bucket(s3, bucket_manifest)


def sync_bucket(s3, manifest):
    log.debug("Beginning sync for {}".format(manifest.get("root")))
    conditional_bidirectional_sync(s3, manifest)
    log.debug("Done with sync for {}".format(manifest.get("root")))


def configure_logging(log_file):
    log = logging.getLogger(APP_NAME)
    log.setLevel(logging.INFO)
    file_handler = logging.handlers.WatchedFileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    file_handler.setLevel(logging.INFO)
    log.addHandler(file_handler)


def conditional_bidirectional_sync(s3, manifest):
    """
    Given a manifest for a specific sync'd directory root & s3 bucket,
    sync them. "Bidirectional" because new remote changes are pulled
    down if the local is stale, and new local changes are pushed up to
    the s3 bucket if the remote is stale.
    """
    bucket = manifest["bucket_name"]
    root = os.path.expanduser(manifest.get("root"))
    manifest_filename = os.path.join(root, MANIFEST_FILE_BASENAME)
    sync_manifest(manifest_filename, bucket, s3, root)

    # TODO: Syncing all items in the manifest is performed serially.
    # TODO: Considering submitting these to a threadpool for concurrent IO ops.
    for key, metadata in manifest["items"].items():
        sync_down_metadata(s3, manifest, key, metadata, bucket, root, manifest_filename)

        # small weirdness here -- can pull false metadata info from s3 (refreshing manfiest)
        # then "correct" it here. This is necessary regardless, but important to call out the
        # abstract "race condition"
        record_local_stats(root, key, metadata)
        bidirectionally_sync_file(key, metadata, bucket, root, s3)


def bidirectionally_sync_file(key, metadata, bucket, root, s3):
    """
    If the remote and local files have different hashes, the file
    with the greater timestamp overwrites the other file.
    """
    if remote_and_local_hashes_are_equal(metadata):
        log.debug(
            "Short circuiting: The remote and local hashes for {} were equal.".format(
                key
            )
        )
    else:
        sync_file_down_if_stale(s3, key, metadata, bucket, root)
        sync_file_up_if_newer(s3, key, metadata, bucket, root)
        log.debug("Completed bi-directional sync for {}".format(key))


def sync_manifest(manifest_filename, bucket, s3, root):
    """
    Note:
        Syncing the metadata also gets all of the locally cached information,
        possibly reflecting the local state of another machine. Since we never
        trust this cached info and always re-caclulate the local stats when syncing,
        should we consider simply removing that cache of the local stats? Technically
        speaking, it's only ever possible for it to be inaccurate while this program
        is running, after syncing the remote manifest but before re-writing the manifest.
    """
    remote_metadata = get_remote_metadata(
        s3, os.path.basename(manifest_filename), bucket
    )
    metadata = {"s3_metadata": remote_metadata}
    record_local_stats(root, manifest_filename, metadata)
    bidirectionally_sync_file(
        os.path.basename(manifest_filename), metadata, bucket, root, s3
    )


def sync_down_metadata(s3, manifest, k, v, bucket, root, manifest_filename):
    """Gets the remote metadata from S3 and writes it to the local manifest file."""
    latest_metadata = get_remote_metadata(s3, k, bucket)

    if latest_metadata is None:
        return
    elif latest_metadata != v.get("s3_metadata", None):
        v["s3_metadata"] = latest_metadata
        write_manifest(manifest, manifest_filename)
        log.info("Wrote new manifest data for {}.".format(k))
    else:
        log.debug("Metadata unchanged for {}. Wrote nothing locally.".format(k))


def get_remote_metadata(s3, key, bucket):
    """Returns the remote S3 metadata for a given object.
    - If HEAD OBJECT 404s, we return sane defaults for the metadata.
    - For any other error, `None` is returned.
    """
    try:
        metadata = s3.head_object(Bucket=bucket, Key=key)
    except EndpointConnectionError as e:
        log.error("Cannot make a connection: {}".format(e))
        raise
    except Exception as e:
        log.error(
            "Issue HEADing {} from {}; error {}, code {}".format(
                key, bucket, e, e.response["Error"]["Code"]
            )
        )

        if e.response["Error"]["Code"] == "404":
            return {"last-modified": 0, "etag": None, "content-length": None}
        else:
            return

    return {
        "last-modified": timegm(
            time.strptime(
                metadata["ResponseMetadata"]["HTTPHeaders"]["last-modified"],
                "%a, %d %b %Y %H:%M:%S %Z",
            )
        ),
        "etag": metadata["ResponseMetadata"]["HTTPHeaders"]["etag"].strip("'\""),
        "content-length": metadata["ResponseMetadata"]["HTTPHeaders"]["content-length"],
    }


def record_local_stats(root, key, metadata):
    """Populates a `metadata` dictionary with the local stats for a given file."""
    mtime, st_size, local_etag = calculate_local_stats(root, key)
    metadata["local_last_modified"], metadata["local_size"] = mtime, st_size
    metadata["local_etag"] = local_etag


def calculate_local_stats(root, key):
    try:
        local_stats = os.stat(os.path.join(root, key))
        return (
            local_stats.st_mtime,
            local_stats.st_size,
            calculate_local_etag(os.path.join(root, key)),
        )
    except FileNotFoundError as e:
        log.info(
            "{} wasn't found. Returning 0, 0, None. Probably a new file.".format(key)
        )
        return 0, 0, None


def sync_file_down_if_stale(s3, k, v, bucket, root):
    if v.get("local_last_modified", 0) < v["s3_metadata"]["last-modified"]:
        try:
            object = s3.download_file(bucket, k, os.path.join(root, k))
            log.info(
                "Downloaded object {}. Remote timestamp is {}, local was {}.".format(
                    k, v["s3_metadata"]["last-modified"], v["local_last_modified"]
                )
            )
        except Exception as e:
            log.error("Error downloading {}: {}".format(k, e))


def sync_file_up_if_newer(s3, k, v, bucket, root):
    remote_modified_at = v["s3_metadata"].get("last-modified", 0)
    local_modified_at = v.get("local_last_modified", 0)

    if remote_modified_at < local_modified_at:
        try:
            s3.upload_file(os.path.join(root, k), bucket, k)
            log.info("Uploaded new file: {} had been locally updated.".format(k))
        except Exception as e:
            log.error("Problem uploading {}: {}".format(k, e))


def write_manifest(manifest, manifest_filename):
    new_manifest = manifest.copy()
    new_manifest["items"] = {
        k: {"s3_metadata": v.get("s3_metadata", {})}
        for k, v in manifest["items"].items()
    }
    write_json(new_manifest, manifest_filename)


def write_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def read_json(manifest_path):
    with open(manifest_path, "r") as f:
        return json.load(f)


def remote_and_local_hashes_are_equal(metadata):
    return metadata["s3_metadata"]["etag"] == metadata.get("local_etag")


def calculate_local_etag(path):
    """
    This is a proxy of S3s implementation to calculate the etag for
    single-part objects.

    Note that multi-part uploaded objects will hash differently than this
    function on S3s service, so we cannot rely on hash comparisons if the
    S3 object was multi-part uploaded.

    The intended use-case of this tool is for relatively small text files,
    not large media or data files, so we're OK with accepting this design
    limitation for now.
    """
    with open(path, "rb") as f:
        m = hashlib.md5()
        while True:
            data = f.read(S3_ETAG_HASHING_BLOCK_SIZE)
            if len(data) == 0:
                break
            m.update(data)
        return m.hexdigest()


if __name__ == "__main__":
    main()
