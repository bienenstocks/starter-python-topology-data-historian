import logging
import ibm_boto3
from ibm_botocore.client import Config


class ObjectStorageSink:
    def __init__(self, attributes):
        self.attributes = attributes
        self.values = []

        # ibm cos client initialization
        cos_endpoint = 'https://s3-api.us-geo.objectstorage.softlayer.net'
        api_key = 'SlLQ580aUDMQnjlXa_vjaH0998Jz2AMUwQCk_jGiuVP-'
        service_instance_id = 'crn:v1:bluemix:public:cloud-object-storage:global:a/f730dc759b4c3f320e480cec27def0d9:a88a9266-0500-4f49-a483-f901bba5b1b0::'
        cos_auth_endpoint = 'https://iam.ng.bluemix.net/oidc/token'
        self.cos_client = ibm_boto3.resource('s3',
                                             ibm_api_key_id=api_key,
                                             ibm_service_instance_id=service_instance_id,
                                             ibm_auth_endpoint=cos_auth_endpoint,
                                             config=Config(signature_version='oauth'),
                                             endpoint_url=cos_endpoint)

        # self.cos_client.Bucket('data_historian_bucket').create(
        #     CreateBucketConfiguration={
        #         "LocationConstraint": 'us-geo'
        #     }
        # )

        for bucket in self.cos_client.buckets.all():
            logging.error(bucket.name)

    def __call__(self, tuple):
        self.values.append(tuple)
        if len(self.values) == 100:
            logging.error(len(self.values))
