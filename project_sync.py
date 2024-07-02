from api_client import TodoistSyncClient, NotionClient
from logger import logger
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

    project_sync_token = db_manager.get_sync_token("project")
    projects_data = todoist_client.get_projects(project_sync_token)
    new_project_sync_token = projects_data['sync_token']
    todoist_projects = projects_data["projects"]

    # 更新数据库中的同步令牌
    db_manager.update_sync_token("project", new_project_sync_token)

    for project in todoist_projects:
        if not isinstance(project, dict):
            logger.error(f"Expected project to be a dictionary but got {type(project)}: {project}")
            continue

        logger.debug(f"Processing project: {project.get('name')}")  # 打印调试信息
        project_id = project.get("id")
        project_name = project.get("name")
        project_created = project.get("created_at")
        project_modified = project.get("updated_at")
        if not all([project_id, project_name, project_created, project_modified]):
            logger.error(f"Project data missing required fields: {project}")
            continue

        notion_project_id = db_manager.fetch_one("SELECT notion_id FROM projects WHERE todoist_id = ?", (project_id,))
        notion_project_id = notion_project_id[0] if notion_project_id else None

        if notion_project_id:
            notion_project = notion_client.get_page(notion_project_id)
            notion_modified = notion_project['last_edited_time']
            modified = db_manager.fetch_one("SELECT updated_at FROM projects WHERE todoist_id = ?", (project_id,))

            if project_modified > modified[0]:
                notion_client.update_project(notion_project_id, get_notion_project_properties(project))
                logger.info(f"Project updated in Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {notion_project_id})")
        else:
            notion_project_id = create_notion_project(notion_client, project)
            notion_url = f"https://www.notion.so/{notion_project_id}"
            todoist_url = f"https://todoist.com/showProject?id={project_id}"
            insert_project_query = get_insert_project_query(db_manager.db_type)
            db_manager.execute_query(insert_project_query, (project_id, project_name, project_id, notion_project_id, todoist_url, notion_url, project_created, project_modified, notion_project['created_time'], notion_modified))
            logger.info(f"Project synced to Notion: {project_name} (Todoist ID: {project_id}, Notion ID: {notion_project_id})")

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
        icon_data = properties.get('icon', {})
        icon_emoji = icon_data.get('emoji', '') if icon_data else ''
        name_text = properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', '')
        project_name = icon_emoji + name_text  # 确保字符串相加
        project_created = project.get('created_time')
        project_modified = project.get('last_edited_time')
        if not all([project_name, project_created, project_modified]):
            logger.error(f"Project data missing required fields: {project}")
            continue

        # 检查项目是否已存在于Todoist
        if todoist_id:
            notion_task_id = db_manager.fetch_one("SELECT notion_id FROM projects WHERE todoist_id = ?", (todoist_id,))
            if notion_task_id:
                notion_task_id = notion_task_id[0]
                notion_task = notion_client.get_page(notion_task_id)
                notion_modified = notion_task['last_edited_time']
                modified = db_manager.fetch_one("SELECT updated_at FROM projects WHERE todoist_id = ?", (todoist_id,))
                if notion_modified > modified[0]:
                    notion_client.update_task(notion_task_id, get_notion_project_properties(project))
                    logger.info(f"Project updated in Todoist: {project_name} (Todoist ID: {todoist_id}, Notion ID: {project['id']})")
            else:
                todoist_project_data = {
                    "name": project_name
                }
                todoist_project_from_notion = todoist_client.create_project(todoist_project_data)
                logger.info(f"Project created in todoist: {project_name} (Todoist ID: {todoist_project_from_notion['id']}), Notion ID:{project['id']}")

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
