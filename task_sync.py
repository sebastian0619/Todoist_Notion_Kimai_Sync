from api_client import TodoistSyncClient, NotionClient, TodoistTask, NotionTask
from db_operations import DatabaseManager
from logger import logger
from sql_statements import get_insert_task_query, get_update_task_query
from utils import map_priority_reverse, map_priority, iso_to_timestamp,iso_to_naive,retry_on_failure, notion_trash_property,notion_task_property, notion_checked_property,notion_priority_property, notion_due_date_property, notion_todoist_id_property, notion_url_property, notion_description_property, is_valid_isoformat, is_valid_uuid
from project_sync import create_notion_project
from datetime import datetime, timezone, timedelta
import uuid
import os
import time
import json
import logging
from pythonjsonlogger import jsonlogger
from notion_client import Client
from dateutil.parser import parse


log_file = 'log.json'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
formatter = jsonlogger.JsonFormatter()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

NOTION_TASK_DATABASE_ID = os.getenv("NOTION_TASK_DATABASE_ID")
NOTION_PROJECT_DATABASE_ID = os.getenv("NOTION_PROJECT_DATABASE_ID")

TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TYPE = os.getenv("DB_TYPE")
DB_PATH = os.getenv("DB_PATH")
db_manager = DatabaseManager(DB_TYPE, DB_PATH)
notion = Client(auth=NOTION_TOKEN)



def create_notion_task(notion_client, todoist_task):
    try:
        notion_task = NotionTask.from_todoist_task(todoist_task)
        
        task_property = notion_task_property(notion_task.name) if notion_task.name else {}
        priority_property = (notion_priority_property(todoist_task.priority)) if notion_task.priority else {}
        logger.info(f"priority is {map_priority(todoist_task.priority)}")
        due_date_property = notion_due_date_property(notion_task.due_date) if notion_task.due_date else {}
        todoist_id_property = notion_todoist_id_property(notion_task.todoist_id) if notion_task.todoist_id else {}
        url_property = notion_url_property(notion_task.todoist_id) if notion_task.todoist_id else {}
        description = notion_description_property(notion_task.description) if notion_task.description else {}
        checked = notion_checked_property(notion_task.checked)

        # 合并属性部分
        properties = {}
        properties.update(task_property)
        properties.update(priority_property)
        properties.update(due_date_property)
        properties.update(todoist_id_property)
        properties.update(url_property)
        properties.update(description)
        properties.update(checked)
        # 检查 properties 是否为空
        if not properties:
            raise Exception("Properties are empty, cannot create Notion task.")

        logger.info(f"Creating Notion task with properties: {json.dumps(properties, ensure_ascii=False)}")
        new_task = notion_client.create_page(NOTION_TASK_DATABASE_ID, properties)
        
        # 检查返回结果是否包含错误
        if new_task.get('object') == 'error':
            raise Exception(f"Notion API error: {new_task.get('message')}")
        
        logger.info(f"Notion task created: {new_task}")
        return new_task
    except Exception as e:
        logger.error(f"Failed to create Notion task: {e}")
        raise

def update_notion_task(notion_client, todoist_task, page_id):
    try:
        # 构建各个属性部分
        task_property = notion_task_property(todoist_task.content) if todoist_task.content else {}
        priority_property = notion_priority_property(todoist_task.priority) if todoist_task.priority else {}
        logger.info(f"priority is {map_priority(todoist_task.priority)}")
        due_date_property = notion_due_date_property(todoist_task.due_date) if todoist_task.due_date else {}
        todoist_id_property = notion_todoist_id_property(todoist_task.id) if todoist_task.id else {}
        url_property = notion_url_property(todoist_task.id) if todoist_task.id else {}
        description = notion_description_property(todoist_task.description) if todoist_task.description else {}
        checked = notion_checked_property(todoist_task.checked) if todoist_task.checked else {}

        # 合并属性部分
        properties = {}
        properties.update(task_property)
        properties.update(priority_property)
        properties.update(due_date_property)
        properties.update(todoist_id_property)
        properties.update(url_property)
        properties.update(description)
        properties.update(checked)
            # 检查 properties 是否为空
        if not properties:
            raise Exception("Properties are empty, cannot update Notion task.")

        logger.info(f"Updating Notion task with properties: {properties}")
        new_task = notion_client.update_task(page_id, properties, todoist_task.deleted)
            
            # 检查返回结果是否包含错误
        if new_task.get('object') == 'error':
            raise Exception(f"Notion API error: {new_task.get('message')}")
            
        logger.info(f"Notion task updated: {new_task}")
        return new_task
    except Exception as e:
        logger.error(f"Failed to update Notion task: {e}")
        raise
