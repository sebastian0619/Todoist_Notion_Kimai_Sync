from api_client import TodoistSyncClient, NotionClient
from logger import logger
from db_operations import DatabaseManager
from sql_statements import get_insert_project_query, get_update_project_query
from utils import iso_to_timestamp, notion_project_property
import uuid
import os
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime, timezone, timedelta

log_file = 'log.json'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
formatter = jsonlogger.JsonFormatter()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
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
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": project.get('name')
                        }
                    }
                ]
            },
            "TodoistID": {
                "rich_text": [
                    {
                        "text": {
                            "content": project.get('id')
                        }
                    }
                ]
            }
    }
    new_project = notion_client.create_page(NOTION_PROJECT_DATABASE_ID, project_data)
    project_id = new_project['id']
    logger.debug(f"Notion project created: {project_id}")
    return new_project



def sync_todoist_projects_to_notion():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN,DB_TYPE, DB_PATH)
    notion_client = NotionClient(NOTION_TOKEN)
    
    project_sync_token = db_manager.get_sync_token("projects")
    projects_data = todoist_client.get_projects(project_sync_token)
    logger.debug(f"Projects data: {projects_data['projects']}")
#    if projects_data['projects']:
#        project_last_modified = max(projects_data['projects'], key=lambda x: x['updated_at'])['updated_at']
#        logger.info(f"Project last modified: {project_last_modified}")
#    else:
#        project_last_modified = None
    db_project_count = db_manager.fetch_one("SELECT * From projects WHERE deleted IS FALSE")
    db_project_count = db_project_count[0] if db_project_count else 0
    todoist_projects = projects_data["projects"]
    new_project_sync_token = projects_data['sync_token']
    current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    project_db_last_modified = db_manager.fetch_one("SELECT MAX(updated_at) FROM projects WHERE deleted IS FALSE")
    project_db_last_modified = project_db_last_modified[0] if project_db_last_modified else None
    if project_db_last_modified == None:
        logger.info(f"Database not set, start initial syncing")
        for project in todoist_projects:
                logger.info(f"Project: {project}")
                if not isinstance(project, dict):
                    logger.error(f"Expected project to be a dictionary but got {type(project)}: {project}")
                    continue

                logger.info(f"Processing project: {project.get('name')}")  # 打印调试信息
                project_id = project.get('id')
                project_name = project.get("name")
                update_notion_project = create_notion_project(notion_client, project)
                notion_url = update_notion_project.get('url')
                todoist_url = f"https://todoist.com/showProject?id={project_id}"
                insert_project_query = get_insert_project_query(db_manager.db_type)
                db_manager.execute_query(insert_project_query, (None, project_name, project_id, update_notion_project['id'], todoist_url, notion_url, current_date, current_date, update_notion_project['created_time'], update_notion_project['created_time'], project.get('is_deleted'),project.get('is_archived')))
                logger.info(f"Project synced to Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {update_notion_project['id']})")
        db_manager.update_sync_token("projects", new_project_sync_token)
    else:
        for project in todoist_projects:
            logger.debug(f"Project: {project}")
            if not isinstance(project, dict):
                logger.error(f"Expected project to be a dictionary but got {type(project)}: {project}")
                continue
            logger.info(f"Processing project: {project.get('name')}")  # 打印调试信息
            project_id = project.get('id')
            project_name = project.get("name")
            todoist_url = f"https://todoist.com/showProject?id={project_id}"
            if not all([project_id, project_name]):
                logger.error(f"Project data missing required fields: {project}")
                continue

            notion_project_id = db_manager.fetch_one("SELECT notion_id FROM projects WHERE todoist_id = ?", (project_id,))
            notion_project_id = notion_project_id[0] if notion_project_id else None
            current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

            if notion_project_id:
                logger.info(f"Notion project exists, updating...")
                update_notion_project = notion_client.update_project(notion_project_id, notion_project_property(project), project.get('is_deleted'))
                update_project_query = get_update_project_query(db_manager.db_type)
                db_manager.execute_query(update_project_query, (None, project_name, project_id, notion_project_id, todoist_url, update_notion_project['url'], None, None, update_notion_project['created_time'], update_notion_project['last_edited_time'], project.get('is_deleted'),project.get('is_archived')))
                logger.info(f"Project updated in Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {notion_project_id})")
                db_manager.update_sync_token("projects", new_project_sync_token)
            else:
                update_notion_project = create_notion_project(notion_client, project)
                notion_url = update_notion_project.get('url')
                todoist_url = f"https://todoist.com/showProject?id={project_id}"
                insert_project_query = get_insert_project_query(db_manager.db_type)
                db_manager.execute_query(insert_project_query, (None, project_name, project_id, update_notion_project['id'], todoist_url, notion_url, current_date, current_date, update_notion_project['created_time'], update_notion_project['created_time'], project.get('is_deleted'),project.get('is_archived')))
                logger.info(f"Project synced to Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {update_notion_project['id']})")
                db_manager.update_sync_token("projects", new_project_sync_token)

        db_manager.close_connection()

    

