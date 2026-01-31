"""
C-TRUST Background Scheduler
=============================
Scheduled refresh and file change detection for automatic updates.

Features:
1. 30-minute scheduled refresh cycle
2. File watcher for dataset changes
3. Hash-based change detection
4. Background async processing
5. Cache invalidation triggers

Architecture:
    Scheduler (30 min) → Check Dataset → Changed? → Run Pipeline
    File Watcher       → File Changed → Invalidate Cache → Run Pipeline

Usage:
    scheduler = RefreshScheduler()
    scheduler.start()  # Start background jobs
    # ... application runs ...
    scheduler.stop()   # Clean shutdown
"""

import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
from typing import Any, Callable, Dict, List, Optional, Set
import json

from src.core import get_logger
from src.core.config import settings

logger = get_logger(__name__)


# ========================================
# FILE WATCHER
# ========================================

class FileWatcher:
    """
    Watches directories for file changes.
    
    Uses hash-based detection to identify actual content changes.
    """
    
    WATCH_EXTENSIONS = {'.xlsx', '.xls', '.csv'}
    
    def __init__(
        self,
        watch_paths: List[str],
        check_interval: int = 60,  # seconds
    ):
        """
        Initialize file watcher.
        
        Args:
            watch_paths: List of directories to watch
            check_interval: Seconds between checks
        """
        self.watch_paths = [Path(p) for p in watch_paths]
        self.check_interval = check_interval
        
        # File state tracking
        self._file_hashes: Dict[str, str] = {}
        self._file_mtimes: Dict[str, float] = {}
        
        # Threading
        self._stop_event = Event()
        self._watch_thread: Optional[Thread] = None
        
        # Callbacks
        self._on_change_callbacks: List[Callable[[List[str]], None]] = []
        
        # Initialize baseline
        self._scan_all_files()
        
        logger.info(f"FileWatcher initialized: watching {len(self.watch_paths)} paths")
    
    def add_change_callback(self, callback: Callable[[List[str]], None]) -> None:
        """Add callback to be called when files change."""
        self._on_change_callbacks.append(callback)
    
    def start(self) -> None:
        """Start watching in background thread."""
        if self._watch_thread is not None:
            return
        
        self._stop_event.clear()
        self._watch_thread = Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
        logger.info("FileWatcher started")
    
    def stop(self) -> None:
        """Stop watching."""
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
            self._watch_thread = None
        logger.info("FileWatcher stopped")
    
    def check_now(self) -> List[str]:
        """Check for changes immediately."""
        return self._check_for_changes()
    
    def _watch_loop(self) -> None:
        """Main watch loop."""
        while not self._stop_event.is_set():
            try:
                changed = self._check_for_changes()
                
                if changed:
                    logger.info(f"Detected {len(changed)} file changes")
                    for callback in self._on_change_callbacks:
                        try:
                            callback(changed)
                        except Exception as e:
                            logger.error(f"Change callback error: {e}")
                
            except Exception as e:
                logger.error(f"FileWatcher error: {e}")
            
            # Wait for interval or stop signal
            self._stop_event.wait(self.check_interval)
    
    def _check_for_changes(self) -> List[str]:
        """Check all watched paths for changes."""
        changed_files = []
        
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
            
            for file_path in watch_path.rglob("*"):
                if file_path.suffix.lower() not in self.WATCH_EXTENSIONS:
                    continue
                
                if not file_path.is_file():
                    continue
                
                file_key = str(file_path)
                
                try:
                    # Quick check - modification time
                    mtime = file_path.stat().st_mtime
                    old_mtime = self._file_mtimes.get(file_key)
                    
                    if old_mtime is None:
                        # New file
                        self._file_mtimes[file_key] = mtime
                        self._file_hashes[file_key] = self._hash_file(file_path)
                        changed_files.append(file_key)
                        
                    elif mtime != old_mtime:
                        # Mtime changed - verify with hash
                        new_hash = self._hash_file(file_path)
                        old_hash = self._file_hashes.get(file_key)
                        
                        if new_hash != old_hash:
                            changed_files.append(file_key)
                            self._file_hashes[file_key] = new_hash
                        
                        self._file_mtimes[file_key] = mtime
                        
                except Exception as e:
                    logger.warning(f"Error checking {file_path}: {e}")
        
        return changed_files
    
    def _scan_all_files(self) -> None:
        """Scan all files and store baseline hashes."""
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
            
            for file_path in watch_path.rglob("*"):
                if file_path.suffix.lower() not in self.WATCH_EXTENSIONS:
                    continue
                
                if not file_path.is_file():
                    continue
                
                try:
                    file_key = str(file_path)
                    self._file_mtimes[file_key] = file_path.stat().st_mtime
                    self._file_hashes[file_key] = self._hash_file(file_path)
                except Exception as e:
                    logger.warning(f"Error scanning {file_path}: {e}")
        
        logger.info(f"Baseline: {len(self._file_hashes)} files indexed")
    
    def _hash_file(self, file_path: Path) -> str:
        """Compute hash of file contents."""
        hasher = hashlib.md5()
        
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            # Fallback to mtime-based hash
            return str(file_path.stat().st_mtime)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get watcher statistics."""
        return {
            "watching_paths": [str(p) for p in self.watch_paths],
            "files_tracked": len(self._file_hashes),
            "check_interval": self.check_interval,
            "is_running": self._watch_thread is not None and self._watch_thread.is_alive(),
        }


# ========================================
# REFRESH SCHEDULER
# ========================================

class RefreshScheduler:
    """
    Background scheduler for periodic data refresh.
    
    Runs every 30 minutes to:
    1. Check if dataset has changed
    2. If changed, run full pipeline
    3. Update cache with new results
    """
    
    DEFAULT_INTERVAL = 1800  # 30 minutes in seconds
    
    def __init__(
        self,
        data_path: Optional[str] = None,
        refresh_interval: int = DEFAULT_INTERVAL,
        enable_file_watcher: bool = True,
    ):
        """
        Initialize scheduler.
        
        Args:
            data_path: Path to dataset directory
            refresh_interval: Seconds between scheduled refreshes
            enable_file_watcher: Enable file change detection
        """
        self.refresh_interval = refresh_interval
        self.enable_file_watcher = enable_file_watcher
        
        # Data path
        if data_path:
            self.data_path = Path(data_path)
        else:
            # Default from settings
            self.data_path = Path(settings.data_root) if hasattr(settings, 'data_root') else None
        
        # Threading
        self._stop_event = Event()
        self._scheduler_thread: Optional[Thread] = None
        
        # File watcher
        self._file_watcher: Optional[FileWatcher] = None
        if enable_file_watcher and self.data_path:
            self._file_watcher = FileWatcher(
                watch_paths=[str(self.data_path)],
                check_interval=60,
            )
            self._file_watcher.add_change_callback(self._on_file_change)
        
        # Refresh callback
        self._refresh_callback: Optional[Callable[[], None]] = None
        
        # State tracking
        self._last_refresh: Optional[datetime] = None
        self._refresh_count = 0
        self._pending_refresh = False
        
        logger.info(f"RefreshScheduler initialized: {refresh_interval}s interval")
    
    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Set callback to run on refresh."""
        self._refresh_callback = callback
    
    def start(self) -> None:
        """Start scheduler and file watcher."""
        if self._scheduler_thread is not None:
            return
        
        # Start file watcher
        if self._file_watcher:
            self._file_watcher.start()
        
        # Start scheduler
        self._stop_event.clear()
        self._scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("RefreshScheduler started")
    
    def stop(self) -> None:
        """Stop scheduler and file watcher."""
        self._stop_event.set()
        
        if self._file_watcher:
            self._file_watcher.stop()
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None
        
        logger.info("RefreshScheduler stopped")
    
    def trigger_refresh(self) -> None:
        """Manually trigger a refresh."""
        self._pending_refresh = True
        logger.info("Manual refresh triggered")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                # Check if refresh needed
                if self._should_refresh():
                    self._do_refresh()
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Wait for interval or stop signal
            self._stop_event.wait(min(60, self.refresh_interval))
    
    def _should_refresh(self) -> bool:
        """Check if refresh is needed."""
        # Pending from file change
        if self._pending_refresh:
            return True
        
        # Scheduled interval
        if self._last_refresh is None:
            return True
        
        elapsed = (datetime.now() - self._last_refresh).total_seconds()
        return elapsed >= self.refresh_interval
    
    def _do_refresh(self) -> None:
        """Execute refresh."""
        logger.info("Starting scheduled refresh...")
        self._pending_refresh = False
        
        try:
            if self._refresh_callback:
                self._refresh_callback()
            
            self._last_refresh = datetime.now()
            self._refresh_count += 1
            
            logger.info(f"Refresh complete (#{self._refresh_count})")
            
        except Exception as e:
            logger.error(f"Refresh failed: {e}")
    
    def _on_file_change(self, changed_files: List[str]) -> None:
        """Handle file change from watcher."""
        logger.info(f"File change detected: {len(changed_files)} files")
        self.trigger_refresh()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "is_running": self._scheduler_thread is not None and self._scheduler_thread.is_alive(),
            "refresh_interval": self.refresh_interval,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "refresh_count": self._refresh_count,
            "pending_refresh": self._pending_refresh,
            "file_watcher": self._file_watcher.get_stats() if self._file_watcher else None,
        }


