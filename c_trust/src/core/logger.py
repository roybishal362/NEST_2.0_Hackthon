"""
logging configuration for C-TRUST system
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import config_manager


class CTrustFormatter(logging.Formatter):
    """Custom formatter for C-TRUST logs"""
    
    def __init__(self):
        super().__init__()
        self.fmt = "[{asctime}] {levelname:8} | {name:20} | {message}"
        self.style = "{"
    
    def format(self, record):
        """Format log record with custom styling"""
        # Add color coding for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        if hasattr(record, 'levelname'):
            color = colors.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


class AuditLogger:
    """Specialized logger for audit events"""
    
    def __init__(self, log_file: str = "logs/audit.log"):
        self.logger = logging.getLogger("c_trust.audit")
        self.logger.setLevel(logging.INFO)
        
        # Create audit log file handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s | AUDIT | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_event(self, event_type: str, entity_id: str, user_id: str, 
                  action: str, details: Optional[dict] = None):
        """Log audit event"""
        audit_data = {
            "event_type": event_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"{audit_data}")


def setup_logging(log_level: str = None, log_file: str = None) -> None:
    """Setup comprehensive logging for the application"""
    
    config = config_manager.get_config()
    log_level = log_level or config.log_level
    log_file = log_file or config.log_file
    
    # Create logs directory
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(CTrustFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        f"logs/{log_file}",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error handler - separate file for errors
    error_handler = logging.handlers.RotatingFileHandler(
        "logs/error.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger("c_trust.core")
    logger.info("C-TRUST logging system initialized")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log file: logs/{log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for specific component"""
    return logging.getLogger(f"c_trust.{name}")


# Global audit logger instance
audit_logger = AuditLogger()
