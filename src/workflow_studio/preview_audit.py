"""Safe preview audit intents; no audit writer is included."""
from dataclasses import dataclass
from enum import Enum
from .contracts import StudioContract, optional_id, safe_code, stable_id, utc_timestamp
from .preview_results import WorkflowPreviewStatus

class WorkflowPreviewAuditEventType(str,Enum):
    PREVIEW_REQUESTED="preview_requested"; PREVIEW_VALIDATION_BLOCKED="preview_validation_blocked"; PREVIEW_STARTED="preview_started"; PREVIEW_COMPLETED="preview_completed"; PREVIEW_FAILED="preview_failed"; PREVIEW_LIMIT_EXCEEDED="preview_limit_exceeded"; PREVIEW_UNAVAILABLE="preview_unavailable"

@dataclass(frozen=True,slots=True)
class WorkflowPreviewAuditIntent(StudioContract):
    event_type:WorkflowPreviewAuditEventType; tenant_id:str; workflow_id:str; version_id:str; actor_id:str; fixture_label:str; status:WorkflowPreviewStatus; reason_code:str; occurred_at:str; correlation_id:str|None=None
    def __post_init__(self):
        object.__setattr__(self,"event_type",self.event_type if isinstance(self.event_type,WorkflowPreviewAuditEventType) else WorkflowPreviewAuditEventType(self.event_type))
        for n in ("tenant_id","workflow_id","version_id","actor_id","fixture_label"): object.__setattr__(self,n,stable_id(getattr(self,n),n))
        object.__setattr__(self,"status",self.status if isinstance(self.status,WorkflowPreviewStatus) else WorkflowPreviewStatus(self.status)); object.__setattr__(self,"reason_code",safe_code(self.reason_code,"reason_code")); object.__setattr__(self,"occurred_at",utc_timestamp(self.occurred_at,"occurred_at")); object.__setattr__(self,"correlation_id",optional_id(self.correlation_id,"correlation_id"))
