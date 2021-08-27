class DataSource:
    def test(self):
        raise NotImplementedError("Please implement this abstract method.")
    def handle(self, ki, binding_set):
        raise NotImplementedError("Please implement this abstract method.")
