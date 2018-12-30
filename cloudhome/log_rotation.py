import os
import time
import logging

LOG_ROTATION_CHECK_FREQUENCY_IN_HERTZ = 1/64
LOG_SIZE_THRESHOLD_IN_MB = 128

def passively_rotate_logs(log_filename, logger_name):
    logger = logging.getLogger(logger_name)

    while True:
        rotate_log_if_too_large(log_filename, logger)
        time.sleep(LOG_ROTATION_CHECK_FREQUENCY_IN_HERTZ ** -1)

def rotate_log_if_too_large(log_filename, logger):
    if log_file_is_too_large(log_filename):
        # this will overwrite the previously archived log file.
        # that's OK. in fact, it's the behavior we want.
        # (since our log file always has the same name)
        os.rename(log_filename, log_filename + ".archived")
        logger.info("Rotating the log file {}. It's too large.".format(log_filename))
    else:
        logger.info("Checked the log file. It's only {} MB. Not doing anything.".format(
            size_of_file_in_mb(log_filename)))

def log_file_is_too_large(filename):
    return size_of_file_in_mb(filename) > LOG_SIZE_THRESHOLD_IN_MB

def size_of_file_in_mb(filename):
    return bytes_to_mb(os.path.getsize(filename))

def bytes_to_mb(bytes_qty):
    return bytes_qty // 1024 // 1024

def main():
    print(size_of_file_in_mb("/tmp/cloudhome.log"))
    print(log_file_is_too_large("/tmp/cloudhome.log"))
    rotate_log_if_too_large("/tmp/cloudhome.log")

if __name__ == '__main__':
    main()
