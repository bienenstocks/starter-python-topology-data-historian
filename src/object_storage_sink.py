import logging


class ObjectStorageSink:
    def __init__(self, attributes):
        self.attributes = attributes
        self.values = []

    def __call__(self, tuple):
        self.values.append(tuple)
        if len(self.values) == 100:
            logging.info("flush to COS")
            self.values.clear()
