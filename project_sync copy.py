from api_client import TodoistSyncClient, NotionClient
from logger import logger
from datetime import datetime
from utils import iso_to_timestamp
import uuid
from db_operations import DatabaseManager
from sql_statements import get_insert_project_query, get_update_project_query
from notion_properties import get_notion_project_properties

import os
NOTION_PROJECT_DATABASE_ID = os.getenv("NOTION_PROJECT_DATABASE_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")

DB_TYPE = os.getenv("DB_TYPE")
DB_PATH = os.getenv("DB_PATH")

class TodoistProject:
    def __init__(self, id, name, created_at, updated_at, deleted, notion_id, notion_url):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted = deleted
        self.notion_id = notion_id
        self.notion_url = notion_url

def create_notion_project(notion_client, project):
    project_data = {
        "parent": {"database_id": NOTION_PROJECT_DATABASE_ID},
        "properties": get_notion_project_properties(project)
    }
    new_project = notion_client.create_project(project_data)
    project_id = new_project['id']
    logger.debug(f"Notion project created: {project_id}")
    return project_id

def sync_todoist_projects_to_notion():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN)
    notion_client = NotionClient(NOTION_TOKEN)

    project_sync_token = db_manager.get_sync_token("projects")
    projects_data = todoist_client.get_projects(project_sync_token)
    new_project_sync_token = projects_data['sync_token']
    todoist_projects = projects_data["projects"]
    # 更新数据库中的同步令牌
    

    for project in todoist_projects:
        if not isinstance(project, dict):
            logger.error(f"Expected project to be a dictionary but got {type(project)}: {project}")
            continue

        logger.info(f"Processing project: {project.get('name')}")  # 打印调试信息
        project_id = project.get('id')
        project_name = project.get("name")
        if not all([project_id, project_name]):
            logger.error(f"Project data missing required fields: {project}")
            continue

        notion_project_id = db_manager.fetch_one("SELECT notion_id FROM projects WHERE todoist_id = ?", (project_id,))
        notion_project_id = notion_project_id[0] if notion_project_id else None
        current_date = datetime.now().strftime("%Y-%m-%d")

        if notion_project_id:
            update_notion_project = notion_client.update_project(notion_project_id, get_notion_project_properties(project))
            update_project_query = get_update_project_query(db_manager.db_type)
            db_manager.execute_query(update_project_query, (None, project_name, project_id, notion_project_id, todoist_url, update_notion_project['url'], None, None, update_notion_project['created_time'], update_notion_project['last_edited_time']))
            logger.info(f"Project updated in Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {notion_project_id})")
            db_manager.update_sync_token("projects", new_project_sync_token)
        else:
            update_notion_project = create_notion_project(notion_client, project)
            notion_url = update_notion_project.get('url')
            todoist_url = f"https://todoist.com/showProject?id={project_id}"
            insert_project_query = get_insert_project_query(db_manager.db_type)
            db_manager.execute_query(insert_project_query, (None, project_name, project_id, update_notion_project['id'], todoist_url, notion_url, current_date, current_date, update_notion_project['created_time'], update_notion_project['created_time']))
            logger.info(f"Project synced to Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {notion_project_id})")
            db_manager.update_sync_token("projects", new_project_sync_token)
    db_manager.close_connection()

def sync_notion_projects_to_todoist():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    notion_client = NotionClient(NOTION_TOKEN)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN)

    notion_projects = notion_client.get_projects({})
    logger.debug(f"Notion projects: {notion_projects}")  # 打印调试信息

    for project in notion_projects.get("results", []):
        if not isinstance(project, dict):
            logger.error(f"Expected project to be a dictionary but got {type(project)}: {project}")
            continue

        properties = project.get('properties', {})
        todoist_id = next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None)
        db_todoist_id = db_manager.fetch_one("SELECT todoist_id FROM projects WHERE notion_id = ?", (project['id'],))
        project_name = properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', '')
        project_created = project.get('created_time')
        project_modified = project.get('last_edited_time')
        modified = db_manager.fetch_one("SELECT updated_at FROM projects WHERE todoist_id = ?", (todoist_id,))
        if not all([project_name, project_created, project_modified]):
            logger.error(f"Project data missing required fields: {project}")
            continue
        todoist_project_data = {
            "name": properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
            "id": todoist_id,
        }
        # 检查项目是否已存在于Todoist
        if todoist_id and db_todoist_id:
            logger.info(f"Comparing project_modified: {project_modified} and modified: {modified}")
            if iso_to_timestamp(str(project_modified)) > iso_to_timestamp(str(modified[0])):
                logger.info(f"Notion project modified time {datetime.fromtimestamp(iso_to_timestamp(str(project_modified)))} is later than database modified time {datetime.fromtimestamp(iso_to_timestamp(str(modified[0])))}, time difference: {abs(iso_to_timestamp(str(project_modified)) - iso_to_timestamp(str(modified[0])))}")
                todoist_client.update_project(todoist_id, todoist_project_data)
                logger.info(f"Project updated in Todoist: {project_name} (Todoist ID: {todoist_id}, Notion ID: {project['id']})")
                update_project_query = get_update_project_query(db_manager.db_type)
                db_manager.execute_query(update_project_query, (None, project_name, todoist_id, project['id'], todoist_url, notion_url, project_modified, None, None, project_modified))
            else:
                temp_id = str(uuid.uuid4())
                temp_id_mapping = todoist_client.create_project(todoist_project_data, temp_id)['temp_id_mapping']
                todoist_project_id = temp_id_mapping['id']
                logger.info(f"Project created in todoist: {project_name} (Todoist ID: {todoist_project_id}), Notion ID:{project['id']}")

                # 在数据库中记录项目
                insert_project_query = get_insert_project_query(db_manager.db_type)
                todoist_url = f"https://todoist.com/showProject?id={todoist_project_from_notion['id']}"
                notion_url = f"https://www.notion.so/{project['id']}"
                db_manager.execute_query(insert_project_query, (todoist_project_from_notion['id'], project_name, project['id'], project['id'], todoist_url, notion_url, project_created, project_modified, project['created_time'], project_modified))
                logger.info(f"Project synced to Todoist and recorded in database: {project_name} (Todoist ID: {todoist_project_from_notion['id']}, Notion ID: {project['id']}")

    db_manager.close_connection()

if __name__ == "__main__":
    logger.info("Starting project synchronization from Todoist to Notion...")
    sync_todoist_projects_to_notion()
    logger.info("Completed project synchronization from Todoist to Notion.")

    logger.info("Starting project synchronization from Notion to Todoist...")
    sync_notion_projects_to_todoist()
    logger.info("Completed project synchronization from Notion to Todoist.")
