from requests.models import Response


class UnexpectedHttpResponseError(Exception):
    def __init__(self, response: Response):
        super().__init__(
            f"Unexpected response from {response.url} with status "
            f'{response.status_code} and body "{response.text}".'
        )


class KnowledgeEngineNotAvailableError(Exception):
    def __init__(self, ke_url: str):
        super().__init__(f"KE runtime at {ke_url} is not available.")


class SmartConnectorNotFoundError(Exception):
    def __init__(self, kb_id: str, ke_url: str):
        super().__init__(
            f"Smart Connector for KB '{kb_id}' not found in KE runtime at {ke_url}."
        )
