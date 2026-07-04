from enum import StrEnum


class EventStatus(StrEnum):
    NEW = "new"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY_WAITING = "retry_waiting"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RunMode(StrEnum):
    NORMAL = "normal"
    REPLAY = "replay"
    REPLAY_FROM_STEP = "replay_from_step"
    EDIT_REPLAY = "edit_replay"
    DRY_RUN = "dry_run"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DRY_RUN_SUCCESS = "dry_run_success"
    DRY_RUN_FAILED = "dry_run_failed"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


class ArtifactType(StrEnum):
    RAW_PAYLOAD = "raw_payload"
    CANONICAL_PAYLOAD = "canonical_payload"
    VALIDATION_RESULT = "validation_result"
    MAPPED_PAYLOAD = "mapped_payload"
    OUTGOING_REQUEST = "outgoing_request"
    INCOMING_RESPONSE = "incoming_response"
    ERROR_DETAILS = "error_details"
    DRY_RUN_REQUEST = "dry_run_request"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class IncidentSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthComponentType(StrEnum):
    CONNECTOR = "connector"
    SITE = "site"
    AGENT = "agent"
    QUEUE = "queue"
    NOTIFICATION_CHANNEL = "notification_channel"
    DATABASE = "database"


class HealthStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    DOWN = "down"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class NotificationTriggerType(StrEnum):
    EVENT_FAILED = "event_failed"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    HEALTH_DOWN = "health_down"
    QUEUE_THRESHOLD = "queue_threshold"
    DAILY_REPORT = "daily_report"


class NotificationDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED_COOLDOWN = "skipped_cooldown"


class ConnectorDirection(StrEnum):
    SOURCE = "source"
    TARGET = "target"
    BIDIRECTIONAL = "bidirectional"


class ConnectorInstanceStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    UNKNOWN = "unknown"


class PollingJobStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


class PollingCursorType(StrEnum):
    NONE = "none"
    UPDATED_AT = "updated_at"
    SKIP = "skip"
    CUSTOM = "custom"


class PrintJobStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PRINTING = "printing"
    PARTIALLY_SENT = "partially_sent"
    SENT = "sent"
    PARTIALLY_PRINTED = "partially_printed"
    PRINTED = "printed"
    ERROR = "error"
    CANCELLED = "cancelled"


class PrintLineStatus(StrEnum):
    NEW = "new"
    RESERVED = "reserved"
    TEST_MODE = "test_mode"
    SENT_TO_PRINTER = "sent_to_printer"
    PRINTED = "printed"
    ERROR = "error"
    RETURN_TO_PRINT = "return_to_print"
    CANCELLED = "cancelled"


class IntegrationMessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


class IntegrationMessageStatus(StrEnum):
    RECEIVED = "received"
    PARSED = "parsed"
    ROUTED = "routed"
    SENT = "sent"
    FAILED = "failed"
    RETRY_WAITING = "retry_waiting"
    ARCHIVED = "archived"
