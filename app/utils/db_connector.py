import mysql.connector
import logging
from typing import Optional, List, Dict, Union

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class DatabaseConnector:
    """Singleton class to manage database connections."""
    _instance = None
    
    def __new__(cls, db_config=None):
        if cls._instance is None:
            cls._instance = super(DatabaseConnector, cls).__new__(cls)
            cls._instance.db_config = db_config
            cls._instance.connection = None
        return cls._instance
    
    def get_connection(self):
        """Get a database connection, creating a new one if needed."""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(**self.db_config)
            return self.connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch_all: bool = True) -> Union[List[Dict], Dict, None]:
        """Execute a database query and return results."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if fetch_all:
                return cursor.fetchall()
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
        finally:
            cursor.close()