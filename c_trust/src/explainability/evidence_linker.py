"""
C-TRUST Evidence Linker
=======================
Links explanations to underlying data sources for traceability.

Key Features:
- Evidence extraction from data sources
- Evidence relevance scoring
- Traceability chain creation
- Evidence aggregation

**Validates: Requirements 7.1, 7.4**
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import hashlib

from src.core import get_logger
from .explanation_engine import EvidenceItem

logger = get_logger(__name__)


@dataclass
class DataSource:
    """Represents a data source for evidence extraction"""
    source_id: str
    source_type: str  # EDC_Metrics, SAE_Dashboard, etc.
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceChain:
    """
    Chain of evidence linking explanation to data.
    
    Provides full traceability from explanation to raw data.
    """
    chain_id: str
    explanation_id: str
    entity_id: str
    evidence_items: List[EvidenceItem]
    source_summary: Dict[str, int]  # source_type -> count
    total_relevance: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chain_id": self.chain_id,
            "explanation_id": self.explanation_id,
            "entity_id": self.entity_id,
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "source_summary": self.source_summary,
            "total_relevance": self.total_relevance,
            "timestamp": self.timestamp.isoformat(),
        }


class EvidenceLinker:
    """
    Links explanations to underlying data sources.
    
    Extracts relevant evidence from data sources and creates
    traceable links between explanations and raw data.
    
    **Validates: Requirements 7.1, 7.4**
    """
    
    # Field mappings for evidence extraction
    FIELD_MAPPINGS = {
        "EDC_Metrics": {
            "missing_pages_pct": ("Missing Pages %", "completeness"),
            "visit_completion_rate": ("Visit Completion Rate", "completeness"),
            "form_completion_rate": ("Form Completion Rate", "completeness"),
            "data_entry_lag_days": ("Data Entry Lag (days)", "operations"),
        },
        "SAE_Dashboard": {
            "sae_backlog_days": ("SAE Backlog (days)", "safety"),
            "sae_overdue_count": ("Overdue SAE Count", "safety"),
            "fatal_sae_count": ("Fatal SAE Count", "safety"),
            "open_sae_count": ("Open SAE Count", "safety"),
        },
        "Query_Metrics": {
            "open_query_count": ("Open Query Count", "operations"),
            "query_aging_days": ("Query Aging (days)", "operations"),
            "query_resolution_rate": ("Query Resolution Rate", "operations"),
        },
        "Compliance_Data": {
            "protocol_deviation_count": ("Protocol Deviations", "compliance"),
            "missing_lab_ranges_pct": ("Missing Lab Ranges %", "compliance"),
            "regulatory_compliance_rate": ("Regulatory Compliance Rate", "compliance"),
        },
    }
    
    # Relevance thresholds
    HIGH_RELEVANCE_THRESHOLD = 0.8
    MEDIUM_RELEVANCE_THRESHOLD = 0.5
    
    def __init__(self):
        """Initialize evidence linker"""
        self._evidence_cache: Dict[str, List[EvidenceItem]] = {}
        logger.info("EvidenceLinker initialized")
    
    def extract_evidence(
        self,
        data_sources: List[DataSource],
        entity_id: str,
        focus_dimensions: Optional[List[str]] = None,
    ) -> List[EvidenceItem]:
        """
        Extract evidence items from data sources.
        
        Args:
            data_sources: List of data sources to extract from
            entity_id: Entity to extract evidence for
            focus_dimensions: Optional list of dimensions to focus on
                            (safety, compliance, completeness, operations)
        
        Returns:
            List of evidence items
        """
        evidence_items = []
        
        for source in data_sources:
            items = self._extract_from_source(source, entity_id, focus_dimensions)
            evidence_items.extend(items)
        
        # Sort by relevance
        evidence_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.debug(f"Extracted {len(evidence_items)} evidence items for {entity_id}")
        return evidence_items
    
    def _extract_from_source(
        self,
        source: DataSource,
        entity_id: str,
        focus_dimensions: Optional[List[str]] = None,
    ) -> List[EvidenceItem]:
        """Extract evidence from a single data source"""
        items = []
        
        field_mapping = self.FIELD_MAPPINGS.get(source.source_type, {})
        
        for field_name, (display_name, dimension) in field_mapping.items():
            # Skip if not in focus dimensions
            if focus_dimensions and dimension not in focus_dimensions:
                continue
            
            # Get value from source data
            value = source.data.get(field_name)
            if value is None:
                continue
            
            # Calculate relevance based on value significance
            relevance = self._calculate_relevance(field_name, value, dimension)
            
            # Generate evidence ID
            evidence_id = self._generate_evidence_id(
                source.source_id, field_name, entity_id
            )
            
            # Create description
            description = self._generate_description(display_name, value, dimension)
            
            items.append(EvidenceItem(
                evidence_id=evidence_id,
                source_type=source.source_type,
                source_field=field_name,
                value=value,
                description=description,
                timestamp=source.timestamp,
                relevance_score=relevance,
            ))
        
        return items
    
    def _calculate_relevance(
        self,
        field_name: str,
        value: Any,
        dimension: str,
    ) -> float:
        """
        Calculate relevance score for evidence item.
        
        Higher relevance for more significant values.
        """
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return 0.5  # Default relevance for non-numeric
        
        # Dimension-specific relevance calculation
        if dimension == "safety":
            # Higher values = more relevant for safety issues
            if "count" in field_name:
                return min(1.0, 0.3 + (numeric_value / 10) * 0.7)
            elif "days" in field_name:
                return min(1.0, 0.3 + (numeric_value / 30) * 0.7)
            return 0.5
        
        elif dimension == "completeness":
            # Lower completion rates = more relevant
            if "rate" in field_name or "completion" in field_name:
                return max(0.1, 1.0 - (numeric_value / 100))
            elif "missing" in field_name or "pct" in field_name:
                return min(1.0, numeric_value / 100)
            return 0.5
        
        elif dimension == "operations":
            # Higher backlogs/aging = more relevant
            if "count" in field_name:
                return min(1.0, 0.3 + (numeric_value / 100) * 0.7)
            elif "days" in field_name or "aging" in field_name:
                return min(1.0, 0.3 + (numeric_value / 30) * 0.7)
            return 0.5
        
        elif dimension == "compliance":
            # Lower compliance = more relevant
            if "rate" in field_name:
                return max(0.1, 1.0 - (numeric_value / 100))
            elif "count" in field_name or "deviation" in field_name:
                return min(1.0, 0.3 + (numeric_value / 20) * 0.7)
            return 0.5
        
        return 0.5
    
    def _generate_evidence_id(
        self,
        source_id: str,
        field_name: str,
        entity_id: str,
    ) -> str:
        """Generate unique evidence ID"""
        content = f"{source_id}:{field_name}:{entity_id}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"EVD_{hash_val}"
    
    def _generate_description(
        self,
        display_name: str,
        value: Any,
        dimension: str,
    ) -> str:
        """Generate human-readable description for evidence"""
        try:
            numeric_value = float(value)
            if "%" in display_name or "rate" in display_name.lower():
                return f"{display_name}: {numeric_value:.1f}%"
            elif "count" in display_name.lower():
                return f"{display_name}: {int(numeric_value)}"
            elif "days" in display_name.lower():
                return f"{display_name}: {numeric_value:.1f} days"
            else:
                return f"{display_name}: {numeric_value:.2f}"
        except (TypeError, ValueError):
            return f"{display_name}: {value}"
    
    def create_evidence_chain(
        self,
        explanation_id: str,
        entity_id: str,
        evidence_items: List[EvidenceItem],
    ) -> EvidenceChain:
        """
        Create evidence chain linking explanation to data.
        
        Args:
            explanation_id: ID of the explanation
            entity_id: Entity being explained
            evidence_items: List of evidence items
        
        Returns:
            EvidenceChain with full traceability
        """
        # Generate chain ID
        chain_id = f"CHAIN_{explanation_id}"
        
        # Calculate source summary
        source_summary: Dict[str, int] = {}
        for item in evidence_items:
            source_summary[item.source_type] = source_summary.get(item.source_type, 0) + 1
        
        # Calculate total relevance
        total_relevance = sum(item.relevance_score for item in evidence_items)
        if evidence_items:
            total_relevance /= len(evidence_items)
        
        chain = EvidenceChain(
            chain_id=chain_id,
            explanation_id=explanation_id,
            entity_id=entity_id,
            evidence_items=evidence_items,
            source_summary=source_summary,
            total_relevance=total_relevance,
        )
        
        logger.debug(f"Created evidence chain {chain_id} with {len(evidence_items)} items")
        return chain
    
    def filter_by_relevance(
        self,
        evidence_items: List[EvidenceItem],
        min_relevance: float = 0.3,
        max_items: int = 10,
    ) -> List[EvidenceItem]:
        """
        Filter evidence items by relevance.
        
        Args:
            evidence_items: List of evidence items
            min_relevance: Minimum relevance score
            max_items: Maximum number of items to return
        
        Returns:
            Filtered list of evidence items
        """
        filtered = [e for e in evidence_items if e.relevance_score >= min_relevance]
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        return filtered[:max_items]
    
    def aggregate_evidence(
        self,
        evidence_items: List[EvidenceItem],
    ) -> Dict[str, Any]:
        """
        Aggregate evidence items into summary statistics.
        
        Args:
            evidence_items: List of evidence items
        
        Returns:
            Dictionary with aggregated statistics
        """
        if not evidence_items:
            return {
                "total_items": 0,
                "avg_relevance": 0.0,
                "sources": [],
                "high_relevance_count": 0,
            }
        
        sources = list(set(e.source_type for e in evidence_items))
        avg_relevance = sum(e.relevance_score for e in evidence_items) / len(evidence_items)
        high_relevance = sum(1 for e in evidence_items 
                           if e.relevance_score >= self.HIGH_RELEVANCE_THRESHOLD)
        
        return {
            "total_items": len(evidence_items),
            "avg_relevance": avg_relevance,
            "sources": sources,
            "high_relevance_count": high_relevance,
            "source_breakdown": {
                src: sum(1 for e in evidence_items if e.source_type == src)
                for src in sources
            },
        }


__all__ = ["EvidenceLinker", "DataSource", "EvidenceChain"]
