"""
Property-Based Tests for Dashboard Navigation Context Preservation
===================================================================
Tests Property: Dashboard Navigation Context Preservation

**Property: Dashboard Navigation Context Preservation**
*For any* navigation path through the dashboard (Portfolio → Study → Site → Subject),
the system should preserve user context including filters, sort orders, and 
selected tabs, allowing users to return to their previous state.

**Validates: Requirements 6.3**

This test uses Hypothesis to generate various navigation scenarios and
verify that context is properly preserved during drill-down navigation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode, parse_qs

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume


# ========================================
# DOMAIN MODELS
# ========================================

class NavigationLevel(Enum):
    """Dashboard navigation hierarchy levels"""
    PORTFOLIO = "portfolio"
    STUDY = "study"
    SITE = "site"
    SUBJECT = "subject"


class SortOrder(Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class RiskFilter(Enum):
    """Risk level filter options"""
    ALL = "all"
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TabType(Enum):
    """Available tabs in study dashboard"""
    OVERVIEW = "overview"
    SITES = "sites"
    DQI = "dqi"
    AGENTS = "agents"


@dataclass
class NavigationContext:
    """Represents the current navigation context state"""
    level: NavigationLevel
    entity_id: Optional[str] = None
    parent_id: Optional[str] = None
    active_tab: TabType = TabType.OVERVIEW
    risk_filter: RiskFilter = RiskFilter.ALL
    sort_column: str = "risk_level"
    sort_order: SortOrder = SortOrder.DESC
    search_query: str = ""
    page: int = 1
    page_size: int = 20
    
    def to_url_params(self) -> Dict[str, str]:
        """Convert context to URL query parameters"""
        params = {}
        if self.active_tab != TabType.OVERVIEW:
            params["tab"] = self.active_tab.value
        if self.risk_filter != RiskFilter.ALL:
            params["risk"] = self.risk_filter.value
        if self.sort_column != "risk_level":
            params["sort"] = self.sort_column
        if self.sort_order != SortOrder.DESC:
            params["order"] = self.sort_order.value
        if self.search_query:
            params["q"] = self.search_query
        if self.page > 1:
            params["page"] = str(self.page)
        if self.parent_id:
            params["from"] = self.parent_id
        return params
    
    @classmethod
    def from_url_params(cls, level: NavigationLevel, entity_id: Optional[str], 
                        params: Dict[str, str]) -> "NavigationContext":
        """Create context from URL query parameters"""
        return cls(
            level=level,
            entity_id=entity_id,
            parent_id=params.get("from"),
            active_tab=TabType(params.get("tab", "overview")),
            risk_filter=RiskFilter(params.get("risk", "all")),
            sort_column=params.get("sort", "risk_level"),
            sort_order=SortOrder(params.get("order", "desc")),
            search_query=params.get("q", ""),
            page=int(params.get("page", "1")),
        )


@dataclass
class NavigationHistoryEntry:
    """Single entry in navigation history"""
    context: NavigationContext
    timestamp: datetime = field(default_factory=datetime.now)


class NavigationContextManager:
    """
    Manages navigation context preservation during dashboard drill-down.
    
    This class implements the context preservation logic that ensures
    users can navigate through Portfolio → Study → Site → Subject
    while maintaining their filters, sort orders, and selected tabs.
    """
    
    def __init__(self):
        self.history: List[NavigationHistoryEntry] = []
        self.current_context: Optional[NavigationContext] = None
        self.max_history_size: int = 50
    
    def navigate_to(self, new_context: NavigationContext) -> NavigationContext:
        """
        Navigate to a new context, preserving history.
        
        Returns the context with any inherited settings from parent.
        """
        # Store current context in history before navigating
        if self.current_context:
            self.history.append(NavigationHistoryEntry(context=self.current_context))
            
            # Trim history if too large
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]
        
        # Set parent reference for drill-down navigation
        if self.current_context and self._is_drill_down(self.current_context.level, new_context.level):
            new_context.parent_id = self.current_context.entity_id
        
        self.current_context = new_context
        return new_context
    
    def navigate_back(self) -> Optional[NavigationContext]:
        """
        Navigate back to previous context.
        
        Returns the previous context or None if at root.
        """
        if not self.history:
            return None
        
        previous_entry = self.history.pop()
        self.current_context = previous_entry.context
        return self.current_context
    
    def get_breadcrumb_path(self) -> List[NavigationContext]:
        """
        Get the breadcrumb navigation path from root to current.
        
        Returns list of contexts representing the navigation path.
        """
        path = []
        
        # Build path from history entries that form a drill-down chain
        for entry in self.history:
            if not path or self._is_drill_down(path[-1].level, entry.context.level):
                path.append(entry.context)
        
        if self.current_context:
            path.append(self.current_context)
        
        return path
    
    def preserve_context_on_return(self, target_level: NavigationLevel) -> Optional[NavigationContext]:
        """
        Find and return to a previous context at the specified level.
        
        This preserves the user's filters and settings when returning
        to a parent level in the hierarchy.
        """
        # Search history for matching level
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].context.level == target_level:
                # Found matching level - restore that context
                restored_context = self.history[i].context
                # Remove entries after this point
                self.history = self.history[:i]
                self.current_context = restored_context
                return restored_context
        
        return None
    
    def generate_return_url(self, context: NavigationContext) -> str:
        """
        Generate a URL that preserves context for navigation.
        
        Returns URL path with query parameters encoding the context.
        """
        base_paths = {
            NavigationLevel.PORTFOLIO: "/portfolio",
            NavigationLevel.STUDY: f"/studies/{context.entity_id}",
            NavigationLevel.SITE: f"/studies/{context.parent_id}/sites/{context.entity_id}",
            NavigationLevel.SUBJECT: f"/studies/{context.parent_id}/sites/{context.entity_id}/subjects",
        }
        
        base_path = base_paths.get(context.level, "/portfolio")
        params = context.to_url_params()
        
        if params:
            return f"{base_path}?{urlencode(params)}"
        return base_path
    
    def _is_drill_down(self, from_level: NavigationLevel, to_level: NavigationLevel) -> bool:
        """Check if navigation is a drill-down (going deeper in hierarchy)"""
        hierarchy = [
            NavigationLevel.PORTFOLIO,
            NavigationLevel.STUDY,
            NavigationLevel.SITE,
            NavigationLevel.SUBJECT,
        ]
        
        try:
            from_idx = hierarchy.index(from_level)
            to_idx = hierarchy.index(to_level)
            return to_idx > from_idx
        except ValueError:
            return False
    
    def _is_drill_up(self, from_level: NavigationLevel, to_level: NavigationLevel) -> bool:
        """Check if navigation is a drill-up (going up in hierarchy)"""
        return self._is_drill_down(to_level, from_level)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def navigation_level_strategy(draw):
    """Generate a valid NavigationLevel"""
    return draw(st.sampled_from(list(NavigationLevel)))


@st.composite
def tab_type_strategy(draw):
    """Generate a valid TabType"""
    return draw(st.sampled_from(list(TabType)))


@st.composite
def risk_filter_strategy(draw):
    """Generate a valid RiskFilter"""
    return draw(st.sampled_from(list(RiskFilter)))


@st.composite
def sort_order_strategy(draw):
    """Generate a valid SortOrder"""
    return draw(st.sampled_from(list(SortOrder)))


@st.composite
def entity_id_strategy(draw):
    """Generate a valid entity ID"""
    prefix = draw(st.sampled_from(["STUDY", "SITE", "SUBJ"]))
    number = draw(st.integers(min_value=1, max_value=99))
    return f"{prefix}_{number:02d}"


@st.composite
def search_query_strategy(draw):
    """Generate a valid search query"""
    return draw(st.text(
        min_size=0, 
        max_size=50, 
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Z'))
    ))


@st.composite
def sort_column_strategy(draw):
    """Generate a valid sort column name"""
    return draw(st.sampled_from([
        "risk_level", "dqi_score", "enrollment", "site_id", 
        "study_id", "queries", "saes", "last_updated"
    ]))


@st.composite
def navigation_context_strategy(draw):
    """Generate a complete navigation context"""
    level = draw(navigation_level_strategy())
    
    # Generate appropriate entity_id based on level
    entity_id = None
    parent_id = None
    
    if level != NavigationLevel.PORTFOLIO:
        entity_id = draw(entity_id_strategy())
    
    if level in [NavigationLevel.SITE, NavigationLevel.SUBJECT]:
        parent_id = draw(entity_id_strategy())
    
    return NavigationContext(
        level=level,
        entity_id=entity_id,
        parent_id=parent_id,
        active_tab=draw(tab_type_strategy()),
        risk_filter=draw(risk_filter_strategy()),
        sort_column=draw(sort_column_strategy()),
        sort_order=draw(sort_order_strategy()),
        search_query=draw(search_query_strategy()),
        page=draw(st.integers(min_value=1, max_value=100)),
    )


@st.composite
def drill_down_path_strategy(draw, min_depth: int = 2, max_depth: int = 4):
    """Generate a valid drill-down navigation path"""
    hierarchy = [
        NavigationLevel.PORTFOLIO,
        NavigationLevel.STUDY,
        NavigationLevel.SITE,
        NavigationLevel.SUBJECT,
    ]
    
    depth = draw(st.integers(min_value=min_depth, max_value=min(max_depth, len(hierarchy))))
    path = []
    
    parent_id = None
    for i in range(depth):
        level = hierarchy[i]
        entity_id = draw(entity_id_strategy()) if level != NavigationLevel.PORTFOLIO else None
        
        context = NavigationContext(
            level=level,
            entity_id=entity_id,
            parent_id=parent_id,
            active_tab=draw(tab_type_strategy()),
            risk_filter=draw(risk_filter_strategy()),
            sort_column=draw(sort_column_strategy()),
            sort_order=draw(sort_order_strategy()),
            search_query=draw(search_query_strategy()),
            page=draw(st.integers(min_value=1, max_value=10)),
        )
        path.append(context)
        parent_id = entity_id
    
    return path


# ========================================
# PROPERTY TESTS
# ========================================

class TestDashboardContextPreservationProperty:
    """
    Property-based tests for dashboard navigation context preservation.
    
    Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
    """
    
    @given(context=navigation_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_context_roundtrip_through_url(self, context: NavigationContext):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Context should survive roundtrip through URL parameters.
        Converting to URL params and back should preserve all settings.
        """
        # Convert to URL params
        params = context.to_url_params()
        
        # Convert back from URL params
        restored = NavigationContext.from_url_params(
            level=context.level,
            entity_id=context.entity_id,
            params=params
        )
        
        # Verify key context is preserved
        assert restored.active_tab == context.active_tab, \
            f"Tab should be preserved: expected {context.active_tab}, got {restored.active_tab}"
        assert restored.risk_filter == context.risk_filter, \
            f"Risk filter should be preserved: expected {context.risk_filter}, got {restored.risk_filter}"
        assert restored.sort_order == context.sort_order, \
            f"Sort order should be preserved: expected {context.sort_order}, got {restored.sort_order}"
        assert restored.search_query == context.search_query, \
            f"Search query should be preserved: expected '{context.search_query}', got '{restored.search_query}'"
    
    @given(path=drill_down_path_strategy())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_drill_down_preserves_parent_reference(self, path: List[NavigationContext]):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: During drill-down navigation, parent references should be
        maintained to enable proper breadcrumb navigation.
        """
        manager = NavigationContextManager()
        
        for context in path:
            result = manager.navigate_to(context)
            
            # After first navigation, parent should be set for drill-downs
            if len(manager.history) > 0:
                prev_context = manager.history[-1].context
                if manager._is_drill_down(prev_context.level, context.level):
                    assert result.parent_id == prev_context.entity_id, \
                        f"Parent ID should be set to previous entity: expected {prev_context.entity_id}"
    
    @given(path=drill_down_path_strategy(min_depth=3))
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_navigate_back_restores_previous_context(self, path: List[NavigationContext]):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Navigating back should restore the exact previous context
        including all filters, sort orders, and tab selections.
        """
        manager = NavigationContextManager()
        
        # Navigate through the path
        for context in path:
            manager.navigate_to(context)
        
        # Navigate back and verify each step
        for i in range(len(path) - 1, 0, -1):
            expected = path[i - 1]
            restored = manager.navigate_back()
            
            assert restored is not None, "Should be able to navigate back"
            assert restored.level == expected.level, \
                f"Level should match: expected {expected.level}, got {restored.level}"
            assert restored.active_tab == expected.active_tab, \
                f"Tab should be preserved on back navigation"
            assert restored.risk_filter == expected.risk_filter, \
                f"Risk filter should be preserved on back navigation"
    
    @given(path=drill_down_path_strategy())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_breadcrumb_path_is_valid_hierarchy(self, path: List[NavigationContext]):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Breadcrumb path should always represent a valid
        hierarchical drill-down from Portfolio to current level.
        """
        manager = NavigationContextManager()
        
        for context in path:
            manager.navigate_to(context)
        
        breadcrumbs = manager.get_breadcrumb_path()
        
        # Verify breadcrumbs form valid hierarchy
        hierarchy_order = [
            NavigationLevel.PORTFOLIO,
            NavigationLevel.STUDY,
            NavigationLevel.SITE,
            NavigationLevel.SUBJECT,
        ]
        
        for i in range(len(breadcrumbs) - 1):
            current_idx = hierarchy_order.index(breadcrumbs[i].level)
            next_idx = hierarchy_order.index(breadcrumbs[i + 1].level)
            assert next_idx > current_idx, \
                f"Breadcrumb path should be strictly increasing in hierarchy"
    
    @given(context=navigation_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_url_generation_includes_context(self, context: NavigationContext):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Generated URLs should include all non-default context
        parameters to enable bookmarking and sharing.
        """
        manager = NavigationContextManager()
        url = manager.generate_return_url(context)
        
        # URL should contain base path
        assert url.startswith("/"), "URL should start with /"
        
        # Non-default values should appear in URL
        if context.active_tab != TabType.OVERVIEW:
            assert f"tab={context.active_tab.value}" in url, \
                "Non-default tab should be in URL"
        
        if context.risk_filter != RiskFilter.ALL:
            assert f"risk={context.risk_filter.value}" in url, \
                "Non-default risk filter should be in URL"
        
        if context.page > 1:
            assert f"page={context.page}" in url, \
                "Non-default page should be in URL"
    
    @given(path=drill_down_path_strategy(min_depth=3))
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_preserve_context_on_return_to_level(self, path: List[NavigationContext]):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: When returning to a previous level (e.g., from Site back to Study),
        the original context at that level should be restored.
        """
        manager = NavigationContextManager()
        
        # Navigate through path
        for context in path:
            manager.navigate_to(context)
        
        # Return to first level (Portfolio)
        target_level = path[0].level
        restored = manager.preserve_context_on_return(target_level)
        
        if restored:
            assert restored.level == target_level, \
                f"Should return to {target_level}"
            assert restored.active_tab == path[0].active_tab, \
                "Original tab selection should be preserved"
            assert restored.risk_filter == path[0].risk_filter, \
                "Original risk filter should be preserved"
    
    @given(contexts=st.lists(navigation_context_strategy(), min_size=1, max_size=60))
    @settings(max_examples=30, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_history_size_is_bounded(self, contexts: List[NavigationContext]):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Navigation history should be bounded to prevent
        memory issues while still preserving recent context.
        """
        manager = NavigationContextManager()
        
        for context in contexts:
            manager.navigate_to(context)
        
        # History should never exceed max size
        assert len(manager.history) <= manager.max_history_size, \
            f"History size {len(manager.history)} exceeds max {manager.max_history_size}"
    
    @given(context=navigation_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_context_has_valid_defaults(self, context: NavigationContext):
        """
        Feature: clinical-ai-system, Property: Dashboard Navigation Context Preservation
        Validates: Requirements 6.3
        
        Property: Navigation context should always have valid default values
        for optional fields.
        """
        # Verify defaults are valid
        assert context.page >= 1, "Page should be at least 1"
        assert context.page_size > 0, "Page size should be positive"
        assert context.active_tab in TabType, "Tab should be valid"
        assert context.risk_filter in RiskFilter, "Risk filter should be valid"
        assert context.sort_order in SortOrder, "Sort order should be valid"


# ========================================
# UNIT TESTS
# ========================================

class TestNavigationContextUnit:
    """Unit tests for navigation context"""
    
    def test_default_context_values(self):
        """Test that default context has expected values"""
        context = NavigationContext(level=NavigationLevel.PORTFOLIO)
        
        assert context.active_tab == TabType.OVERVIEW
        assert context.risk_filter == RiskFilter.ALL
        assert context.sort_order == SortOrder.DESC
        assert context.page == 1
    
    def test_url_params_empty_for_defaults(self):
        """Test that default values don't appear in URL params"""
        context = NavigationContext(level=NavigationLevel.PORTFOLIO)
        params = context.to_url_params()
        
        assert len(params) == 0, "Default context should have no URL params"
    
    def test_url_params_include_non_defaults(self):
        """Test that non-default values appear in URL params"""
        context = NavigationContext(
            level=NavigationLevel.STUDY,
            entity_id="STUDY_01",
            active_tab=TabType.SITES,
            risk_filter=RiskFilter.HIGH,
            page=3,
        )
        params = context.to_url_params()
        
        assert params["tab"] == "sites"
        assert params["risk"] == "high"
        assert params["page"] == "3"


class TestNavigationContextManagerUnit:
    """Unit tests for navigation context manager"""
    
    def test_initial_state(self):
        """Test manager starts with no history"""
        manager = NavigationContextManager()
        
        assert manager.current_context is None
        assert len(manager.history) == 0
    
    def test_navigate_to_sets_current(self):
        """Test that navigate_to sets current context"""
        manager = NavigationContextManager()
        context = NavigationContext(level=NavigationLevel.PORTFOLIO)
        
        manager.navigate_to(context)
        
        assert manager.current_context == context
    
    def test_navigate_back_from_empty_returns_none(self):
        """Test that navigate_back returns None when no history"""
        manager = NavigationContextManager()
        
        result = manager.navigate_back()
        
        assert result is None
    
    def test_drill_down_detection(self):
        """Test drill-down detection logic"""
        manager = NavigationContextManager()
        
        assert manager._is_drill_down(NavigationLevel.PORTFOLIO, NavigationLevel.STUDY)
        assert manager._is_drill_down(NavigationLevel.STUDY, NavigationLevel.SITE)
        assert not manager._is_drill_down(NavigationLevel.SITE, NavigationLevel.STUDY)
        assert not manager._is_drill_down(NavigationLevel.STUDY, NavigationLevel.STUDY)
