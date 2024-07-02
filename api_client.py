import os
import requests
import uuid
import requests
from db_operations import DatabaseManager
from dotenv import load_dotenv
from typing import Any, Dict, List, Tuple
import logging
from notion_client import Client
import logger

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE")
DB_PATH = os.getenv("DB_PATH")
db_manager = DatabaseManager(DB_TYPE, DB_PATH)

class TodoistSyncClient:
    def __init__(self, token: str, DB_TYPE: str, DB_PATH: str):
        self.token = token
        self.base_url = "https://api.todoist.com/sync/v9"
        self.db_manager = DatabaseManager(DB_TYPE, DB_PATH)

    def sync_api(self, resource_types: str, sync_token: str, commands: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/sync"
        params = {
            "sync_token": sync_token,
            "resource_types": resource_types
        }
        if commands:
            params["commands"] = commands
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 打印调试信息
        logging.info(f"Sending request to {url} with params: {params} and headers: {headers}")
        
        response = requests.post(url, json=params, headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
            raise
        result = response.json()
        return result

    def get_tasks(self, sync_token: str ) -> Dict[str, Any]:
        result = self.sync_api('["items"]', sync_token)
        return result


    def get_single_task(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/items/get"
        data = {
            "item_id": task_id,
            "all_data": False
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        logging.info(f"result: {result}")
        return result
    def get_projects(self, sync_token: str) -> Dict[str, Any]:
        result = self.sync_api('["projects"]', sync_token)
        return result
    def get_single_project(self, sync_token: str, project_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/sync"
        params = {
            "project_id": project_id,
            "all_data": False
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(url, json=params, headers=headers)
        result = response.json()
        return result
    def create_task(self, task_data: Dict[str, Any], temp_id: str) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("items")
        resource_types = '["items"]'
        commands = [{
            "type": "item_add",
            "temp_id": temp_id,
            "uuid": str(uuid.uuid4()),
            "args": task_data
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("items", result["sync_token"])
        return result
    
    def create_task_with_note(self, task_data: Dict[str, Any], temp_id: str, content: str) -> Tuple[str, str, str]:
        sync_token = self.db_manager.get_sync_token("items")
        resource_types = '["items"]'
        commands = [
            {
                "type": "item_add",
                "temp_id": temp_id,
                "args": task_data,
                "uuid": str(uuid.uuid4())
            },
            {
                "type": "note_add",
                "temp_id": str(uuid.uuid4()),
                "args": {
                    "item_id": temp_id,
                    "content": content
                },
                "uuid": str(uuid.uuid4())
            }
        ]
        result = self.sync_api(resource_types, sync_token, commands)
        sync_token = result["sync_token"]
        temp_id_mapping = result.get("temp_id_mapping", {})
        item_id = temp_id_mapping.get(temp_id)
        note_id = None
        # 找到不是 item_id 的另一个 ID，假设它是 note_id
        for temp_id_key, real_id_value in temp_id_mapping.items():
            if temp_id_key != temp_id:
                note_id = real_id_value
                break
        self.db_manager.update_sync_token("items", result["sync_token"])
        print(f"create_task_with_note() 返回: {(sync_token, item_id, note_id)}")
        return sync_token, item_id, note_id

    def create_project(self, project_data: Dict[str, Any],temp_id) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("projects")
        resource_types = '["projects"]'
        commands = [{
            "type": "project_add",
            "temp_id": temp_id,
            "uuid": str(uuid.uuid4()),
            "args": project_data
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("projects", result["sync_token"])
        print(f"create_project() 返回: {result}")
        return result

    def update_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("items")
        resource_types = '["items"]'
        commands = [{
            "type": "item_update",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id,
                **task_data
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("items", result["sync_token"])
        print(f"update_task() 返回: {(result)}")
        return result

    def update_project(self, project_id: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("projects")
        resource_types = '["projects"]'
        commands = [{
            "type": "project_update",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": project_id,
                **project_data
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("projects", result["sync_token"])
        print(f"update_project() 返回类型: {type(result)}")
        return result

    def check_task(self, task_id: str) -> List[Dict[str, Any]]:
        sync_token = self.db_manager.get_sync_token("items")
        resource_types = '["items"]'
        commands = [{
            "type": "item_complete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("items", result["sync_token"])
        print(f"check_task() 返回类型: {type(result['items'])}")
        return result["items"]

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("items")
        resource_types = '["items"]'
        commands = [{
            "type": "item_delete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("items", result["sync_token"])
        print(f"delete_task() 返回类型: {type(result)}")
        return result
    def add_note(self, task_id: str, content: str, temp_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/sync"
        commands = [{
            "type": "note_add",
            "uuid": str(uuid.uuid4()),
            "temp_id": temp_id,
            "args": {
                "item_id": task_id,
                "content": content
            }
        }]
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(url, json={"commands": commands}, headers=headers)
        result = response.json()
        print(f"add_note() 返回: {(result)}")
        return result

    def update_note(self, note_id: str, content: str) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("notes")
        resource_types = '["notes"]'
        commands = [{
            "type": "note_update",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": note_id,
                "content": content
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("notes", result["sync_token"])
        print(f"update_note() 返回类型: {type(result)}")
        return result

    def delete_note(self, note_id: str) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("notes")
        resource_types = '["notes"]'
        commands = [{
            "type": "note_delete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": note_id
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("notes", result["sync_token"])
        print(f"delete_note() 返回类���: {type(result)}")
        return result

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        sync_token = self.db_manager.get_sync_token("projects")
        resource_types = '["projects"]'
        commands = [{
            "type": "project_delete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": project_id
            }
        }]
        result = self.sync_api(resource_types, sync_token, commands)
        self.db_manager.update_sync_token("projects", result["sync_token"])
        print(f"delete_project() 返回类型: {type(result)}")
        return result



class NotionClient:
    def __init__(self, token: str):
        self.token = token
        self.client = Client(auth=self.token)
        self.task_database_id = os.getenv("NOTION_TASK_DATABASE_ID")
        self.project_database_id = os.getenv("NOTION_PROJECT_DATABASE_ID")

    def create_page(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        result = self.client.pages.create(**data)
        print(f"create_page() 返回: {result}")
        return result
    
    def update_page(self, page_id: str, properties: Dict[str, Any], archived) -> Dict[str, Any]:
        data = {
            "page_id": page_id,
            "properties": properties,
            "archived": archived
        }
        result = self.client.pages.update(**data)
        print(f"update_page() 返回类型: {type(result)}")
        return result
    
    def delete_page(self, page_id: str) -> Dict[str, Any]:
        data = {
            "page_id": page_id,
            "archived": True
        }
        result = self.client.pages.update(**data)
        print(f"delete_page() 返回: {result}")
        return result

    def get_page(self, page_id: str) -> Dict[str, Any]:
        result = self.client.pages.retrieve(page_id=page_id)
        print(f"get_page() 返回: {result}")
        return result

    def create_task(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_page(self.task_database_id, properties)

    def create_project(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_page(self.project_database_id, properties)

    def update_task(self, page_id: str, properties: Dict[str, Any], archived) -> Dict[str, Any]:
        return self.update_page(page_id, properties, archived)

    def update_project(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_page(page_id, properties)

    def task_complete(self, task_id: str) -> Dict[str, Any]:
        data = {
            "page_id": task_id,
            "properties": {
                "Status": {
                    "checkbox": True
                }
            }
        }
        result = self.client.pages.update(**data)
        print(f"task_complete() 返回类型: {type(result)}")
        return result

    def delete_page(self, page_id: str) -> bool:
        data = {
            "page_id": page_id,
            "archived": True
        }
        result = self.client.pages.update(**data)
        print(f"delete_page() 返回: {result}")
        return result['archived']
    def restore_task(self, task_id: str) -> Dict[str, Any]:
        data = {
            "page_id": task_id,
            "archived": False
        }
        result = self.client.pages.update(**data)
        print(f"restore_task() 返回: {result}")
        return result
    def get_projects(self, filter_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        data = {
            "database_id": self.project_database_id,
        }
        if filter_properties:
            data["filter"] = filter_properties
        result = self.client.databases.query(**data)
        print(f"get_projects() 返回: {result}")
        return result
    
    def get_tasks(self, filter_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        data = {
            "database_id": self.task_database_id,
        }
        if filter_properties:
            data["filter"] = filter_properties
        result = self.client.databases.query(**data)
        print(f"get_tasks() 返回: {result}")
        return result

    def delete_task(self, task_id: str) -> bool:
        return self.delete_page(task_id)

    def delete_project(self, project_id: str) -> bool:
        return self.delete_page(project_id)

class TodoistTask:
    def __init__(self, id, content, due_date, priority, project_id, project_name, added_at, note_id, note, checked, description, recurring, date_updated, deleted, notion_id, notion_url):
        self.id = id
        self.content = content
        self.due_date = due_date
        self.priority = priority
        self.project_id = project_id
        self.project_name = project_name
        self.added_at = added_at
        self.note_id = note_id
        self.note = note
        self.checked = checked
        self.description = description
        self.recurring = recurring
        self.date_updated = date_updated
        self.deleted = deleted
        self.notion_id = notion_id
        self.notion_url = notion_url

class NotionTask:
    @staticmethod
    def from_todoist_task(todoist_task):
        return NotionTask(
            name=todoist_task.content,
            description=todoist_task.description,
            due_date=todoist_task.due_date,
            priority=todoist_task.priority,
            project_id=todoist_task.project_id,
            todoist_id=todoist_task.id,
            checked=todoist_task.checked,
            deleted=todoist_task.deleted
        )

    def __init__(self, name, description, due_date, priority, project_id, todoist_id, checked,deleted):
        self.name = name
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.project_id = project_id
        self.todoist_id = todoist_id
        self.checked = checked
        self.deleted = deleted

class KimaiClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://kimai.kingschats.com/api"
        self.headers = {"Authorization": f"Bearer {self.token}"}