def create_todoist_task_with_note(todoist_client, temp_id, todoist_task, notion_url):
    #rich_text = todoist_task.get('Description', {}).get('rich_text', [])
    #description = rich_text[0].get('text', {}).get('content', '') if rich_text else ''
    #priority_select = todoist_task.get('Priority', {}).get('select')
    #task_data = {
       #     "content": todoist_task.get('Task', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
       #     "due_date": todoist_task.get('Due', {}).get('date', {}).get('start'),
       #     "priority": priority_select.get('name') if priority_select else None,
       #     "project_id": todoist_task.get('Project ID', {}).get('select', {}).get('id'),
         #   "todoist_id": next((prop['text']['content'] for prop in todoist_task.get('TodoistID', {}).get('rich_text', [])), None),
      #      "description": description
      #      }
    task_data = todoist_task
    
    new_sync_token, new_item_id, new_note_id = todoist_client.create_task_with_note(task_data, temp_id, notion_url)
    new_task = todoist_client.get_single_task(new_item_id)['item']
    logger.debug(f"Created todoist task {new_task}")
    return new_task, new_sync_token, new_item_id, new_note_id


def sync_todoist_to_notion():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN, DB_TYPE, DB_PATH)
    notion_client = NotionClient(NOTION_TOKEN)

    task_sync_token = db_manager.get_sync_token("items")
    logger.info(f"Task sync token: {task_sync_token}")
    tasks_data = todoist_client.get_tasks(task_sync_token)
    logger.info(f"Tasks data from Todoist: {tasks_data}")
    new_task_sync_token = tasks_data['sync_token']
    logger.info(f"New task sync token: {new_task_sync_token}")
    todoist_tasks = tasks_data["items"]
    logger.debug(f"Todoist tasks: {todoist_tasks}")



    for task in todoist_tasks:
        if not isinstance(task, dict):
            logger.error(f"Expected task to be a dictionary but got {type(task)}: {task}")
            continue

        logger.debug(f"Processing task: {task}")  # Print debug info

        # 获取与任务相关的笔记
        note_id, note_content = db_manager.fetch_one("SELECT note_id, note FROM tasks WHERE todoist_id = ?", (task.get("id"),)) or (None, None)
        due_date = task.get("due", {}).get("date") if task.get("due") else None
        if due_date:
            #due_date = datetime.fromisoformat(due_date)
            logger.debug(f"due_date: {due_date}")
        todoist_task = TodoistTask(
            id=task.get("id"),
            content=task.get("content"),
            due_date=due_date,
            priority=task.get("priority") if task.get("priority") else None,
            project_id=task.get("project_id"),
            project_name=db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (task.get("project_id"),))[0] or None,
            added_at=task.get("added_at"),
            note_id=note_id,
            note=note_content,
            checked=task.get("checked"),
            description=task.get("description"),
            recurring=task.get("due", {}).get("is_recurring") if task.get("due") else None,
            date_updated=task.get("updated_at"),
            deleted=task.get("is_deleted"),
            notion_id=None,  # Fetch notion id if needed
            notion_url=None
        )
        # 获取 notion_task_id 并提取第一个元素
        modified_date = db_manager.fetch_one("SELECT date_updated FROM tasks WHERE todoist_id = ?", (todoist_task.id,))
        modified_date = modified_date[0] if modified_date else None
        notion_task_id_tuple = db_manager.fetch_one("SELECT notion_id FROM tasks WHERE todoist_id = ?", (todoist_task.id,))
        notion_task_id = notion_task_id_tuple[0] if notion_task_id_tuple else None
        logger.debug(f"Fetched notion_task_id: {notion_task_id}")


        if todoist_task.date_updated and modified_date and todoist_task.deleted != True:
            if todoist_task.date_updated > modified_date:
                logger.info(f"对比结果: Todoist任务的更新时间 {todoist_task.date_updated} > 数据库中的更新时间 {modified_date}")
            if notion_task_id and is_valid_uuid(notion_task_id):
                logger.info(f"Valid Notion task ID found: {notion_task_id}")
                notion_task = notion_client.get_page(notion_task_id)
                notion_modified = notion_task.get('last_edited_time')
                logger.info(f"Fetched notion_task: {notion_task.get('properties')['Task']['title'][0]['text']['content']}")
                logger.debug(f"Fetched modified date: {notion_modified}, comparing with todoist_task.date_updated: {todoist_task.date_updated}")
            logger.info("Updating existing Notion task...")
            logger.debug(f"Proposed notion properties: id={todoist_task.id}, content={todoist_task.content}, due_date={todoist_task.due_date}, priority={todoist_task.priority}, project_id={todoist_task.project_id}, added_at={todoist_task.added_at}, date_updated={todoist_task.date_updated}, description={todoist_task.description}")
            new_task_in_todoist = update_notion_task(notion_client, todoist_task, notion_task_id)
            logger.info(f"Updated task in Notion: {new_task_in_todoist}")
            update_task_query = get_update_task_query(db_manager.db_type)
            db_manager.execute_query(update_task_query, (
                todoist_task.content, todoist_task.due_date, todoist_task.priority, todoist_task.project_id, todoist_task.project_name, note_id, new_task_in_todoist.get('url'), 
                todoist_task.checked, todoist_task.description, todoist_task.recurring, datetime.now(), todoist_task.deleted, 
                notion_task.get('id'), new_task_in_todoist.get("url"), todoist_task.added_at, todoist_task.date_updated, notion_task.get('created_time'), notion_modified, todoist_task.id
            ))
            logger.info(f"Task updated in database: {todoist_task.content} (Todoist ID: {todoist_task.id}, Notion ID: {notion_task.get('id')})")
        elif todoist_task.deleted == True:
            notion_client.delete_page(notion_task_id)
            logger.info(f"Deleting Notion Page with ID: {notion_task_id}")

        else:    
            temp_id = str(uuid.uuid4())
            logger.info("Cannot find matching notion task in database or in Notion, creating new Notion task...")
            try:
                logger.debug(f"Proposed notion properties: id={todoist_task.id}, content={task.get('content')}, due_date={todoist_task.due_date}, priority={todoist_task.priority}, project_id={todoist_task.project_id}, added_at={todoist_task.added_at}, date_updated={todoist_task.date_updated}")
                notion_task = create_notion_task(notion_client, todoist_task)
            except Exception:
                logger.error("Failed to create Notion task")
            notion_url = notion_task.get('url')
            todoist_url = f"https://todoist.com/showTask?id={todoist_task.id}"
            current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
            logger.info(f"Adding note with Notion url: {notion_url}, Todoist ID: {todoist_task.id}, Temp ID: {temp_id}, ")
            note = todoist_client.add_note(todoist_task.id, notion_url, temp_id)
            logger.info(f"Added note: {note}")
            temp_id_mapping = note.get("temp_id_mapping", {})
            note_id = temp_id_mapping.get(temp_id)
            insert_task_query = get_insert_task_query(db_manager.db_type)
            project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (todoist_task.project_id,))
            logger.debug(f"Fetched project_name: {project_name}")
            due_date = todoist_task.due_date
            is_recurring = todoist_task.recurring
            db_manager.execute_query(insert_task_query, (
                todoist_task.id, todoist_task.content, todoist_task.due_date, todoist_task.priority, todoist_task.project_id, todoist_task.project_name, todoist_task.added_at, note_id, notion_url, 
                todoist_task.checked, todoist_task.description, todoist_task.recurring, current_date, todoist_task.deleted, 
                notion_task.get('id'), notion_url, todoist_task.added_at, todoist_task.date_updated, notion_task.get('created_time'), notion_task.get('last_edited_time')
                    ))
            logger.info(f"Task synced to Notion: {notion_task.get} (Todoist ID: {todoist_task.id}, Notion ID: {notion_task.get('id')})")

    db_manager.update_sync_token("items", new_task_sync_token)
    db_manager.close_connection()


