import sqlite3

conn = sqlite3.connect("agenteval.db")
conn.execute("DELETE FROM eval_cache")
conn.commit()
conn.close()
print("eval_cache cleared.")
