import os
import sys
import psycopg2
import config

def seed_database():
    password = config.PG_PASSWORD or os.environ.get("PGPASSWORD")
    if not password:
        import getpass
        print(f"Connecting to PostgreSQL on {config.PG_HOST}:{config.PG_PORT} as user '{config.PG_USER}'...")
        password = getpass.getpass("Enter PostgreSQL password: ")

    try:
        conn = psycopg2.connect(
            host=config.PG_HOST,
            port=config.PG_PORT,
            user=config.PG_USER,
            password=password,
            dbname=config.PG_DATABASE
        )
        print("Connected to PostgreSQL successfully.")
        
        with open("seed_ecommerce.sql", "r", encoding="utf-8") as f:
            sql_script = f.read()

        with conn.cursor() as cur:
            cur.execute(sql_script)
        conn.commit()
        conn.close()
        print("Successfully created tables and seeded sample e-commerce data!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed_database()
