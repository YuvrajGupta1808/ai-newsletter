"""
Utility functions for validation and security
"""
import re
import logging
from email_validator import validate_email, EmailNotValidError
from functools import wraps
from flask import request, jsonify
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_email_address(email):
    """
    Robust email validation using email-validator library
    """
    try:
        # Validate and get normalized result
        validated_email = validate_email(email)
        return validated_email.email
    except EmailNotValidError:
        return None

def validate_topics(topics, valid_topics):
    """
    Validate that selected topics are from allowed list
    """
    if not topics or not isinstance(topics, list):
        return False
    
    # Check all topics are valid
    for topic in topics:
        if topic not in valid_topics:
            return False
    
    return True

def sanitize_input(text, max_length=255):
    """
    Basic input sanitization
    """
    if not text:
        return ""
    
    # Strip whitespace and limit length
    text = str(text).strip()[:max_length]
    
    # Remove potential HTML/script tags
    text = re.sub(r'<[^>]*>', '', text)
    
    return text

def log_security_event(event_type, details, request_info=None):
    """
    Log security-related events for monitoring
    """
    if request_info is None:
        request_info = {
            'ip': request.remote_addr if request else 'unknown',
            'user_agent': request.headers.get('User-Agent', 'unknown') if request else 'unknown'
        }
    
    logger.warning(f"SECURITY EVENT: {event_type} - {details} - IP: {request_info['ip']}")

# Simple in-memory rate limiting (for basic protection)
# In production, use Redis-based rate limiting
_rate_limit_storage = {}

def simple_rate_limit(max_requests=50, window_seconds=300):  # Increased for testing
    """
    Simple in-memory rate limiting decorator
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old entries
            cutoff_time = current_time - window_seconds
            _rate_limit_storage[client_ip] = [
                timestamp for timestamp in _rate_limit_storage.get(client_ip, [])
                if timestamp > cutoff_time
            ]
            
            # Check rate limit
            requests_in_window = len(_rate_limit_storage.get(client_ip, []))
            
            if requests_in_window >= max_requests:
                log_security_event("RATE_LIMIT_EXCEEDED", f"IP: {client_ip}, Requests: {requests_in_window}")
                return jsonify({
                    'error': 'Rate limit exceeded. Please try again later.'
                }), 429
            
            # Add current request
            if client_ip not in _rate_limit_storage:
                _rate_limit_storage[client_ip] = []
            _rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_secure_otp():
    """
    Generate a secure 6-digit OTP
    """
    import secrets
    # 6-digit OTP (100000 to 999999)
    return f"{secrets.randbelow(900000) + 100000}"

def validate_otp_format(otp):
    """
    Validate OTP format - must be exactly 6 digits
    """
    if not otp:
        return False
    
    # Must be exactly 6 digits
    return bool(re.match(r'^\d{6}$', otp))
