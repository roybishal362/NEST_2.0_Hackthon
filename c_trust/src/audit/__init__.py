"""
Audit Trail Module for C-TRUST
==============================
Provides comprehensive, immutable audit logging for all system operations,
user actions, and agent decisions.

Key Components:
- AuditTrailManager: Central audit trail management
- AuditEvent: Immutable audit event records
- AuditQuery: Query and reporting interface

**Validates: Requirements 7.3, 10.3**
"""

from .audit_trail import (
    AuditTrailManager,
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditReport,
)

__all__ = [
    "AuditTrailManager",
    "AuditEvent",
    "AuditEventType",
    "AuditQuery",
    "AuditReport",
]
