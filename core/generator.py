import uuid
import random
import string

def generate_extension_id():
    """Generate a unique extension ID"""
    return str(uuid.uuid4())

def generate_random_string(length=10):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))