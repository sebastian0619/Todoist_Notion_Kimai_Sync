# Todoist_Notion_Kimai_Sync Usage Guide

## Introduction

The [Todoist_Notion_Kimai_Sync](file:///Users/sebastian/Documents/GitHub/Todoist_Notion_Kimai_Sync/README.md#1%2C3-1%2C3) project is designed to synchronize tasks and projects between Todoist, Notion, and Kimai. This guide will walk you through the setup and usage of the synchronization tool.

## Prerequisites

Before you begin, ensure you have the following:

1. **Python 3.9 or higher** installed on your machine.
2. **Todoist API Token**.
3. **Notion API Key**.
4. **Kimai API Token** (if using Kimai).
5. **Database**: SQLite or MySQL.

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Todoist_Notion_Kimai_Sync.git
cd Todoist_Notion_Kimai_Sync
```

### 2. Create and Configure the `.env` File

Create a `.env` file in the root directory of the project and add your API keys and database configuration. You can use the `env.example` file as a template.

```bash
cp env.example .env
```

Edit the `.env` file with your credentials:

```env
NOTION_TOKEN=YOUR_NOTION_API_KEY
NOTION_TASK_DATABASE_ID=YOUR_NOTION_TASK_DATABASE_ID
NOTION_PROJECT_DATABASE_ID=YOUR_NOTION_PROJECT_DATABASE_ID
TODOIST_TOKEN=YOUR_TODOIST_API_TOKEN
DB_TYPE=sqlite or mysql
DB_PATH=sync_tasks.db or your_mysql_host
DB_NAME=sync_tasks.db or your_mysql_database
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=sync_tasks
```

### 3. Install Dependencies

Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

## Deployment

You can deploy the application either locally or using Docker.

### Local Deployment

Run the main script directly with Python:

```bash
python main.py
```

### Docker Deployment

Build and run the Docker container:

```bash
docker build -t todoist_notion_kimai_sync .
docker run -d --env-file .env todoist_notion_kimai_sync
```

## Synchronization

The synchronization process involves syncing projects and tasks between Todoist and Notion. The main synchronization functions are defined in the `project_sync.py` and `task_sync.py` files.

### Project Synchronization

Projects are synchronized in both directions between Todoist and Notion.

#### Sync Todoist Projects to Notion

This function fetches projects from Todoist and updates or creates corresponding projects in Notion.


```1:81:project_sync.py
from api_client import TodoistSyncClient, NotionClient
from logger import logger
from db_operations import DatabaseManager
from sql_statements import get_insert_project_query, get_update_project_query
from notion_properties import get_notion_project_properties
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
```


#### Sync Notion Projects to Todoist

This function fetches projects from Notion and updates or creates corresponding projects in Todoist.


```1:94:project_sync.py
from api_client import TodoistSyncClient, NotionClient
from logger import logger
from db_operations import DatabaseManager
from sql_statements import get_insert_project_query, get_update_project_query
from notion_properties import get_notion_project_properties
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
```


### Task Synchronization

Tasks are synchronized in both directions between Todoist and Notion.

#### Sync Todoist Tasks to Notion

This function fetches tasks from Todoist and updates or creates corresponding tasks in Notion.


```1:64:task_sync.py
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
```


#### Sync Notion Tasks to Todoist

This function fetches tasks from Notion and updates or creates corresponding tasks in Todoist.


```1:92:task_sync.py
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
```


## Logging

The application logs synchronization activities to a JSON log file (`log.json`). This can be useful for debugging and monitoring the synchronization process.


```1:18:project_sync.py
from api_client import TodoistSyncClient, NotionClient
from logger import logger
from db_operations import DatabaseManager
from sql_statements import get_insert_project_query, get_update_project_query
from notion_properties import get_notion_project_properties
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
```


## Conclusion

This guide provides a basic overview of setting up and using the `Todoist_Notion_Kimai_Sync` project. For more detailed information, refer to the code and comments within the project files. If you encounter any issues, please check the logs and ensure all API keys and database configurations are correct.

