from utils import map_priority, map_priority_reverse
from db_operations import DatabaseManager
from api_client import NotionClient, TodoistSyncClient
from sql_statements import get_insert_project_query, get_insert_task_query
import uuid
import os
from datetime import datetime
DB_TYPE = os.getenv("DB_TYPE") # 或 "mysql"
DB_PATH = os.getenv("DB_PATH")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
Todoist_TOKEN = os.getenv("Todoist_TOKEN")
db_manager = DatabaseManager(DB_TYPE, DB_PATH)
notion_client = NotionClient(NOTION_TOKEN)
todoist_client = TodoistSyncClient(Todoist_TOKEN, DB_TYPE, DB_PATH)

def get_notion_task_properties(task, db_manager):
    # 获取或创建Notion项目ID
    notion_project_id = None
    if 'project_id' in task and (task['project_id'] or task['project_id'] == ""):
        # 从数据库中查找对应的Notion项目ID
        notion_project_id = db_manager.fetch_one("SELECT notion_id FROM projects WHERE todoist_id = ?", (task["project_id"],))
        if notion_project_id:
            notion_project_id = notion_project_id[0]

    properties = {
        "Task": {
            "title": [
                {
                    "text": {
                        "content": task.get("content", "")
                    }
                }
            ]
        },
        "Priority": {
            "select": {
                "name": map_priority(task.get("priority", 1))  # 默认优先级为1
            }
        },
        "Project": {
            "relation": [
                {"id": notion_project_id}
            ] if notion_project_id else []
        },
        "TodoistID": {
            "rich_text": [
                {
                    "text": {
                        "content": task.get("id", "")
                    }
                }
            ]
        },
        "Recurring": {
            "checkbox": task.get("due", {}).get('is_recurring', False) if task.get("due") else False
        },
        "URL": {
            "url": f"https://todoist.com/showTask?id={task.get('id', '')}"
        }
    }

    # 仅在存在 description 时添加 Description 属性
    if task.get("description"):
        properties["Description"] = {
            "rich_text": [
                {
                    "text": {
                        "content": task["description"]
                    }
                }
            ]
        }

    # 仅在存在 due 日期时添加 Due 属性
    if task.get("due") and task["due"].get("date"):
        properties["Due"] = {
            "date": {
                "start": task["due"]["date"]
            }
        }

    return properties


def get_notion_project_properties(project):
    return {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": project.get("name")
                    }
                }
            ]
        },
        "TodoistID": {
            "rich_text": [
                {
                    "text": {
                        "content": project.get("id")
                    }
                }
            ]
        },
        "TodoistURL": {
            "url": f"https://todoist.com/showProject?id={project.get('id')}"
        }
    }
def get_todoist_project_id(task):
    todoist_project_id = None
    if task["Project"]["relation"] and task["Project"]["relation"][0]["id"]:
        todoist_project_id_result = db_manager.fetch_one("SELECT todoist_id FROM projects WHERE notion_id = ?", (task["Project"]["relation"][0]["id"],))
        if todoist_project_id_result:
            todoist_project_id = todoist_project_id_result[0]
        else:
            project_name = notion_client.get_page(task['Project']['relation'][0]['id'])['Name']['title'][0]['text']['content']
            todoist_projects = todoist_client.get_project("*")
            for project in todoist_projects:
                if project['name'] == project_name:
                    todoist_project_id = project['id']
                    break
            else:
                notion_project_id = task["Project"]["relation"][0]["id"]
                notion_project = notion_client.get_page(notion_project_id)
                notion_project_data = get_notion_project_properties(notion_project)
                temp_id = str(uuid.uuid4())
                todoist_project_data = todoist_client.create_project(notion_project_data, temp_id)
                temp_id_mapping = todoist_project_data.get("temp_id_mapping", {})
                todoist_project_id = temp_id_mapping.get(temp_id)
                current_date = datetime.now()
                insert_project_query = get_insert_project_query(DB_TYPE)
                notion_url = f"https://www.notion.so/{notion_project_id}"
                todoist_url = f"https://todoist.com/showProject?id={todoist_project_id}"
                notion_client.update_page(notion_project_id, {"TodoistID": {"rich_text": [{"text": {"content": todoist_project_id}}]}})
                db_manager.execute_query(insert_project_query, (todoist_project_id, project_name, todoist_project_id, notion_project_id, todoist_url, notion_url, current_date, current_date, notion_project['created_time'], notion_project['last_edited_time']))
    return todoist_project_id

