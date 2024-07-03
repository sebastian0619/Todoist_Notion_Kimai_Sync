def get_create_tasks_table_sql(db_type):
    if db_type == "mysql":
        return """
        CREATE TABLE IF NOT EXISTS tasks (
            todoist_id INT PRIMARY KEY,
            content TEXT,
            due DATE,
            priority INT,
            project_id INT,
            project_name TEXT,
            added_at DATETIME,
            note_id TEXT,
            note TEXT,
            checked BOOLEAN,
            description TEXT,
            recurring TEXT,
            date_updated DATETIME,
            deleted BOOLEAN,
            notion_id TEXT,
            notion_url TEXT,
            todoist_created DATETIME,
            todoist_modified DATETIME,
            notion_created DATETIME,
            notion_modified DATETIME
        );
        """
    else:
        return """
        CREATE TABLE IF NOT EXISTS tasks (
            todoist_id INTEGER PRIMARY KEY,
            content TEXT,
            due DATE,
            priority INTEGER,
            project_id INTEGER,
            project_name TEXT,
            added_at DATETIME,
            note_id TEXT,
            note TEXT,
            checked BOOLEAN,
            description TEXT,
            recurring TEXT,
            date_updated DATETIME,
            deleted BOOLEAN,
            notion_id TEXT,
            notion_url TEXT,
            todoist_created DATETIME,
            todoist_modified DATETIME,
            notion_created DATETIME,
            notion_modified DATETIME
        );
        """

def get_create_projects_table_sql(db_type):
    if db_type == "mysql":
        return """
        CREATE TABLE IF NOT EXISTS projects (
            id INT PRIMARY KEY,
            name TEXT,
            todoist_id INT,
            notion_id TEXT,
            todoist_url TEXT,
            notion_url TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            notion_created DATETIME,
            notion_modified DATETIME,
            deleted BOOLEAN,
            archived BOOLEAN
        );
        """
    else:
        return """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT,
            todoist_id INTEGER,
            notion_id TEXT,
            todoist_url TEXT,
            notion_url TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            notion_created DATETIME,
            notion_modified DATETIME,
            deleted BOOLEAN,
            archived BOOLEAN
        );
        """

def get_create_sync_tokens_table_sql(db_type):
    if db_type == "mysql":
        return """
        CREATE TABLE IF NOT EXISTS sync_tokens (
            resource_type VARCHAR(255) PRIMARY KEY,
            sync_token VARCHAR(255)
        );
        """
    else:
        return """
        CREATE TABLE IF NOT EXISTS sync_tokens (
            resource_type TEXT PRIMARY KEY,
            sync_token TEXT
        );
        """

def get_create_count_table_sql(db_type):
    if db_type == "mysql":
        return """
        CREATE TABLE IF NOT EXISTS count (
            type TEXT PRIMARY KEY,
            count INT
        );
        """
    else:
        return """
        CREATE TABLE IF NOT EXISTS count (
            type TEXT PRIMARY KEY,
            count INTEGER
        );
        """

def get_insert_task_query(db_type):
    if db_type == "mysql":
        return """
        INSERT INTO tasks (todoist_id, content, due, priority, project_id, project_name, added_at, note_id, note, checked, description, recurring, date_updated, deleted, notion_id, notion_url, todoist_created, todoist_modified, notion_created, notion_modified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
    else:
        return """
        INSERT INTO tasks (todoist_id, content, due, priority, project_id, project_name, added_at, note_id, note, checked, description, recurring, date_updated, deleted, notion_id, notion_url, todoist_created, todoist_modified, notion_created, notion_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

def get_update_task_query(db_type):
    if db_type == "mysql":
        return """
        UPDATE tasks SET content = %s, due = %s, priority = %s, project_id = %s, project_name = %s, note_id = %s, note = %s, checked = %s, description = %s, recurring = %s, date_updated = %s, deleted = %s, notion_id = %s, notion_url = %s, todoist_created = %s, todoist_modified = %s, notion_created = %s, notion_modified = %s
        WHERE todoist_id = %s
        """
    else:
        return """
        UPDATE tasks SET content = ?, due = ?, priority = ?, project_id = ?, project_name = ?, note_id = ?, note = ?, checked = ?, description = ?, recurring = ?, date_updated = ?, deleted = ?, notion_id = ?, notion_url = ?, todoist_created = ?, todoist_modified = ?, notion_created = ?, notion_modified = ?
        WHERE todoist_id = ?
        """

def get_insert_project_query(db_type):
    if db_type == "mysql":
        return """
        INSERT INTO projects (id, name, todoist_id, notion_id, todoist_url, notion_url, created_at, updated_at, notion_created, notion_modified, deleted, archived)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
    else:
        return """
        INSERT INTO projects (id, name, todoist_id, notion_id, todoist_url, notion_url, created_at, updated_at, notion_created, notion_modified, deleted, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

def get_update_project_query(db_type):
    if db_type == "mysql":
        return """
        UPDATE projects SET name = %s, todoist_id = %s, notion_id = %s, todoist_url = %s, notion_url = %s, created_at = %s, updated_at = %s, notion_created = %s, notion_modified = %s, deleted = %s, archived = %s
        WHERE id = %s
        """
    else:
        return """
        UPDATE projects SET name = ?, todoist_id = ?, notion_id = ?, todoist_url = ?, notion_url = ?, created_at = ?, updated_at = ?, notion_created = ?, notion_modified = ?, deleted = ?, archived = ?
        WHERE id = ?
        """

def get_sync_token_query(db_type):
    if db_type == "mysql":
        return """
        SELECT sync_token FROM sync_tokens WHERE resource_type = %s
        """
    else:
        return """
        SELECT sync_token FROM sync_tokens WHERE resource_type = ?
        """

def get_update_sync_token_query(db_type):
    if db_type == "mysql":
        return """
        REPLACE INTO sync_tokens (resource_type, sync_token) VALUES (%s, %s)
        """
    else:
        return """
        REPLACE INTO sync_tokens (resource_type, sync_token) VALUES (?, ?)
        """

def get_update_count_query(db_type):
    if db_type == "mysql":
        return """
        UPDATE count SET count = %s WHERE type = %s
        """
    else:
        return """
        UPDATE count SET count = ? WHERE type = ?
        """