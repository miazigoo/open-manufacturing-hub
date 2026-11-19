"""Convenience import of all SQLAlchemy declarative models so that Base.metadata contains the full schema."""

from app.artifacts.models import Artifact  # noqa: F401
from app.audit.models import AuditEvent  # noqa: F401
from app.business_rules.models import BusinessRuleSet  # noqa: F401
from app.change_sets.models import ChangeSet, ChangeSetItem  # noqa: F401
from app.chz_aggregations.models import ChzAggregationRegistration  # noqa: F401
from app.config_versions.models import ConfigVersion  # noqa: F401
from app.connectors.models import ConnectorInstance  # noqa: F401
from app.core.database import Base, async_session, engine  # noqa: F401
from app.data_contracts.models import DataContract  # noqa: F401
from app.data_inbox.models import InboxRecord, InboxTemplate  # noqa: F401
from app.environments.models import EnvironmentProfile, EnvironmentVariable  # noqa: F401
from app.events.models import EventRun, EventStep, IntegrationEvent  # noqa: F401
from app.enterprise_runtime.models import (  # noqa: F401
    BusinessRuleDefinition,
    CanonicalBusinessObject,
    DeadLetterQueueItem,
    IntegrationQueueMessage,
    ODataCacheEntry,
    QueueAttempt,
    ResolverDefinition,
)
from app.external_errors.models import ExternalErrorRecord  # noqa: F401
from app.federation.models import FederationSyncRun  # noqa: F401
from app.health.models import AgentHeartbeat, HealthCheck, Site  # noqa: F401
from app.incidents.models import Incident, IncidentEvent  # noqa: F401
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate  # noqa: F401
from app.integration_flows.models import IntegrationFlow  # noqa: F401
from app.integration_master.models import IntegrationMasterDraft  # noqa: F401
from app.maintenance.models import MaintenanceWindow  # noqa: F401
from app.mapping_center.models import MappingProfile  # noqa: F401
from app.mappings.models import MappingDefinition, MappingVersion  # noqa: F401
from app.marking_code_pools.models import MarkingCodePoolExport, MarkingCodePoolRoutingRule  # noqa: F401
from app.notifications.models import NotificationDelivery, NotificationRule  # noqa: F401
from app.onboarding.models import OnboardingState  # noqa: F401
from app.onec_workbench.models import IntegrationMessage  # noqa: F401
from app.operation_catalog.models import OperationProfile  # noqa: F401
from app.operation_templates.models import OperationTemplate  # noqa: F401
from app.packages.models import InstalledPackage, PackageRuntimeCapability  # noqa: F401
from app.packages_auth.models import AuthRecoveryKey, AuthSession, AuthSettings, AuthUser  # noqa: F401
from app.polling.models import PollingJob, PollingJobRun, SourceEventCursor  # noqa: F401
from app.printing.models import PrintJob, PrintJobLine, PrintJobLog, PrintPrinter  # noqa: F401
from app.production.models import BackupRecord, ProductionState  # noqa: F401
from app.resolvers.models import ResolverCacheEntry, ResolverDefinitionV2  # noqa: F401
from app.secrets.models import Secret  # noqa: F401
from app.test_console.models import SavedTestCase  # noqa: F401
from app.workflows.models import Workflow  # noqa: F401