def sync_notion_projects_to_todoist():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    notion_client = NotionClient(NOTION_TOKEN)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN,DB_TYPE, DB_PATH)
    filter = {
            "and":[{
                "property": "Archived",
                "checkbox": {
                    "equals": False
                }
            }]
        
    }
    notion_projects = notion_client.get_projects(filter)
    logger.debug(f"Notion projects: {notion_projects}")
    current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    valid_projects = [project for project in notion_projects.get("results", []) if project.get('last_edited_time') is not None]
    logger.debug(f"Valid projects: {valid_projects}")
<<<<<<< HEAD
=======
    notion_projects = notion_projects['results']
>>>>>>> 46c0da2ae8b35eb56b9a6d9e7142b1b2d8dd520c
    if valid_projects:
        project_last_modified = max(valid_projects, key=lambda x: x['last_edited_time'])['last_edited_time']
    else:
        project_last_modified = None  # 或者设置为一个合理的默认值
    project_db_last_modified = db_manager.fetch_one("SELECT MAX(updated_at) FROM projects WHERE deleted IS FALSE")
    project_db_last_modified = project_db_last_modified[0] if project_db_last_modified else None

    if project_db_last_modified == None:
        logger.info(f"Database not set, start initial syncing")
        for project in notion_projects:
            properties = project['properties']
            todoist_id = next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None)
            project_name = properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', '')
            project_created = project.get('created_time')
            project_modified = project.get('last_edited_time')
            temp_id = str(uuid.uuid4())
            todoist_project_data = {
                "name": properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                "id": todoist_id,

            }
            temp_id_mapping = todoist_client.create_project(todoist_project_data, temp_id)['temp_id_mapping']
            logger.debug(f"temp_id_mapping: {temp_id_mapping}")
            todoist_project_id = temp_id_mapping[temp_id]
            logger.info(f"Project created in todoist: {project_name} (Todoist ID: {todoist_project_id}), Notion ID:{project['id']}")
            notion_url = project.get('url')
            todoist_url = f"https://todoist.com/showProject?id={todoist_project_id}"
            insert_project_query = get_insert_project_query(db_manager.db_type)
            db_manager.execute_query(insert_project_query, (
                    None, project_name, project.get('id'), project.get('id'), todoist_url, notion_url, 
                    project.get('created_time'), current_date, project.get('created_time'), project.get('last_edited_time'), project.get('archived'),properties.get('Archived', {}).get('checkbox')
            ))
            logger.info(f"Project synced to Notion: {project_name} (Todoist ID: {todoist_project_id}, Notion ID: {project.get('id')})")
    else:
        logger.info(f"Comparing DB modified time: {project_db_last_modified} and Notion Project DB modified time: {project_last_modified}")
        if iso_to_timestamp(str(project_last_modified)) > iso_to_timestamp(str(project_db_last_modified)):
            logger.info(f"Notion Project modified time {project_last_modified} is later than DB modified time {project_db_last_modified}, time difference: {abs(iso_to_timestamp(str(project_last_modified)) - iso_to_timestamp(str(project_db_last_modified)))}")
            for project in valid_projects:
                logger.debug(f"Project: {project}")
                properties = project.get('properties', {})
                todoist_id = next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None)
                project_name = properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', '')
                project_created = project.get('created_time')
                project_modified = project.get('last_edited_time')
                todoist_url = f"https://todoist.com/showProject?id={todoist_id}"
                db_todoist_id = db_manager.fetch_one("SELECT todoist_id FROM projects WHERE notion_id = ?", (project['id'],))
                todoist_project_data = {
                    "name": properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                    "id": todoist_id,

                }
                modified = db_manager.fetch_one("SELECT updated_at FROM projects WHERE todoist_id = ?", (todoist_id,))
                if todoist_id and db_todoist_id:
                    if iso_to_timestamp(str(project_modified)) > iso_to_timestamp(str(modified[0])):
                        logger.info(f"Comparing project_modified: {project_modified} and modified: {modified[0]}")
                        logger.info(f"Notion project modified time {datetime.fromtimestamp(iso_to_timestamp(str(project_modified)))} is later than database modified time {datetime.fromtimestamp(iso_to_timestamp(str(modified[0])))}, time difference: {abs(iso_to_timestamp(str(project_modified)) - iso_to_timestamp(str(modified[0])))}")
                        todoist_client.update_project(todoist_id, todoist_project_data)
                        logger.info(f"Project updated in Todoist: {project_name} (Todoist ID: {todoist_id}, Notion ID: {project['id']})")
                        update_project_query = get_update_project_query(db_manager.db_type)
                        db_manager.execute_query(update_project_query, (None, project_name, todoist_id, project['id'], todoist_url, project.get("url"), project_modified, None, None, project_modified, project.get('archived'),properties.get('Archived', {}).get('checkbox')))
                elif not db_todoist_id:
                    logger.info(f"Project not in todoist, creating...")
                    temp_id = str(uuid.uuid4())
                    temp_id_mapping = todoist_client.create_project(todoist_project_data, temp_id)['temp_id_mapping']
                    logger.debug(f"temp_id_mapping: {temp_id_mapping}")
                    todoist_project_id = temp_id_mapping[temp_id]
                    logger.info(f"Project created in todoist: {project_name} (Todoist ID: {todoist_project_id}), Notion ID:{project['id']}")
                    notion_url = project.get('url')
                    todoist_url = f"https://todoist.com/showProject?id={todoist_project_id}"
                    insert_project_query = get_insert_project_query(db_manager.db_type)
                    db_manager.execute_query(insert_project_query, (
                            None, project_name, todoist_project_id, project.get('id'), todoist_url, notion_url, 
                            project.get('created_time'), current_date, project.get('created_time'), project.get('last_edited_time'), project.get('archived'),properties.get('Archived', {}).get('checkbox')
                    ))
                    logger.info(f"Project synced to Todoist: {project_name} (Todoist ID: {todoist_project_id}, Notion ID: {project.get('id')})")
        else:
            logger.info(f"Notion Project modified time {project_last_modified} is earlier than DB modified time {project_db_last_modified}, time difference: {abs(iso_to_timestamp(str(project_last_modified)) - iso_to_timestamp(str(project_db_last_modified)))} seconds")

    db_manager.close_connection()
    


if __name__ == "__main__":
    logger.info("Starting synchronization from Notion to Todoist...")
    sync_notion_projects_to_todoist()

    logger.info("Completed synchronization from Notion to Todoist.")
               
    
    logger.info("Starting synchronization from Todoist to Notion...")

    sync_todoist_projects_to_notion()

    logger.info("Completed synchronization from Todoist to Notion.")
    
