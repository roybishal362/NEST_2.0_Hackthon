"""
C-TRUST Versioned Configuration Management System
=================================================
Provides configuration management with version control, human approval
workflow, and change history tracking.

Key Features:
- Versioned configuration with semantic versioning
- Human approval workflow for all changes
- Complete change history tracking
- No automatic self-modification in production

**Validates: Requirements 8.1, 8.2, 8.5**

Design Principles:
- All configuration changes require human approval
- Complete audit trail of all changes
- Version control with rollback capability
- Never implement automatic learning or self-modification
"""

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid
import yaml
import copy

from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# ENUMERATIONS
# ========================================

class ConfigChangeStatus(str, Enum):
    """Status of a configuration change request"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    ROLLED_BACK = "ROLLED_BACK"


class ConfigChangeType(str, Enum):
    """Type of configuration change"""
    THRESHOLD_UPDATE = "THRESHOLD_UPDATE"
    WEIGHT_UPDATE = "WEIGHT_UPDATE"
    RULE_UPDATE = "RULE_UPDATE"
    AGENT_CONFIG = "AGENT_CONFIG"
    DQI_CONFIG = "DQI_CONFIG"
    GUARDIAN_CONFIG = "GUARDIAN_CONFIG"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"


# ========================================
# DATA STRUCTURES
# ========================================

@dataclass
class ConfigVersion:
    """
    Represents a specific version of the configuration.
    
    Attributes:
        version_id: Unique version identifier
        version_number: Semantic version string (e.g., "1.2.3")
        config_data: The configuration data at this version
        created_at: When this version was created
        created_by: User who created this version
        description: Description of changes in this version
        checksum: Hash for integrity verification
        is_active: Whether this is the currently active version
    """
    version_id: str
    version_number: str
    config_data: Dict[str, Any]
    created_at: datetime
    created_by: str
    description: str
    checksum: str = ""
    is_active: bool = False
    
    def __post_init__(self):
        """Calculate checksum after initialization"""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum for integrity verification"""
        content = json.dumps(self.config_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify configuration integrity using checksum"""
        return self.checksum == self._calculate_checksum()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "version_id": self.version_id,
            "version_number": self.version_number,
            "config_data": self.config_data,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "checksum": self.checksum,
            "is_active": self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigVersion":
        """Create ConfigVersion from dictionary"""
        return cls(
            version_id=data["version_id"],
            version_number=data["version_number"],
            config_data=data["config_data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data["created_by"],
            description=data["description"],
            checksum=data.get("checksum", ""),
            is_active=data.get("is_active", False),
        )


@dataclass
class ConfigChangeRequest:
    """
    Represents a request to change configuration.
    
    All configuration changes must go through this approval workflow.
    This ensures human oversight and prevents automatic self-modification.
    
    Attributes:
        request_id: Unique request identifier
        change_type: Type of configuration change
        config_key: Configuration key being changed
        current_value: Current value before change
        proposed_value: Proposed new value
        justification: Reason for the change
        requested_by: User requesting the change
        requested_at: When the request was made
        status: Current status of the request
        reviewed_by: User who reviewed the request (if any)
        reviewed_at: When the request was reviewed (if any)
        review_notes: Notes from the reviewer (if any)
        source: Source of the recommendation (manual, guardian, etc.)
    """
    request_id: str
    change_type: ConfigChangeType
    config_key: str
    current_value: Any
    proposed_value: Any
    justification: str
    requested_by: str
    requested_at: datetime
    status: ConfigChangeStatus = ConfigChangeStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    source: str = "manual"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "request_id": self.request_id,
            "change_type": self.change_type.value,
            "config_key": self.config_key,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "justification": self.justification,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigChangeRequest":
        """Create ConfigChangeRequest from dictionary"""
        return cls(
            request_id=data["request_id"],
            change_type=ConfigChangeType(data["change_type"]),
            config_key=data["config_key"],
            current_value=data["current_value"],
            proposed_value=data["proposed_value"],
            justification=data["justification"],
            requested_by=data["requested_by"],
            requested_at=datetime.fromisoformat(data["requested_at"]),
            status=ConfigChangeStatus(data["status"]),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            review_notes=data.get("review_notes"),
            source=data.get("source", "manual"),
        )


# ========================================
# VERSIONED CONFIGURATION MANAGER
# ========================================

class VersionedConfigManager:
    """
    Versioned Configuration Management System.
    
    Provides configuration management with:
    - Version control with semantic versioning
    - Human approval workflow for all changes
    - Complete change history tracking
    - Rollback capability
    - No automatic self-modification
    
    **Validates: Requirements 8.1, 8.2, 8.5**
    
    CRITICAL: This system NEVER implements automatic learning or
    self-modification in production. All changes require human approval.
    """
    
    def __init__(
        self,
        config_path: str = "config/system_config.yaml",
        history_path: str = "config/history",
        initial_version: str = "1.0.0",
    ):
        """
        Initialize versioned configuration manager.
        
        Args:
            config_path: Path to main configuration file
            history_path: Path to store version history
            initial_version: Initial version number
        """
        self.config_path = Path(config_path)
        self.history_path = Path(history_path)
        self.history_path.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._versions: List[ConfigVersion] = []
        self._change_requests: List[ConfigChangeRequest] = []
        self._callbacks: List[Callable[[ConfigChangeRequest], None]] = []
        
        # Load existing configuration and history
        self._load_history()
        
        # If no versions exist, create initial version
        if not self._versions:
            self._create_initial_version(initial_version)
        
        logger.info(
            f"VersionedConfigManager initialized: "
            f"{len(self._versions)} versions, "
            f"active version: {self.get_active_version().version_number}"
        )
    
    # ========================================
    # VERSION MANAGEMENT
    # ========================================
    
    def _create_initial_version(self, version_number: str) -> ConfigVersion:
        """Create initial configuration version"""
        config_data = self._load_config_file()
        
        version = ConfigVersion(
            version_id=str(uuid.uuid4()),
            version_number=version_number,
            config_data=config_data,
            created_at=datetime.now(),
            created_by="system",
            description="Initial configuration version",
            is_active=True,
        )
        
        self._versions.append(version)
        self._save_history()
        
        logger.info(f"Created initial config version: {version_number}")
        return version
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                return {}
        return {}
    
    def _save_config_file(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to YAML file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
    
    def _load_history(self) -> None:
        """Load version history from files"""
        versions_file = self.history_path / "versions.json"
        requests_file = self.history_path / "change_requests.json"
        
        if versions_file.exists():
            try:
                with open(versions_file, 'r') as f:
                    data = json.load(f)
                    self._versions = [ConfigVersion.from_dict(v) for v in data]
            except Exception as e:
                logger.error(f"Failed to load version history: {e}")
        
        if requests_file.exists():
            try:
                with open(requests_file, 'r') as f:
                    data = json.load(f)
                    self._change_requests = [ConfigChangeRequest.from_dict(r) for r in data]
            except Exception as e:
                logger.error(f"Failed to load change requests: {e}")
    
    def _save_history(self) -> None:
        """Save version history to files"""
        versions_file = self.history_path / "versions.json"
        requests_file = self.history_path / "change_requests.json"
        
        try:
            with open(versions_file, 'w') as f:
                json.dump([v.to_dict() for v in self._versions], f, indent=2)
            
            with open(requests_file, 'w') as f:
                json.dump([r.to_dict() for r in self._change_requests], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def get_active_version(self) -> ConfigVersion:
        """Get the currently active configuration version"""
        for version in self._versions:
            if version.is_active:
                return version
        
        # If no active version, return the latest
        if self._versions:
            return self._versions[-1]
        
        raise ValueError("No configuration versions available")
    
    def get_version(self, version_id: str) -> Optional[ConfigVersion]:
        """Get a specific configuration version by ID"""
        for version in self._versions:
            if version.version_id == version_id:
                return version
        return None
    
    def get_version_by_number(self, version_number: str) -> Optional[ConfigVersion]:
        """Get a specific configuration version by version number"""
        for version in self._versions:
            if version.version_number == version_number:
                return version
        return None
    
    def list_versions(self) -> List[ConfigVersion]:
        """List all configuration versions"""
        return sorted(self._versions, key=lambda v: v.created_at, reverse=True)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from the active version.
        
        Args:
            key: Dot-notation key (e.g., "dqi.weights.safety")
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        version = self.get_active_version()
        return self._get_nested_value(version.config_data, key, default)
    
    def _get_nested_value(self, data: Dict, key: str, default: Any = None) -> Any:
        """Get nested value using dot notation"""
        keys = key.split(".")
        value = data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _set_nested_value(self, data: Dict, key: str, value: Any) -> Dict:
        """Set nested value using dot notation"""
        keys = key.split(".")
        result = copy.deepcopy(data)
        current = result
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        return result

    
    # ========================================
    # CHANGE REQUEST WORKFLOW
    # ========================================
    
    def create_change_request(
        self,
        change_type: ConfigChangeType,
        config_key: str,
        proposed_value: Any,
        justification: str,
        requested_by: str,
        source: str = "manual",
    ) -> ConfigChangeRequest:
        """
        Create a configuration change request.
        
        All configuration changes must go through this approval workflow.
        This ensures human oversight and prevents automatic self-modification.
        
        Args:
            change_type: Type of configuration change
            config_key: Configuration key to change
            proposed_value: Proposed new value
            justification: Reason for the change
            requested_by: User requesting the change
            source: Source of the recommendation
        
        Returns:
            Created ConfigChangeRequest
        """
        with self._lock:
            current_value = self.get_config_value(config_key)
            
            request = ConfigChangeRequest(
                request_id=str(uuid.uuid4()),
                change_type=change_type,
                config_key=config_key,
                current_value=current_value,
                proposed_value=proposed_value,
                justification=justification,
                requested_by=requested_by,
                requested_at=datetime.now(),
                source=source,
            )
            
            self._change_requests.append(request)
            self._save_history()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(request)
                except Exception as e:
                    logger.error(f"Change request callback error: {e}")
            
            logger.info(
                f"Change request created: {request.request_id} - "
                f"{config_key}: {current_value} -> {proposed_value}"
            )
            
            return request
    
    def approve_change_request(
        self,
        request_id: str,
        reviewed_by: str,
        review_notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Approve a configuration change request.
        
        This is the human approval step required for all configuration changes.
        
        Args:
            request_id: ID of the change request
            reviewed_by: User approving the change
            review_notes: Optional notes from reviewer
        
        Returns:
            Tuple of (success, message)
        """
        with self._lock:
            request = self._get_change_request(request_id)
            if not request:
                return False, f"Change request not found: {request_id}"
            
            if request.status != ConfigChangeStatus.PENDING:
                return False, f"Change request is not pending: {request.status.value}"
            
            # Update request status
            request.status = ConfigChangeStatus.APPROVED
            request.reviewed_by = reviewed_by
            request.reviewed_at = datetime.now()
            request.review_notes = review_notes
            
            self._save_history()
            
            logger.info(
                f"Change request approved: {request_id} by {reviewed_by}"
            )
            
            return True, "Change request approved"
    
    def reject_change_request(
        self,
        request_id: str,
        reviewed_by: str,
        review_notes: str,
    ) -> Tuple[bool, str]:
        """
        Reject a configuration change request.
        
        Args:
            request_id: ID of the change request
            reviewed_by: User rejecting the change
            review_notes: Reason for rejection
        
        Returns:
            Tuple of (success, message)
        """
        with self._lock:
            request = self._get_change_request(request_id)
            if not request:
                return False, f"Change request not found: {request_id}"
            
            if request.status != ConfigChangeStatus.PENDING:
                return False, f"Change request is not pending: {request.status.value}"
            
            # Update request status
            request.status = ConfigChangeStatus.REJECTED
            request.reviewed_by = reviewed_by
            request.reviewed_at = datetime.now()
            request.review_notes = review_notes
            
            self._save_history()
            
            logger.info(
                f"Change request rejected: {request_id} by {reviewed_by} - {review_notes}"
            )
            
            return True, "Change request rejected"
    
    def apply_change_request(
        self,
        request_id: str,
        applied_by: str,
        version_description: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[ConfigVersion]]:
        """
        Apply an approved configuration change request.
        
        Creates a new configuration version with the change applied.
        
        Args:
            request_id: ID of the approved change request
            applied_by: User applying the change
            version_description: Optional description for new version
        
        Returns:
            Tuple of (success, message, new_version)
        """
        with self._lock:
            request = self._get_change_request(request_id)
            if not request:
                return False, f"Change request not found: {request_id}", None
            
            if request.status != ConfigChangeStatus.APPROVED:
                return False, f"Change request is not approved: {request.status.value}", None
            
            # Get current active version
            current_version = self.get_active_version()
            
            # Create new config with change applied
            new_config = self._set_nested_value(
                current_version.config_data,
                request.config_key,
                request.proposed_value,
            )
            
            # Calculate new version number
            new_version_number = self._increment_version(current_version.version_number)
            
            # Create new version
            description = version_description or (
                f"Applied change: {request.config_key} = {request.proposed_value}"
            )
            
            new_version = ConfigVersion(
                version_id=str(uuid.uuid4()),
                version_number=new_version_number,
                config_data=new_config,
                created_at=datetime.now(),
                created_by=applied_by,
                description=description,
                is_active=True,
            )
            
            # Deactivate current version
            current_version.is_active = False
            
            # Add new version
            self._versions.append(new_version)
            
            # Update request status
            request.status = ConfigChangeStatus.APPLIED
            
            # Save to file and history
            self._save_config_file(new_config)
            self._save_history()
            
            logger.info(
                f"Change request applied: {request_id} - "
                f"New version: {new_version_number}"
            )
            
            return True, f"Change applied, new version: {new_version_number}", new_version
    
    def _get_change_request(self, request_id: str) -> Optional[ConfigChangeRequest]:
        """Get a change request by ID"""
        for request in self._change_requests:
            if request.request_id == request_id:
                return request
        return None
    
    def _increment_version(self, version: str) -> str:
        """Increment patch version number"""
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return ".".join(parts)
        return f"{version}.1"
    
    def get_pending_requests(self) -> List[ConfigChangeRequest]:
        """Get all pending change requests"""
        return [r for r in self._change_requests if r.status == ConfigChangeStatus.PENDING]
    
    def get_change_history(
        self,
        config_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[ConfigChangeRequest]:
        """
        Get change request history.
        
        Args:
            config_key: Optional filter by config key
            limit: Maximum number of requests to return
        
        Returns:
            List of change requests
        """
        requests = self._change_requests
        
        if config_key:
            requests = [r for r in requests if r.config_key == config_key]
        
        # Sort by requested_at descending
        requests = sorted(requests, key=lambda r: r.requested_at, reverse=True)
        
        return requests[:limit]
    
    # ========================================
    # ROLLBACK CAPABILITY
    # ========================================
    
    def rollback_to_version(
        self,
        version_id: str,
        rolled_back_by: str,
        reason: str,
    ) -> Tuple[bool, str]:
        """
        Rollback to a previous configuration version.
        
        Args:
            version_id: ID of version to rollback to
            rolled_back_by: User performing rollback
            reason: Reason for rollback
        
        Returns:
            Tuple of (success, message)
        """
        with self._lock:
            target_version = self.get_version(version_id)
            if not target_version:
                return False, f"Version not found: {version_id}"
            
            # Verify integrity
            if not target_version.verify_integrity():
                return False, "Version integrity check failed"
            
            # Deactivate current version
            current_version = self.get_active_version()
            current_version.is_active = False
            
            # Create rollback version (copy of target)
            rollback_version = ConfigVersion(
                version_id=str(uuid.uuid4()),
                version_number=self._increment_version(current_version.version_number),
                config_data=copy.deepcopy(target_version.config_data),
                created_at=datetime.now(),
                created_by=rolled_back_by,
                description=f"Rollback to {target_version.version_number}: {reason}",
                is_active=True,
            )
            
            self._versions.append(rollback_version)
            
            # Save to file and history
            self._save_config_file(rollback_version.config_data)
            self._save_history()
            
            logger.info(
                f"Rolled back to version {target_version.version_number} "
                f"by {rolled_back_by}: {reason}"
            )
            
            return True, f"Rolled back to version {target_version.version_number}"
    
    # ========================================
    # CALLBACKS
    # ========================================
    
    def register_change_callback(
        self,
        callback: Callable[[ConfigChangeRequest], None],
    ) -> None:
        """Register callback for new change requests"""
        self._callbacks.append(callback)
    
    def unregister_change_callback(
        self,
        callback: Callable[[ConfigChangeRequest], None],
    ) -> None:
        """Unregister callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# Global versioned config manager instance
versioned_config_manager = VersionedConfigManager()


__all__ = [
    "VersionedConfigManager",
    "ConfigVersion",
    "ConfigChangeRequest",
    "ConfigChangeStatus",
    "ConfigChangeType",
    "versioned_config_manager",
]
