import functools
import logging
import inspect
from pathlib import Path
from logging.handlers import RotatingFileHandler


def handle_errors(func=None, *, on_error=None):
    """
    Decorator to handle errors in functions.
    
    Args:
        func: The function to decorate.
        on_error: A callable or a string representing a method name on the first argument (self).
                 The handler will be called with (*args, **kwargs, error=e).
    """
    if func is None:
        return lambda f: handle_errors(f, on_error=on_error)
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"[vhl_common:error handler] Error in {func.__name__}: {e}")
            
            if on_error:
                handler = on_error
                is_method = False
                # If on_error is a string, it's a method name on the first argument (likely 'self')
                if isinstance(on_error, str) and args:
                    handler = getattr(args[0], on_error, None)
                    is_method = True
                
                if callable(handler):
                    try:
                        # If it's a bound method, args[0] (self) is already bound, 
                        # so we should only pass the remaining args to avoid passing self twice.
                        handler_args = args[1:] if is_method and len(args) > 0 else args
                        
                        if inspect.iscoroutinefunction(handler):
                            await handler(*handler_args, **kwargs, error=e)
                        else:
                            handler(*handler_args, **kwargs, error=e)
                    except Exception as he:
                        logging.error(f"[vhl_common:error handler] Error in on_error handler: {he}")
            
            return None
    return wrapper




def setup_dedicated_logger(
    logger_name: str,
    log_filename: str,
    log_dir: str = "logs",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB default
    backup_count: int = 5,             # Keep 5 old log files
    level: int = logging.DEBUG,
    propagate: bool = True,
    extra_loggers: list[logging.Logger] | None = None
) -> logging.Logger:
    """
    Creates a logger with automatic log rotation.
    
    Args:
        logger_name: Unique ID for the logger.
        log_filename: Filename (e.g. 'archy_agent.log').
        log_dir: Directory for logs.
        max_bytes: Max size per file before rotating.
        backup_count: Number of historical files to keep.
        level: Logging level.
        propagate: Whether to send logs to the root logger.
        extra_loggers: Additional loggers that should receive the same file handler.
    """


    target_dir = Path(log_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / log_filename

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = propagate

    # Prevent duplicate handlers if the logger is fetched multiple times
    if not logger.handlers:
        # RotatingFileHandler handles the cleanup automatically
        handler = RotatingFileHandler(
            log_path, 
            maxBytes=max_bytes, 
            backupCount=backup_count,
            encoding='utf-8' # Good practice for LLM output (emojis/special chars)
        )
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Attach the handler to any additional loggers requested
        if extra_loggers:
            for el in extra_loggers:
                if handler not in el.handlers:
                    el.setLevel(level)
                    el.addHandler(handler)

    return logger