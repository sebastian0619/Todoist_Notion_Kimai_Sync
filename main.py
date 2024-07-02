import time
from threading import Thread
from logger import logger
from project_sync import sync_todoist_projects_to_notion, sync_notion_projects_to_todoist
from task_sync import sync_todoist_to_notion, sync_notion_to_todoist

def project_sync():
    while True:
        try:
            logger.info("Starting project synchronization from Todoist to Notion...")
            sync_todoist_projects_to_notion()
            logger.info("Completed project synchronization from Todoist to Notion.")
            
            logger.info("Starting project synchronization from Notion to Todoist...")
            sync_notion_projects_to_todoist()
            logger.info("Completed project synchronization from Notion to Todoist.")
        except Exception as e:
            logger.error(f"Error during project synchronization: {e}")
        
        time.sleep(15)

def task_sync():
    while True:
        try:
            logger.info("Starting task synchronization from Todoist to Notion...")
            if not sync_todoist_to_notion():
                logger.info("No new tasks to sync from Todoist to Notion.")
            else:
                logger.info("Completed task synchronization from Todoist to Notion.")
            
            logger.info("Starting task synchronization from Notion to Todoist...")
            if not sync_notion_to_todoist():
                logger.info("No new tasks to sync from Notion to Todoist.")
            else:
                logger.info("Completed task synchronization from Notion to Todoist.")
        except Exception as e:
            logger.error(f"Error during task synchronization: {e}")
        
        time.sleep(15)
        time.sleep(15)

if __name__ == "__main__":
    project_thread = Thread(target=project_sync)
    task_thread = Thread(target=task_sync)
    
    project_thread.daemon = True
    task_thread.daemon = True
    
    project_thread.start()
    task_thread.start()
    
    project_thread.join()
    task_thread.join()