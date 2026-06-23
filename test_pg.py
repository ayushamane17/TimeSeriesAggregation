import psycopg2
from psycopg2 import OperationalError

def verify_raw_postgres_connection():
    connection_config = {
        "host": "localhost",
        "port": "5432",
        "database": "postgres",
        "user": "postgres",
        "password": "root",
        "connect_timeout": 5 # Prevent background threads from hanging indefinitely
    }
    
    conn = None
    try:
        # Establish the raw connection socket
        conn = psycopg2.connect(**connection_config)
        
        # CRITICAL: Prevent the connection test from leaving an open, uncommitted transaction block
        conn.autocommit = True
        
        # Execute an active protocol wire-check via a cursor context manager
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            
        print("✅ Live database link verified successfully.")
        return {"success": True, "message": "Connected to PostgreSQL successfully."}
        
    except OperationalError as oe:
        error_msg = f"Network Handshake Timeout / Authentication Refused: {str(oe)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected Database Client Runtime Exception: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": error_msg}
        
    finally:
        # GUARANTEE: Sockets are completely closed and freed back to the system catalog
        if conn is not None:
            conn.close()
            print("💾 Database connection socket closed cleanly.")

if __name__ == "__main__":
    verify_raw_postgres_connection()