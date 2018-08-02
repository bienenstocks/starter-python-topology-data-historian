class TupleToCsv:
    def __init__(self, attributes_order):
        self.attributes_order = attributes_order

    def __call__(self, tuple):
        csv_line = ""
        for attribute in self.attributes_order:
            csv_line += str(tuple[attribute]) + ","
        return csv_line