# ========================================
# INTEGRATED ANALYSIS SCHEDULER
# ========================================

class AnalysisScheduler:
    """
    High-level scheduler that integrates all components.
    
    Coordinates:
    - Cache manager
    - Agent pipeline
    - File watcher
    - Scheduled refresh
    """
    
    def __init__(self):
        """Initialize integrated scheduler."""
        from src.core.cache import get_cache
        from src.intelligence.agent_pipeline import get_pipeline
        
        self.cache = get_cache()
        self.pipeline = get_pipeline()
        
        # Create refresh scheduler
        self.scheduler = RefreshScheduler(
            refresh_interval=1800,  # 30 minutes
            enable_file_watcher=True,
        )
        self.scheduler.set_refresh_callback(self._refresh_all_studies)
        
        self._is_running = False
        logger.info("AnalysisScheduler initialized")
    
    def start(self) -> None:
        """Start the integrated scheduler."""
        self.scheduler.start()
        self._is_running = True
        logger.info("AnalysisScheduler started")
    
    def stop(self) -> None:
        """Stop the integrated scheduler."""
        self.scheduler.stop()
        self._is_running = False
        logger.info("AnalysisScheduler stopped")
    
    def _refresh_all_studies(self) -> None:
        """Refresh analysis for all studies."""
        from src.data import StudyDiscovery
        
        try:
            # Discover all studies
            discovery = StudyDiscovery()
            studies = discovery.discover_studies()
            
            logger.info(f"Refreshing {len(studies)} studies...")
            
            for study_id in studies:
                try:
                    # Invalidate cache
                    self.cache.invalidate(f"analysis_{study_id}")
                    
                    # Note: Actual recompute happens on next request
                    # This is the cache-first pattern
                    
                except Exception as e:
                    logger.error(f"Error refreshing {study_id}: {e}")
            
            logger.info("Study refresh complete")
            
        except Exception as e:
            logger.error(f"Refresh all studies failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "is_running": self._is_running,
            "cache_stats": self.cache.get_stats(),
            "pipeline_stats": self.pipeline.get_pipeline_stats(),
            "scheduler_status": self.scheduler.get_status(),
        }


# ========================================
# SINGLETON INSTANCE
# ========================================

_scheduler_instance: Optional[AnalysisScheduler] = None


def get_scheduler() -> AnalysisScheduler:
    """Get or create singleton scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AnalysisScheduler()
    return _scheduler_instance


def start_scheduler() -> AnalysisScheduler:
    """Start the scheduler and return instance."""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "FileWatcher",
    "RefreshScheduler",
    "AnalysisScheduler",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
]
