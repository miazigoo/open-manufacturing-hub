class ConnectorError(Exception):
    pass


class ConnectorNotFoundError(ConnectorError):
    pass


class ConnectorConfigError(ConnectorError):
    pass