def sync_notion_to_todoist():
    db_manager = DatabaseManager(DB_TYPE, DB_PATH)
    notion_client = NotionClient(NOTION_TOKEN)
    todoist_client = TodoistSyncClient(TODOIST_TOKEN, DB_TYPE, DB_PATH)
    task_sync_token = db_manager.get_sync_token("items")
    logger.debug(f"Task sync token: {task_sync_token}")
    notion_tasks = notion_client.get_tasks({})
    valid_tasks = [project for project in notion_tasks.get("results", []) if project.get('last_edited_time') is not None]
    logger.debug(f"Valid tasks: {valid_tasks}")
    if valid_tasks:
        task_last_modified = max(valid_tasks, key=lambda x: x['last_edited_time'])['last_edited_time']
    else:
        task_last_modified = None  # 或者设置为一个合理的默认值
    task_db_last_modified = db_manager.fetch_one("SELECT MAX(date_updated) FROM tasks WHERE deleted IS FALSE")
    task_db_last_modified = task_db_last_modified[0] if task_db_last_modified else None
    
    if task_db_last_modified == None:
        logger.info(f"Database not set, start initial syncing")
        for task in notion_tasks.get("results", []):
                if not isinstance(task, dict):
                    logger.error(f"Expected task to be a dictionary but got {type(task)}: {task}")
                    continue
                current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
                logger.debug(f"Processing task: {task}")  # Print debug info
                properties = task.get('properties', {})
                due_date = properties.get('Due',{})
                due_date_value = ''
                if due_date:
                    date_field = due_date.get('date')
                    if date_field:
                        due_date_value = date_field.get('start')
                        due_date_value = iso_to_naive(due_date_value)
                        logger.debug(f"due_date_value: {due_date_value}")
                rich_text = properties.get('Description', {}).get('rich_text', [])
                description = rich_text[0].get('text', {}).get('content', '') if rich_text else ''
                priority_select = properties.get('Priority', {}).get('select')
                todoist_task_data = {
                    "content": properties.get('Task', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                    "due": {
                        "date":due_date_value,
                        "is_recurring": properties.get('Recurring', {}).get('checkbox'),
                        "timezone": "Asia/Shanghai"
                                        },
                    "priority": map_priority_reverse(priority_select.get('name')) if priority_select else None,
                    "project_id": properties.get('Project ID', {}).get('select', {}).get('id'),
                    "todoist_id": next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None),
                    "description": description,
                    "checked": properties.get('Status', {}).get('checkbox'),
                    "is_deleted": task.get('archived'),
                }
                temp_id = str(uuid.uuid4())
                new_task_in_todoist, new_task_sync_token, item_id, note_id = create_todoist_task_with_note(todoist_client, temp_id, todoist_task_data, task.get('url'))
                todoist_url = f"https://todoist.com/showTask?id={item_id}"
                logger.debug(f"Todoist task created: {item_id}")
                logger.debug(f"Todoist note created: {note_id}")
                logger.debug(f"Updating notion with TodoistID: {item_id}")
                proposed_properties = notion_todoist_id_property(item_id)
                update_notion_task = notion_client.update_page(notion_task_id, proposed_properties, new_task_in_todoist.get('is_deleted'))
                logger.info(f"Updated notion with TodoistID: {item_id}")
                current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
                notion_url = task.get('url')

                insert_task_query = get_insert_task_query(db_manager.db_type)
                project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (new_task_in_todoist.get('project_id'),))[0]
                #  if not project_name:
                #       logger.info("Project not found, running project_sync...")
                #     project_sync()
                #     project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (new_task_in_todoist.get('project_id'),))
                logger.debug(f"Fetched project_name: {project_name}")
                db_manager.execute_query(insert_task_query, (
                        item_id, task_name, due_date_value, new_task_in_todoist.get("priority"), 
                        new_task_in_todoist.get("project_id"), project_name, current_date, note_id, 
                        todoist_url, new_task_in_todoist['checked'], todoist_task_data['description'], 
                        todoist_task_data['due']['is_recurring'], current_date, new_task_in_todoist.get('is_deleted'), 
                        task.get('id'), notion_url, new_task_in_todoist.get('added_at'), new_task_in_todoist.get('updated_at'), task['created_time'], task['last_edited_time']
                ))
                db_manager.update_sync_token('items', new_task_sync_token)
                logger.info(f"Task synced to Todoist and recorded in database: {task_name} (Todoist ID: {item_id}, Notion ID: {task['id']})")
    else:
        logger.info(f"Comparing DB modified time: {task_db_last_modified} and Notion Task DB modified time: {task_last_modified}")
        if iso_to_timestamp(str(task_last_modified)) > iso_to_timestamp(str(task_db_last_modified)):
            logger.info(f"Notion Task modified time {task_last_modified} is later than DB modified time {task_db_last_modified}, time difference: {abs(iso_to_timestamp(str(task_last_modified)) - iso_to_timestamp(str(task_db_last_modified)))}")
            for task in valid_tasks.get("results", []):
                if not isinstance(task, dict):
                    logger.error(f"Expected task to be a dictionary but got {type(task)}: {task}")
                    continue
                current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
                logger.debug(f"Processing task: {task}")  # Print debug info
                properties = task.get('properties', {})
                due_date = properties.get('Due',{})
                due_date_value = ''
                if due_date:
                    date_field = due_date.get('date')
                    if date_field:
                        due_date_value = date_field.get('start')
                        due_date_value = iso_to_naive(due_date_value)
                        logger.debug(f"due_date_value: {due_date_value}")
                rich_text = properties.get('Description', {}).get('rich_text', [])
                description = rich_text[0].get('text', {}).get('content', '') if rich_text else ''
                priority_select = properties.get('Priority', {}).get('select')
                todoist_task_data = {
                    "content": properties.get('Task', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                    "due": {
                        "date":due_date_value,
                        "is_recurring": properties.get('Recurring', {}).get('checkbox'),
                        "timezone": "Asia/Shanghai"
                                        },
                    "priority": map_priority_reverse(priority_select.get('name')) if priority_select else None,
                    "project_id": properties.get('Project ID', {}).get('select', {}).get('id'),
                    "todoist_id": next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None),
                    "description": description,
                    "checked": properties.get('Status', {}).get('checkbox'),
                    "is_deleted": task.get('archived'),
                }
                logger.debug(f"Notion due date: {due_date_value}")
                logger.debug(f"Todoist task properties: {todoist_task_data}")
                #update
                
                logger.info(f"Updated task in Todoist: {todoist_task_data['content']}")
                todoist_id = todoist_task_data["todoist_id"]
                task_name = todoist_task_data["content"]
                task_created = task.get('created_time')
                task_modified = task.get('last_edited_time')
                if not all([task_name, task_created, task_modified]):
                    logger.error(f"Task data missing required fields: {task}")
                    continue

            # Check if the project exists in Todoist
                notion_task_id = task.get('id')
                todoist_id = db_manager.fetch_one("SELECT todoist_id FROM tasks WHERE notion_id = ?", (notion_task_id,))
                todoist_id = todoist_id[0] if todoist_id else None
                logger.info(f"Todoist task ID found: {todoist_id}")

                if not todoist_id:
                    logger.info(f"No matching Todoist task found for notion_id: {notion_task_id}")
                    temp_id = str(uuid.uuid4())
                    new_task_in_todoist, new_task_sync_token, item_id, note_id = create_todoist_task_with_note(todoist_client, temp_id, todoist_task_data, task.get('url'))
                    logger.info(f"is deleted {new_task_in_todoist.get('is_deleted')}")
                    logger.info(f"Todoist Task created: {new_task_in_todoist}")
                    todoist_url = f"https://todoist.com/showTask?id={item_id}"
                    logger.info(f"Todoist task created: {item_id}")
                    logger.info(f"Todoist note created: {note_id}")
                    logger.info(f"Updating notion with TodoistID: {item_id}")
                    proposed_properties = notion_todoist_id_property(item_id)
                    update_notion_task = notion_client.update_page(notion_task_id, proposed_properties, new_task_in_todoist.get('is_deleted'))
                    logger.info(f"Updated notion with TodoistID: {item_id}")
                    current_date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
                    notion_url = task.get('url')

                    insert_task_query = get_insert_task_query(db_manager.db_type)
                    project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (new_task_in_todoist.get('project_id'),))[0]
                #  if not project_name:
                #       logger.info("Project not found, running project_sync...")
                #     project_sync()
                #     project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (new_task_in_todoist.get('project_id'),))
                    logger.info(f"Fetched project_name: {project_name}")
                    db_manager.execute_query(insert_task_query, (
                        item_id, task_name, due_date_value, new_task_in_todoist.get("priority"), 
                        new_task_in_todoist.get("project_id"), project_name, current_date, note_id, 
                        todoist_url, new_task_in_todoist['checked'], todoist_task_data['description'], 
                        todoist_task_data['due']['is_recurring'], current_date, new_task_in_todoist.get('is_deleted'), 
                        task.get('id'), notion_url, new_task_in_todoist.get('added_at'), new_task_in_todoist.get('updated_at'), task['created_time'], task['last_edited_time']
                    ))
                    db_manager.update_sync_token('items', new_task_sync_token)
                    logger.info(f"Task synced to Todoist and recorded in database: {task_name} (Todoist ID: {item_id}, Notion ID: {task['id']})")
                else:
                    notion_modified = task.get('last_edited_time')
                    notion_modified = iso_to_timestamp(str(notion_modified))
                    logger.info(f"notion_modified: {notion_modified}")
                    modified = db_manager.fetch_one("SELECT date_updated FROM tasks WHERE todoist_id = ?", (todoist_id,))
                    modified = iso_to_timestamp(modified[0]) if modified else None
                    if notion_modified and modified:
                        logger.info(f"Fetched notion update time {datetime.fromtimestamp(notion_modified)}, comparing with database update date: {datetime.fromtimestamp(modified)}")
                    if notion_modified > modified:
                        logger.info(f"Notion task modified time {datetime.fromtimestamp(notion_modified)} is later than database modified time {datetime.fromtimestamp(modified)}, time difference: {abs(notion_modified - modified)}")
                        task_data_update = {
                                "content": properties.get('Task', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
                                "due": {
                                    "datetime": due_date_value,
                                    "is_recurring": properties.get('Recurring', {}).get('checkbox'),
                                    "timezone": "Asia/Shanghai"
                                },
                                "priority": map_priority_reverse(priority_select.get('name')) if priority_select else None,
                                "project_id": properties.get('Project ID', {}).get('select', {}).get('id'),
                                "todoist_id": next((prop['text']['content'] for prop in properties.get('TodoistID', {}).get('rich_text', [])), None),
                                "description": description,
                                "checked": properties.get('Status', {}).get('checkbox'),
                                "is_deleted": task.get('archived'),
                            }
                        logger.info(f"Updating task in Todoist: {todoist_task_data}")
                        new_task_in_todoist = todoist_client.update_task(todoist_id, todoist_task_data)
                        logger.info(f"Updated task in Todoist: {new_task_in_todoist}")
                        new_sync_token = new_task_in_todoist.get('sync_token')
                        logger.info(f"New sync token: {new_sync_token}")
                        task_data = todoist_client.get_single_task(todoist_id)
                        logger.info(f"Fetched single task data from Todoist: {task_data}")
                        notion_url = f"https://www.notion.so/{task['id']}"
                        todoist_url = f"https://todoist.com/showTask?id={todoist_id}"
                        project_name = db_manager.fetch_one("SELECT name FROM projects WHERE todoist_id = ?", (todoist_task_data.get("project_id"),))[0]
                        logger.info(f"Fetched project name: {project_name}")
                        update_task_query = get_update_task_query(db_manager.db_type)
                        db_manager.execute_query(update_task_query, (
                                new_task_in_todoist.get('content'), due_date_value, todoist_task_data.get('priority'),
                                todoist_task_data.get('project_id'), project_name, None, None, todoist_task_data['checked'], todoist_task_data['description'],
                                properties.get('Recurring', {}).get('checkbox'), current_date, todoist_task_data.get('is_deleted'),
                                task['id'], notion_url, None, task_data.get('updated_at'), task['created_time'], task['last_edited_time'], todoist_id
                            ))
                        logger.info(f"Task updated in database: {task_name} (Todoist ID: {todoist_id}, Notion ID: {task['id']})")
                        db_manager.update_sync_token("items", new_sync_token)
                        logger.info(f"Sync token updated for items: {new_sync_token}")
                    else:
                        logger.info(f"No update needed for task: {task_name} (Todoist ID: {todoist_id}, Notion ID: {task['id']})")
    
    db_manager.close_connection()

if __name__ == "__main__":
    logger.info("Starting synchronization from Todoist to Notion...")

    sync_todoist_to_notion()

    logger.info("Completed synchronization from Todoist to Notion.")
    
    logger.info("Starting synchronization from Notion to Todoist...")
    sync_notion_to_todoist()

    logger.info("Completed synchronization from Notion to Todoist.")