def get_todoist_task_id(task):
    todoist_task_id = None
    if task['TodoistID']['rich_text'] and task['TodoistID']['rich_text'][0]['text']['content']:
        todoist_task_id_result = db_manager.fetch_one("SELECT todoist_id FROM tasks WHERE notion_id = ?", (task["TodoistID"]["rich_text"][0]["text"]["content"],))
    else:
        todoist_task_id_result = db_manager.fetch_one("SELECT todoist_id FROM tasks WHERE notion_id = ?", (task["TodoistID"]["rich_text"][0]["text"]["content"],))
        if todoist_task_id_result:
            todoist_task_id = todoist_task_id_result[0]
        else:
            task_name = task['Task']['title'][0]['text']['content']
            todoist_tasks = todoist_client.get_task("*")
            for todoist_task in todoist_tasks:
                if todoist_task['name'] == task_name:
                    todoist_task_id = todoist_task['id']
                    break
            else:
                temp_id = str(uuid.uuid4())
                todoist_project_id = notion_client.get_project(task['Project']['relation'][0]['id'])['Name']['rich_text'][0]['text']['content']
                task_data = get_todoist_task_properties(task)
                notion_task_id = task['id']
                todoist_task_data = todoist_client.create_task_with_note(task_data, temp_id)
                note_id = todoist_task_data['note_id']
                task_id = todoist_task_data['task_id']
                new_sync_token = todoist_task_data['new_sync_token']
                temp_id_mapping = todoist_task_data.get("temp_id_mapping", {})
                todoist_task_data = todoist_client.get_single_task(task_id)['items'][0]
            todoist_task_id = temp_id_mapping.get(temp_id)
            current_date = datetime.now()
            insert_task_query = get_insert_task_query(DB_TYPE)
            notion_url = f"https://www.notion.so/{notion_task_id}"
            todoist_url = f"https://todoist.com/showTask?id={todoist_task_id}"
            notion_client.update_page(task['id'], {
                "TodoistID": {"rich_text": [{"text": {"content": todoist_project_id}}]},
                "URL": {"url": todoist_url}
            })
            db_manager.execute_query (insert_task_query, (todoist_task_id, task_name, task['due']['date']['start'], map_priority_reverse(task['Status']['select']['name']), todoist_project_id, notion_client.get_page(task['Project']['relation']['id'])['properties']['Name'], task['added_at'], note_id, todoist_url, task['Status']['checkbox'], task['description'], task['due']['is_recurring'], current_date, task['archived'], task['id'], notion_url, todoist_task_data['add_at'], task['last_edited_at'], task['created_time'], task['last_edited_time']))
            todoist_task_id = todoist_task_data['id']

def get_todoist_task_properties(task):

    todoist_project_id = get_todoist_project_id(task)
    todoist_task_id = get_todoist_task_id(task)

                
    return {
        "content": task["Task"]["title"][0]["text"]["content"],
        "description": task["Description"]["rich_text"][0]["text"]["content"] if task["Description"]["rich_text"] else "",
        "due_date": task["Due"]["date"]["start"] if task["Due"] and "date" in task["Due"] else None,
        "priority": task["Priority"]["select"]["name"],
        "project_id": todoist_project_id,
        "is_recurring": task["Recurring"]["checkbox"],
        "id": todoist_task_id,
        "url": f"https://todoist.com/showTask?id={todoist_task_id}"
    }

def get_todoist_project_properties(project):
    return {
        "name": project["Name"]["title"][0]["text"]["content"],
        "id": project["TodoistID"]["rich_text"][0]["text"]["content"],
        "url": project["TodoistURL"]["url"]
    }