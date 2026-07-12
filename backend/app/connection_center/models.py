from app.connectors.models import ConnectorInstance

# Connection Profile is a user-facing projection over connector_instances.
# Keeping connector_instances as the storage model preserves legacy connectors,
# OData Explorer, CHZ settings and existing integration drafts.

__all__ = ["ConnectorInstance"]
