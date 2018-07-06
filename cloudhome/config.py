import os

MANIFEST_FILENAME = 'manifest.json'

class Config:
    def __init__(self, data):
        self.cloudhome = os.path.expanduser(data.get('cloudhome', None))
        self.bucket_names = data.get('bucket_names', [])
        self.log_file = os.path.expanduser(data.get('log_file', '/tmp/cloudhome.log'))
        self.credential_profile = data.get('credential_profile')

    def bucket_manifests(self):
        return [os.path.join(self.cloudhome, x, MANIFEST_FILENAME) for x in self.bucket_names]
