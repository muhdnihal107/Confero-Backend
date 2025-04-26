# # auth_service/accounts/tasks.py
# import json
# import pika
# from celery import shared_task
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)

# @shared_task
# def send_notification_task(receiver_id: str, message: str, notification_type: str, friend_request_id: str = None):
#     logger.info(f"Executing send_notification_task for receiver: {receiver_id}")
#     try:
#         credentials = pika.PlainCredentials(
#             username=settings.RABBITMQ_USER,
#             password=settings.RABBITMQ_PASS
#         )
#         connection = pika.BlockingConnection(
#             pika.ConnectionParameters(
#                 host=settings.RABBITMQ_HOST,
#                 port=int(settings.RABBITMQ_PORT),
#                 credentials=credentials,
#                 virtual_host=settings.RABBITMQ_VHOST
#             )
#         )
#         channel = connection.channel()
#         channel.queue_declare(queue="notification_queue", durable=True)

#         notification_data = {
#             "receiver_id": receiver_id,
#             "message": message,
#             "type": notification_type,
#             "friend_request_id": friend_request_id
#         }

#         channel.basic_publish(
#             exchange="",
#             routing_key="notification_queue",
#             body=json.dumps(notification_data)
#         )
#         logger.info(f"Published notification to notification_queue: {notification_data}")
#         connection.close()
#     except Exception as e:
#         print(f"Error sending notification: {e}")
#         raise