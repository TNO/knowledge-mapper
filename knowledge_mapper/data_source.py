class DataSource:
    def test(self):
        raise NotImplementedError("Please implement this abstract method.")
    def handle(self, ki, binding_set):
        raise NotImplementedError("Please implement this abstract method.")

    def set_tke_client(self, tke_client):
        self.tke_client = tke_client
