print("Testing Flask-Login import...")
try:
    import flask_login
    print("Flask-Login OK.")
except ImportError:
    print("--- ERROR: Flask-Login is NOT installed. ---")
    print("--- Please run: pip install Flask-Login ---")
    exit()
except Exception as e:
    print(f"An unexpected error occurred with Flask-Login: {e}")
    exit()

print("\nTesting BSON import...")
try:
    from bson import json_util
    print("BSON OK.")
except ImportError:
    print("--- ERROR: BSON is NOT installed or has a conflict. ---")
    print("--- This is a problem with the 'pymongo' library. ---")
except Exception as e:
    print(f"An unexpected error occurred with BSON: {e}")
    exit()

print("\nAll new imports seem to be working.")