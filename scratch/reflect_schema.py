import sqlite3
from sqlalchemy import create_engine, MetaData, inspect

def main():
    db_path = "agenteval.db"
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    print("================ REFLECTED TABLE SCHEMAS ================")
    for table_name in metadata.tables:
        print(f"\nTable: {table_name}")
        table = metadata.tables[table_name]
        for col in table.columns:
            print(f"  - {col.name}: {col.type} (primary_key={col.primary_key}, nullable={col.nullable})")
            
    print("=========================================================")

if __name__ == "__main__":
    main()
