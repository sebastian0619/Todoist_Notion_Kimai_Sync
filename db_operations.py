import os
import sqlite3
import mysql.connector
from contextlib import contextmanager
from sql_statements import *

DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_NAME = os.getenv("DB_NAME", "sync_tasks.db")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
DB_PATH = os.getenv("DB_PATH")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "sync_tasks")

class DatabaseManager:
    def __init__(self, db_type, db_path):
        self.db_type = db_type
        self.db_path = db_path
        self.connection = self.create_connection()
        self.create_tables_if_not_exists()

    def create_connection(self):
        if self.db_type == "mysql":
            import mysql.connector
            return mysql.connector.connect(
                host="your_host",
                user="your_user",
                password="your_password",
                database=self.db_path
            )
        else:
            import sqlite3
            return sqlite3.connect(self.db_path)

    def create_tables_if_not_exists(self):
        self.execute_query(get_create_tasks_table_sql(self.db_type))
        self.execute_query(get_create_projects_table_sql(self.db_type))
        self.execute_query(get_create_sync_tokens_table_sql(self.db_type))
        self.initialize_sync_tokens()

    def initialize_sync_tokens(self):
        # 初始化同步令牌
        initial_tokens = [("items", "*"), ("projects", "*")]
        for resource_type, sync_token in initial_tokens:
            if not self.fetch_one("SELECT sync_token FROM sync_tokens WHERE resource_type = ?", (resource_type,)):
                self.execute_query("INSERT INTO sync_tokens (resource_type, sync_token) VALUES (?, ?)", (resource_type, sync_token))

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        cursor.close()

    def fetch_one(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    # 同步令牌的方法
    def get_sync_token(self, resource_type):
        query = get_sync_token_query(self.db_type)
        result = self.fetch_one(query, (resource_type,))
        return result[0] if result else "*"

    def update_sync_token(self, resource_type, sync_token):
        query = get_update_sync_token_query(self.db_type)
        self.execute_query(query, (resource_type, sync_token))

    # 插入和更新任务的方法
    def insert_task(self, task):
        query = get_insert_task_query(self.db_type)
        self.execute_query(query, task)

    def update_task(self, task):
        query = get_update_task_query(self.db_type)
        self.execute_query(query, task)

    # 插入和更新项目的方法
    def insert_project(self, project):
        query = get_insert_project_query(self.db_type)
        self.execute_query(query, project)

    def update_project(self, project):
        query = get_update_project_query(self.db_type)
        self.execute_query(query, project)
        
    def close_connection(self):
        self.connection.close()