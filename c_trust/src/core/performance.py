"""
C-TRUST Performance Monitoring and Optimization Module
======================================================
Provides progress indicators, retry logic with exponential backoff,
and resource constraint handling through queuing.

**Validates: Requirements 9.3, 9.4, 9.5**

Key Features:
1. Progress indicators for batch processing
2. Retry logic with exponential backoff
3. Resource constraint handling through queuing
4. Performance metrics collection and reporting
"""

import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
import random

from src.core import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


# ========================================
# PROGRESS INDICATORS
# ========================================

class ProgressStatus(str, Enum):
    """Status of a progress indicator"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ProgressInfo:
    """
    Progress information for a batch operation.
    
    **Validates: Requirements 9.4**
    """
    task_id: str
    task_name: str
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_item: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Calculate elapsed time"""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return end - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[timedelta]:
        """Estimate remaining time based on current progress"""
        if self.processed_items == 0 or self.start_time is None:
            return None
        
        elapsed = self.elapsed_time
        if elapsed is None:
            return None
        
        items_remaining = self.total_items - self.processed_items
        time_per_item = elapsed.total_seconds() / self.processed_items
        remaining_seconds = items_remaining * time_per_item
        
        return timedelta(seconds=remaining_seconds)
    
    @property
    def items_per_second(self) -> float:
        """Calculate processing rate"""
        elapsed = self.elapsed_time
        if elapsed is None or elapsed.total_seconds() == 0:
            return 0.0
        return self.processed_items / elapsed.total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "status": self.status.value,
            "progress_percentage": round(self.progress_percentage, 2),
            "elapsed_seconds": self.elapsed_time.total_seconds() if self.elapsed_time else None,
            "estimated_remaining_seconds": self.estimated_remaining.total_seconds() if self.estimated_remaining else None,
            "items_per_second": round(self.items_per_second, 2),
            "current_item": self.current_item,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class ProgressTracker:
    """
    Thread-safe progress tracker for batch operations.
    
    **Validates: Requirements 9.4**
    
    Usage:
        tracker = ProgressTracker("batch_001", "Processing Studies", total_items=23)
        tracker.start()
        
        for study in studies:
            tracker.update_current(study.study_id)
            process_study(study)
            tracker.increment()
        
        tracker.complete()
    """
    
    def __init__(
        self,
        task_id: str,
        task_name: str,
        total_items: int,
        callback: Optional[Callable[[ProgressInfo], None]] = None
    ):
        """
        Initialize progress tracker.
        
        Args:
            task_id: Unique identifier for the task
            task_name: Human-readable task name
            total_items: Total number of items to process
            callback: Optional callback function called on each update
        """
        self._lock = threading.Lock()
        self._progress = ProgressInfo(
            task_id=task_id,
            task_name=task_name,
            total_items=total_items,
        )
        self._callback = callback
        self._listeners: List[Callable[[ProgressInfo], None]] = []
    
    def add_listener(self, listener: Callable[[ProgressInfo], None]) -> None:
        """Add a progress listener"""
        self._listeners.append(listener)
    
    def start(self) -> None:
        """Mark task as started"""
        with self._lock:
            self._progress.status = ProgressStatus.IN_PROGRESS
            self._progress.start_time = datetime.now()
            self._notify()
            logger.info(f"Started task: {self._progress.task_name} ({self._progress.total_items} items)")
    
    def update_current(self, item_name: str) -> None:
        """Update current item being processed"""
        with self._lock:
            self._progress.current_item = item_name
            self._notify()
    
    def increment(self, count: int = 1) -> None:
        """Increment processed items count"""
        with self._lock:
            self._progress.processed_items += count
            self._notify()
            
            # Log progress at intervals
            if self._progress.processed_items % max(1, self._progress.total_items // 10) == 0:
                logger.info(
                    f"Progress: {self._progress.progress_percentage:.1f}% "
                    f"({self._progress.processed_items}/{self._progress.total_items})"
                )
    
    def increment_failed(self, count: int = 1) -> None:
        """Increment failed items count"""
        with self._lock:
            self._progress.failed_items += count
            self._notify()
    
    def complete(self) -> None:
        """Mark task as completed"""
        with self._lock:
            self._progress.status = ProgressStatus.COMPLETED
            self._progress.end_time = datetime.now()
            self._notify()
            
            elapsed = self._progress.elapsed_time
            logger.info(
                f"Completed task: {self._progress.task_name} - "
                f"{self._progress.processed_items} processed, "
                f"{self._progress.failed_items} failed, "
                f"elapsed: {elapsed.total_seconds():.2f}s"
            )
    
    def fail(self, error_message: str) -> None:
        """Mark task as failed"""
        with self._lock:
            self._progress.status = ProgressStatus.FAILED
            self._progress.end_time = datetime.now()
            self._progress.error_message = error_message
            self._notify()
            logger.error(f"Failed task: {self._progress.task_name} - {error_message}")
    
    def cancel(self) -> None:
        """Mark task as cancelled"""
        with self._lock:
            self._progress.status = ProgressStatus.CANCELLED
            self._progress.end_time = datetime.now()
            self._notify()
            logger.warning(f"Cancelled task: {self._progress.task_name}")
    
    def get_progress(self) -> ProgressInfo:
        """Get current progress info"""
        with self._lock:
            return self._progress
    
    def _notify(self) -> None:
        """Notify listeners of progress update"""
        if self._callback:
            try:
                self._callback(self._progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        for listener in self._listeners:
            try:
                listener(self._progress)
            except Exception as e:
                logger.warning(f"Progress listener error: {e}")


# ========================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# ========================================

@dataclass
class RetryConfig:
    """
    Configuration for retry logic.
    
    **Validates: Requirements 9.5**
    """
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: tuple = (Exception,)


@dataclass
class RetryResult(Generic[T]):
    """Result of a retry operation"""
    success: bool
    result: Optional[T] = None
    attempts: int = 0
    total_delay: float = 0.0
    last_exception: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "attempts": self.attempts,
            "total_delay": round(self.total_delay, 2),
            "last_exception": str(self.last_exception) if self.last_exception else None,
        }


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    Calculate delay for exponential backoff.
    
    **Validates: Requirements 9.5**
    
    Formula: delay = min(initial_delay * (base ^ attempt), max_delay)
    With optional jitter: delay * random(0.5, 1.5)
    """
    delay = config.initial_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add jitter: multiply by random factor between 0.5 and 1.5
        jitter_factor = 0.5 + random.random()
        delay *= jitter_factor
    
    return delay


def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> RetryResult[T]:
    """
    Execute function with retry logic and exponential backoff.
    
    **Validates: Requirements 9.5**
    
    Args:
        func: Function to execute
        config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        RetryResult with success status and result
    """
    config = config or RetryConfig()
    
    attempts = 0
    total_delay = 0.0
    last_exception = None
    
    while attempts <= config.max_retries:
        try:
            result = func(*args, **kwargs)
            return RetryResult(
                success=True,
                result=result,
                attempts=attempts + 1,
                total_delay=total_delay,
            )
        except config.retryable_exceptions as e:
            last_exception = e
            attempts += 1
            
            if attempts > config.max_retries:
                logger.warning(
                    f"Max retries ({config.max_retries}) exceeded for {func.__name__}: {e}"
                )
                break
            
            delay = calculate_backoff_delay(attempts - 1, config)
            total_delay += delay
            
            logger.info(
                f"Retry {attempts}/{config.max_retries} for {func.__name__} "
                f"after {delay:.2f}s delay: {e}"
            )
            
            time.sleep(delay)
    
    return RetryResult(
        success=False,
        result=None,
        attempts=attempts,
        total_delay=total_delay,
        last_exception=last_exception,
    )


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions.
    
    **Validates: Requirements 9.5**
    
    Usage:
        @with_retry(RetryConfig(max_retries=3))
        def fetch_data():
            ...
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result = retry_with_backoff(func, config, *args, **kwargs)
            if result.success:
                return result.result
            raise result.last_exception or Exception("Retry failed")
        return wrapper
    return decorator


# ========================================
# RESOURCE CONSTRAINT HANDLING (QUEUING)
# ========================================

@dataclass
class QueuedTask(Generic[T]):
    """A task in the processing queue"""
    task_id: str
    func: Callable[..., T]
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more priority
    submitted_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other: 'QueuedTask') -> bool:
        """Compare by priority (higher first), then by submission time"""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.submitted_at < other.submitted_at


@dataclass
class TaskResult(Generic[T]):
    """Result of a queued task execution"""
    task_id: str
    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    queued_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "error": self.error,
            "execution_time": round(self.execution_time, 3),
            "queued_time": round(self.queued_time, 3),
        }


class ResourceConstrainedQueue:
    """
    Queue for handling resource constraints through controlled concurrency.
    
    **Validates: Requirements 9.3**
    
    Features:
    - Configurable max concurrent workers
    - Priority-based task scheduling
    - Graceful shutdown
    - Task result tracking
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        max_queue_size: int = 100,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize resource-constrained queue.
        
        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum queue size (0 = unlimited)
            retry_config: Configuration for retry logic
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.retry_config = retry_config or RetryConfig()
        
        self._queue: queue.PriorityQueue = queue.PriorityQueue(
            maxsize=max_queue_size if max_queue_size > 0 else 0
        )
        self._executor: Optional[ThreadPoolExecutor] = None
        self._results: Dict[str, TaskResult] = {}
        self._lock = threading.Lock()
        self._running = False
        self._futures: Dict[str, Future] = {}
        
        logger.info(
            f"ResourceConstrainedQueue initialized: "
            f"max_workers={max_workers}, max_queue_size={max_queue_size}"
        )
    
    def start(self) -> None:
        """Start the queue processor"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            logger.info("ResourceConstrainedQueue started")
    
    def stop(self, wait: bool = True) -> None:
        """
        Stop the queue processor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            if self._executor:
                self._executor.shutdown(wait=wait)
                self._executor = None
            
            logger.info("ResourceConstrainedQueue stopped")
    
    def submit(
        self,
        task_id: str,
        func: Callable[..., T],
        *args,
        priority: int = 0,
        **kwargs
    ) -> bool:
        """
        Submit a task to the queue.
        
        Args:
            task_id: Unique task identifier
            func: Function to execute
            *args: Positional arguments
            priority: Task priority (higher = more priority)
            **kwargs: Keyword arguments
        
        Returns:
            True if task was queued, False if queue is full
        """
        task = QueuedTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )
        
        try:
            self._queue.put_nowait(task)
            logger.debug(f"Task {task_id} queued with priority {priority}")
            
            # If executor is running, submit for execution
            if self._running and self._executor:
                self._submit_task(task)
            
            return True
        except queue.Full:
            logger.warning(f"Queue full, task {task_id} rejected")
            return False
    
    def _submit_task(self, task: QueuedTask) -> None:
        """Submit task to executor"""
        future = self._executor.submit(self._execute_task, task)
        
        with self._lock:
            self._futures[task.task_id] = future
    
    def _execute_task(self, task: QueuedTask) -> TaskResult:
        """Execute a queued task with retry logic"""
        queued_time = (datetime.now() - task.submitted_at).total_seconds()
        start_time = time.time()
        
        try:
            # Execute with retry
            retry_result = retry_with_backoff(
                task.func,
                self.retry_config,
                *task.args,
                **task.kwargs
            )
            
            execution_time = time.time() - start_time
            
            result = TaskResult(
                task_id=task.task_id,
                success=retry_result.success,
                result=retry_result.result if retry_result.success else None,
                error=str(retry_result.last_exception) if not retry_result.success else None,
                execution_time=execution_time,
                queued_time=queued_time,
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                queued_time=queued_time,
            )
            logger.error(f"Task {task.task_id} failed: {e}")
        
        # Store result
        with self._lock:
            self._results[task.task_id] = result
            if task.task_id in self._futures:
                del self._futures[task.task_id]
        
        return result
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Get result for a task.
        
        Args:
            task_id: Task identifier
            timeout: Maximum time to wait (None = don't wait)
        
        Returns:
            TaskResult if available, None otherwise
        """
        # Check if result already available
        with self._lock:
            if task_id in self._results:
                return self._results[task_id]
            
            future = self._futures.get(task_id)
        
        # Wait for future if exists
        if future and timeout:
            try:
                future.result(timeout=timeout)
                with self._lock:
                    return self._results.get(task_id)
            except Exception:
                pass
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self._lock:
            return {
                "running": self._running,
                "queue_size": self._queue.qsize(),
                "pending_tasks": len(self._futures),
                "completed_tasks": len(self._results),
                "max_workers": self.max_workers,
                "max_queue_size": self.max_queue_size,
            }
    
    def process_all(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """
        Process all queued tasks and return results.
        
        Args:
            timeout: Maximum time to wait for all tasks
        
        Returns:
            List of TaskResults
        """
        if not self._running:
            self.start()
        
        # Submit all queued tasks
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
                self._submit_task(task)
            except queue.Empty:
                break
        
        # Wait for all futures
        start_time = time.time()
        
        with self._lock:
            futures_copy = list(self._futures.values())
        
        for future in as_completed(futures_copy, timeout=timeout):
            if timeout and (time.time() - start_time) > timeout:
                break
            try:
                future.result()
            except Exception:
                pass
        
        with self._lock:
            return list(self._results.values())


# ========================================
# PERFORMANCE METRICS
# ========================================

@dataclass
class PerformanceMetrics:
    """
    Performance metrics for monitoring system health.
    
    **Validates: Requirements 9.3, 9.4**
    """
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    items_processed: int = 0
    items_failed: int = 0
    total_retries: int = 0
    peak_memory_mb: float = 0.0
    avg_item_time_ms: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        """Get operation duration in seconds"""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def throughput(self) -> float:
        """Calculate items per second"""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.items_processed / duration
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.items_processed + self.items_failed
        if total == 0:
            return 0.0
        return self.items_processed / total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_name": self.operation_name,
            "duration_seconds": round(self.duration_seconds, 2),
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "total_retries": self.total_retries,
            "throughput": round(self.throughput, 2),
            "success_rate": round(self.success_rate * 100, 2),
            "avg_item_time_ms": round(self.avg_item_time_ms, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
        }


class PerformanceMonitor:
    """
    Monitor for tracking performance metrics.
    
    **Validates: Requirements 9.3, 9.4**
    """
    
    def __init__(self):
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation_name: str) -> str:
        """Start tracking an operation"""
        operation_id = f"{operation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self._lock:
            self._metrics[operation_id] = PerformanceMetrics(
                operation_name=operation_name,
                start_time=datetime.now(),
            )
        
        logger.debug(f"Started tracking operation: {operation_id}")
        return operation_id
    
    def record_item(self, operation_id: str, success: bool = True, retries: int = 0) -> None:
        """Record processing of an item"""
        with self._lock:
            if operation_id not in self._metrics:
                return
            
            metrics = self._metrics[operation_id]
            if success:
                metrics.items_processed += 1
            else:
                metrics.items_failed += 1
            metrics.total_retries += retries
    
    def end_operation(self, operation_id: str) -> Optional[PerformanceMetrics]:
        """End tracking an operation"""
        with self._lock:
            if operation_id not in self._metrics:
                return None
            
            metrics = self._metrics[operation_id]
            metrics.end_time = datetime.now()
            
            # Calculate average item time
            total_items = metrics.items_processed + metrics.items_failed
            if total_items > 0:
                metrics.avg_item_time_ms = (metrics.duration_seconds * 1000) / total_items
            
            logger.info(
                f"Operation {operation_id} completed: "
                f"{metrics.items_processed} processed, "
                f"{metrics.items_failed} failed, "
                f"{metrics.duration_seconds:.2f}s"
            )
            
            return metrics
    
    def get_metrics(self, operation_id: str) -> Optional[PerformanceMetrics]:
        """Get metrics for an operation"""
        with self._lock:
            return self._metrics.get(operation_id)
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get all tracked metrics"""
        with self._lock:
            return self._metrics.copy()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


__all__ = [
    "ProgressStatus",
    "ProgressInfo",
    "ProgressTracker",
    "RetryConfig",
    "RetryResult",
    "calculate_backoff_delay",
    "retry_with_backoff",
    "with_retry",
    "QueuedTask",
    "TaskResult",
    "ResourceConstrainedQueue",
    "PerformanceMetrics",
    "PerformanceMonitor",
    "performance_monitor",
]
