from requests.models import Response

class UnexpectedHttpResponseError(Exception):
    def __init__(self, response: Response):
        super().__init__(f'Unexpected response from {response.url} with status {response.status_code} and body "{response.text}".')
