from data_sources import DataSource

class ExampleDataSource(DataSource):
    def __init__(self, example):
        self.example = example

    def test(self):
        print('testing example')

    def handle(self, ki, binding_set):
        result_bindings = []
        binding = dict()
        for variable in ki['vars']:
            binding[variable] = f'<{self.example}>'
        result_bindings.append(binding)
        return result_bindings
