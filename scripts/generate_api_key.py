import argparse
import secrets
from agenteval.sdk.storage import TraceStore

def main():
    parser = argparse.ArgumentParser(description="Generate a secure API key for AgentEval and store its hash in the database.")
    parser.add_argument("--user-id", required=True, help="Unique string identifier for the user (e.g. 'alice')")
    parser.add_argument("--db-path", default="agenteval.db", help="Path to the SQLite database file")
    args = parser.parse_args()

    # Generate a cryptographically secure random hexadecimal key
    api_key = secrets.token_hex(24)
    
    # Store the user and key hash in the SQLite database
    store = TraceStore(db_path=args.db_path)
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
