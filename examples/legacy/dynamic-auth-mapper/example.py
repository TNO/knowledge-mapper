from src.data_source import DataSource

class ExampleDataSource(DataSource):
    def __init__(self, argument):
        print(argument)

    def test(self):
        print('testing example')

    def handle(self, ki, binding_set, requesting_kb):
        result_bindings = []
        binding = dict()
        binding['tree'] = '<http://example.org/dynamically-secured-maple>'
        binding['height'] = '"48"^^<http://www.w3.org/2001/XMLSchema#integer>'
        binding['name'] = '"Dynamically secured Maple"'
        result_bindings.append(binding)
        return result_bindings
