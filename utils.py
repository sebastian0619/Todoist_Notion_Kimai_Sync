import logger
from datetime import datetime
import time
import uuid
def map_priority(priority):
    priority_map = {
        4: "🚨HIGH",
        3: "🧀 Medium",
        2: "🧊 Low",
        1: "🔴 None"
    }
    return priority_map.get(priority)

def map_priority_reverse(priority_name):
    priority_map = {
        "🚨HIGH": 4,
        "🧀 Medium": 3,
        "🧊 Low": 2,
        "🔴 None": 1
    }
    return priority_map.get(priority_name)

def retry_on_failure(func):
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    raise
    return wrapper

def notion_task_property(content):
    return {
        "Task": {
            "title": [
                {
                    "text": {
                        "content": content
                    }
                }
            ]
        }
    }

def notion_priority_property(priority):
    return {
        "Priority": {
            "select": {
                "name": map_priority(priority)
            }
        }
    }

def notion_due_date_property(due_date):
    return {
        "Due": {
            "date": {
                "start": due_date,
                "time_zone": "Asia/Shanghai"
            }
        }
    }

def notion_todoist_id_property(todoist_id):
    return {
        "TodoistID": {
            "rich_text": [
                {
                    "text": {
                        "content": str(todoist_id)
                    }
                }
            ]
        }
    }

def notion_url_property(todoist_id):
    return {
        "URL": {
            "url": f"https://todoist.com/showTask?id={todoist_id}"
        }
    }

def notion_checked_property(checked):
    return {
        "Status": {
            "checkbox": checked
        }
    }
def notion_trash_property(deleted):
    return {
        "archived": deleted
    }
def notion_description_property(description):
    return {
        "Description": {
            "rich_text": [
                {
                    "text": {
                        "content": description
                    }
                }
            ]
        }
    }
def is_valid_isoformat(date_string):
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False
def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test