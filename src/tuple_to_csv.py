class TupleToCsv:
    def __init__(self, attributes_order):
        self.attributes_order = attributes_order

    def __call__(self, tuple):
        ret = ""
        for attribute in self.attributes_order:
            ret += str(tuple[attribute]) + ","
        return ret
