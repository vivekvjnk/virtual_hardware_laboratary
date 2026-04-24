import functools
import logging
import inspect
import asyncio

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
