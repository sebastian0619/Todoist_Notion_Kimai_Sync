import time
from threading import Thread
from logger import logger
from project_sync import sync_todoist_projects_to_notion, sync_notion_projects_to_todoist
from task_sync import sync_todoist_to_notion, sync_notion_to_todoist

def project_sync():
    try:
        logger.info("开始从 Notion 到 Todoist 的项目同步...")
        sync_notion_projects_to_todoist()
        logger.info("完成从 Notion 到 Todoist 的项目同步。")
        
        logger.info("开始从 Todoist 到 Notion 的项目同步...")
        sync_todoist_projects_to_notion()
        logger.info("完成从 Todoist 到 Notion 的项目同步。")
    except Exception as e:
        logger.error(f"项目同步过程中出错: {e}")

def sync_all():
    while True:
        project_sync()  # 每次任务同步前先进行项目同步
        
        try:
            logger.info("开始从 Todoist 到 Notion 的任务同步...")
            if not sync_todoist_to_notion():
                logger.info("没有新任务需要从 Todoist 同步到 Notion。")
            else:
                logger.info("完成从 Todoist 到 Notion 的任务同步。")
            
            logger.info("开始从 Notion 到 Todoist 的任务同步...")
            if not sync_notion_to_todoist():
                logger.info("没有新任务需要从 Notion 同步到 Todoist。")
            else:
                logger.info("完成从 Notion 到 Todoist 的任务同步。")
        except Exception as e:
            logger.error(f"任务同步过程中出错: {e}")
        
        time.sleep(120)  # 每两分钟进行一次完整的同步

if __name__ == "__main__":
    sync_thread = Thread(target=sync_all)
    sync_thread.daemon = True
    sync_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")