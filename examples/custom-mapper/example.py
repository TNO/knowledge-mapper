from knowledge_mapper.data_source import DataSource

class ExampleDataSource(DataSource):
    def __init__(self, argument):
        print(argument)

    def test(self):
        print('testing example')

    def handle(self, ki, binding_set, requesting_kb):
        result_bindings = []
        binding = dict()
        binding['tree'] = '<http://example.org/maple>'
        binding['height'] = '44'
        binding['name'] = '"Maple"'
        result_bindings.append(binding)
        return result_bindings
