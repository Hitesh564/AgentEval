import argparse
import secrets
from agenteval.sdk.storage import TraceStore
from agenteval.sdk.database import resolve_database_url

def main():
    parser = argparse.ArgumentParser(description="Generate a secure API key for AgentEval and store its hash in the database.")
    parser.add_argument("--user-id", required=True, help="Unique string identifier for the user (e.g. 'alice')")
    parser.add_argument("--database-url", default=None, help="Database URL or SQLite path. Defaults to AGENTEVAL_DATABASE_URL when set.")
    args = parser.parse_args()

    # Generate a cryptographically secure random hexadecimal key
    api_key = secrets.token_hex(24)
    
    database_url = resolve_database_url(args.database_url, allow_sqlite_fallback=True)
    store = TraceStore(database_url=database_url)
    store.create_user(args.user_id, api_key)
    
    print("=================================================================")
    print("USER GENERATED SUCCESSFULLY")
    print("=================================================================")
    print(f"User ID:    {args.user_id}")
    print(f"API Key:    {api_key}")
    print("=================================================================")
    print("WARNING: This API key is printed ONCE. Store it securely.")
    print("=================================================================")

if __name__ == "__main__":
    main()
