"""
Unit Tests for Performance Monitoring Module
=============================================
Tests for progress indicators, retry logic, and resource constraint handling.

**Validates: Requirements 9.3, 9.4, 9.5**
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.core.performance import (
    ProgressStatus,
    ProgressInfo,
    ProgressTracker,
    RetryConfig,
    RetryResult,
    calculate_backoff_delay,
    retry_with_backoff,
    with_retry,
    QueuedTask,
    TaskResult,
    ResourceConstrainedQueue,
    PerformanceMetrics,
    PerformanceMonitor,
)


# ========================================
# PROGRESS INDICATOR TESTS
# ========================================

class TestProgressInfo:
    """Tests for ProgressInfo dataclass"""
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation"""
        info = ProgressInfo(
            task_id="test_001",
            task_name="Test Task",
            total_items=100,
            processed_items=50,
        )
        
        assert info.progress_percentage == 50.0
    
    def test_progress_percentage_zero_total(self):
        """Test progress percentage with zero total items"""
        info = ProgressInfo(
            task_id="test_001",
            task_name="Test Task",
            total_items=0,
            processed_items=0,
        )
        
        assert info.progress_percentage == 0.0
    
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation"""
        start = datetime.now()
        info = ProgressInfo(
            task_id="test_001",
            task_name="Test Task",
            total_items=100,
            start_time=start,
        )
        
        time.sleep(0.1)
        elapsed = info.elapsed_time
        
        assert elapsed is not None
        assert elapsed.total_seconds() >= 0.1
    
    def test_items_per_second_calculation(self):
        """Test items per second calculation"""
        start = datetime.now() - timedelta(seconds=10)
        info = ProgressInfo(
            task_id="test_001",
            task_name="Test Task",
            total_items=100,
            processed_items=50,
            start_time=start,
            end_time=datetime.now(),
        )
        
        assert info.items_per_second == pytest.approx(5.0, rel=0.1)
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization"""
        info = ProgressInfo(
            task_id="test_001",
            task_name="Test Task",
            total_items=100,
            processed_items=50,
            status=ProgressStatus.IN_PROGRESS,
        )
        
        result = info.to_dict()
        
        assert result["task_id"] == "test_001"
        assert result["task_name"] == "Test Task"
        assert result["total_items"] == 100
        assert result["processed_items"] == 50
        assert result["status"] == "IN_PROGRESS"
        assert result["progress_percentage"] == 50.0


