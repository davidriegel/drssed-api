from sys import exit
from time import perf_counter
from mysql.connector import pooling, MySQLConnection
from app.utils.logging import get_logger
from os import getenv

logger = get_logger()

class Database:
    _pool: pooling.MySQLConnectionPool = None
    
    @classmethod
    def getConnection(cls) -> MySQLConnection:
        if cls._pool is None:
            
            
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    pool_name="connectionPool",
                    pool_size=5,
                    host=getenv("DATABASE_HOST", "localhost"),
                    port=getenv("DATABASE_PORT", "3306"),
                    user=getenv("DATABASE_USERNAME"),
                    password=getenv("DATABASE_PASSWORD"),
                    database=getenv("DATABASE_NAME")
                )
                
                connection = cls._pool.get_connection()
                connection.ping()
                connection.close()
                
                logger.debug(f"Successfully created database connection pool.")
            except Exception as e:
                logger.critical(f"Failed to create database connection pool: {e}")
                exit(1)

        return cls._pool.get_connection()
    
    @classmethod
    def health(cls) -> dict:
        start = perf_counter()
        connection = None
        cursor = None
        try:
            connection = cls.getConnection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return {
                "status": "ok",
                "latency_ms": round((perf_counter() - start) * 1000, 2),
            }
        except Exception as exc:
            logger.warning(f"Database health check failed: {exc}")
            return {
                "status": "error",
                "latency_ms": round((perf_counter() - start) * 1000, 2),
            }
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass