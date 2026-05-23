import requests
import os

def slack_alert(context):
    webhook_url = os.getenv("SLACK_WEBHOOK")
    if not webhook_url:
        return
    
    dag_id = context['dag'].dag_id
    task_id = context['task_instance'].task_id
    
    requests.post(webhook_url, json={
        "text": f"❌ DAG 실패\nDAG: {dag_id}\nTask: {task_id}"
    })