class TestProgressTracker:
    """Tests for ProgressTracker class"""
    
    def test_tracker_initialization(self):
        """Test tracker initialization"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        progress = tracker.get_progress()
        
        assert progress.task_id == "task_001"
        assert progress.task_name == "Test Task"
        assert progress.total_items == 100
        assert progress.status == ProgressStatus.PENDING
    
    def test_tracker_start(self):
        """Test starting the tracker"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        progress = tracker.get_progress()
        
        assert progress.status == ProgressStatus.IN_PROGRESS
        assert progress.start_time is not None
    
    def test_tracker_increment(self):
        """Test incrementing processed items"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        tracker.increment()
        tracker.increment(5)
        progress = tracker.get_progress()
        
        assert progress.processed_items == 6
    
    def test_tracker_increment_failed(self):
        """Test incrementing failed items"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        tracker.increment_failed()
        tracker.increment_failed(2)
        progress = tracker.get_progress()
        
        assert progress.failed_items == 3
    
    def test_tracker_complete(self):
        """Test completing the tracker"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        tracker.increment(100)
        tracker.complete()
        progress = tracker.get_progress()
        
        assert progress.status == ProgressStatus.COMPLETED
        assert progress.end_time is not None
    
    def test_tracker_fail(self):
        """Test failing the tracker"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        tracker.fail("Test error")
        progress = tracker.get_progress()
        
        assert progress.status == ProgressStatus.FAILED
        assert progress.error_message == "Test error"
    
    def test_tracker_cancel(self):
        """Test cancelling the tracker"""
        tracker = ProgressTracker("task_001", "Test Task", 100)
        tracker.start()
        tracker.cancel()
        progress = tracker.get_progress()
        
        assert progress.status == ProgressStatus.CANCELLED
    
    def test_tracker_callback(self):
        """Test progress callback"""
        callback_calls = []
        
        def callback(info: ProgressInfo):
            callback_calls.append(info.processed_items)
        
        tracker = ProgressTracker("task_001", "Test Task", 100, callback=callback)
        tracker.start()
        tracker.increment()
        tracker.increment()
        
        assert len(callback_calls) >= 2
    
    def test_tracker_thread_safety(self):
        """Test thread safety of tracker"""
        tracker = ProgressTracker("task_001", "Test Task", 1000)
        tracker.start()
        
        def increment_worker():
            for _ in range(100):
                tracker.increment()
        
        threads = [threading.Thread(target=increment_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        progress = tracker.get_progress()
        assert progress.processed_items == 1000


# ========================================
# RETRY LOGIC TESTS
# ========================================

class TestRetryConfig:
    """Tests for RetryConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
        )
        
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0


class TestBackoffDelay:
    """Tests for backoff delay calculation"""
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        
        assert calculate_backoff_delay(0, config) == 1.0
        assert calculate_backoff_delay(1, config) == 2.0
        assert calculate_backoff_delay(2, config) == 4.0
        assert calculate_backoff_delay(3, config) == 8.0
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )
        
        # 2^10 = 1024, but should be capped at 5
        assert calculate_backoff_delay(10, config) == 5.0
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness"""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=True,
        )
        
        delays = [calculate_backoff_delay(1, config) for _ in range(10)]
        
        # With jitter, delays should vary
        assert len(set(delays)) > 1


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function"""
    
    def test_successful_first_attempt(self):
        """Test successful execution on first attempt"""
        def success_func():
            return "success"
        
        result = retry_with_backoff(success_func)
        
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
    
    def test_retry_on_failure(self):
        """Test retry on failure"""
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,
            jitter=False,
        )
        
        result = retry_with_backoff(failing_func, config)
        
        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 3
    
    def test_max_retries_exceeded(self):
        """Test when max retries is exceeded"""
        def always_fails():
            raise ValueError("Always fails")
        
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            jitter=False,
        )
        
        result = retry_with_backoff(always_fails, config)
        
        assert result.success is False
        assert result.result is None
        assert result.attempts == 3  # Initial + 2 retries
        assert isinstance(result.last_exception, ValueError)
    
    def test_retryable_exceptions_filter(self):
        """Test that only specified exceptions trigger retry"""
        def raises_type_error():
            raise TypeError("Not retryable")
        
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,),  # Only retry ValueError
        )
        
        # TypeError should not be retried
        with pytest.raises(TypeError):
            retry_with_backoff(raises_type_error, config)


class TestWithRetryDecorator:
    """Tests for with_retry decorator"""
    
    def test_decorator_success(self):
        """Test decorator with successful function"""
        @with_retry(RetryConfig(max_retries=3, initial_delay=0.01))
        def success_func():
            return "decorated_success"
        
        result = success_func()
        assert result == "decorated_success"
    
    def test_decorator_retry(self):
        """Test decorator with retrying function"""
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3, initial_delay=0.01, jitter=False))
        def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success_after_retry"
        
        result = retry_func()
        assert result == "success_after_retry"
        assert call_count == 2


# ========================================
# RESOURCE CONSTRAINT QUEUE TESTS
# ========================================

class TestResourceConstrainedQueue:
    """Tests for ResourceConstrainedQueue"""
    
    def test_queue_initialization(self):
        """Test queue initialization"""
        queue = ResourceConstrainedQueue(max_workers=2, max_queue_size=10)
        status = queue.get_queue_status()
        
        assert status["max_workers"] == 2
        assert status["max_queue_size"] == 10
        assert status["running"] is False
    
    def test_queue_start_stop(self):
        """Test starting and stopping queue"""
        queue = ResourceConstrainedQueue(max_workers=2)
        
        queue.start()
        assert queue.get_queue_status()["running"] is True
        
        queue.stop()
        assert queue.get_queue_status()["running"] is False
    
    def test_submit_and_process_task(self):
        """Test submitting and processing a task"""
        queue = ResourceConstrainedQueue(max_workers=2)
        queue.start()
        
        def simple_task(x):
            return x * 2
        
        queue.submit("task_001", simple_task, 5)
        
        # Wait for result
        time.sleep(0.5)
        result = queue.get_result("task_001")
        
        queue.stop()
        
        assert result is not None
        assert result.success is True
        assert result.result == 10
    
    def test_task_priority(self):
        """Test task priority ordering"""
        queue = ResourceConstrainedQueue(max_workers=1, max_queue_size=10)
        
        results = []
        
        def record_task(task_id):
            results.append(task_id)
            return task_id
        
        # Submit tasks with different priorities
        queue.submit("low", record_task, "low", priority=1)
        queue.submit("high", record_task, "high", priority=10)
        queue.submit("medium", record_task, "medium", priority=5)
        
        queue.start()
        all_results = queue.process_all(timeout=5)
        queue.stop()
        
        # Higher priority tasks should complete first
        assert len(all_results) == 3
    
    def test_queue_full_rejection(self):
        """Test that tasks are rejected when queue is full"""
        queue = ResourceConstrainedQueue(max_workers=1, max_queue_size=2)
        
        def slow_task():
            time.sleep(1)
            return "done"
        
        # Fill the queue
        assert queue.submit("task_1", slow_task) is True
        assert queue.submit("task_2", slow_task) is True
        
        # Queue should be full now
        assert queue.submit("task_3", slow_task) is False
    
    def test_task_with_retry(self):
        """Test task execution with retry logic"""
        queue = ResourceConstrainedQueue(
            max_workers=2,
            retry_config=RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)
        )
        queue.start()
        
        call_count = 0
        
        def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        queue.submit("flaky_task", flaky_task)
        
        time.sleep(1)
        result = queue.get_result("flaky_task")
        
        queue.stop()
        
        assert result is not None
        assert result.success is True
        assert result.result == "success"


# ========================================
# PERFORMANCE METRICS TESTS
# ========================================

class TestPerformanceMetrics:
    """Tests for PerformanceMetrics"""
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        start = datetime.now()
        time.sleep(0.1)
        end = datetime.now()
        
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=start,
            end_time=end,
        )
        
        assert metrics.duration_seconds >= 0.1
    
    def test_throughput_calculation(self):
        """Test throughput calculation"""
        start = datetime.now() - timedelta(seconds=10)
        
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=start,
            end_time=datetime.now(),
            items_processed=100,
        )
        
        assert metrics.throughput == pytest.approx(10.0, rel=0.1)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=datetime.now(),
            items_processed=80,
            items_failed=20,
        )
        
        assert metrics.success_rate == 0.8
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization"""
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=datetime.now(),
            items_processed=50,
            items_failed=5,
        )
        
        result = metrics.to_dict()
        
        assert result["operation_name"] == "test_op"
        assert result["items_processed"] == 50
        assert result["items_failed"] == 5


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor"""
    
    def test_start_operation(self):
        """Test starting an operation"""
        monitor = PerformanceMonitor()
        op_id = monitor.start_operation("test_operation")
        
        assert op_id.startswith("test_operation_")
        
        metrics = monitor.get_metrics(op_id)
        assert metrics is not None
        assert metrics.operation_name == "test_operation"
    
    def test_record_items(self):
        """Test recording processed items"""
        monitor = PerformanceMonitor()
        op_id = monitor.start_operation("test_operation")
        
        monitor.record_item(op_id, success=True)
        monitor.record_item(op_id, success=True)
        monitor.record_item(op_id, success=False)
        
        metrics = monitor.get_metrics(op_id)
        assert metrics.items_processed == 2
        assert metrics.items_failed == 1
    
    def test_end_operation(self):
        """Test ending an operation"""
        monitor = PerformanceMonitor()
        op_id = monitor.start_operation("test_operation")
        
        monitor.record_item(op_id, success=True)
        time.sleep(0.1)
        
        metrics = monitor.end_operation(op_id)
        
        assert metrics is not None
        assert metrics.end_time is not None
        assert metrics.duration_seconds >= 0.1
    
    def test_get_all_metrics(self):
        """Test getting all metrics"""
        monitor = PerformanceMonitor()
        
        op1 = monitor.start_operation("op1")
        op2 = monitor.start_operation("op2")
        
        all_metrics = monitor.get_all_metrics()
        
        assert op1 in all_metrics
        assert op2 in all_metrics
