# from celery import shared_task
# from django.core.mail import send_mail
# from django.conf import settings
# from rooms.models import Room,VideoCallSchedule
# import logging
# import pika
# import os
# import json
# from django.utils import timezone
# from django.db import transaction

# from datetime import timedelta

# logger = logging.getLogger(__name__)

# @shared_task
# def send_room_invite_email(room_id, receiver_id, sender_email, friend_email):
#     """
#     Celery task to send an email invitation to a friend for a room.
    
#     Args:
#         room_id (int): ID of the room.
#         receiver_id (int): ID of the invited user.
#         sender_email (str): Email of the user sending the invite.
#         friend_email (str): Email of the friend being invited.

#     """
#     logger.info(f"Processing email task for {friend_email} for room {room_id}")
#     try:
#         room = Room.objects.get(id=room_id)
#         subject = f"Invitation to join {room.name}"
#         message = (
#             f"Hi,\n\n"
#             f"You have been invited by {sender_email} to join the room '{room.name}'!\n"
#             f"Description: {room.description or 'No description provided'}\n\n"
#             f"To join the room, please visit our platform and accept the invitation.\n"
#             # f"Room Link: {settings.SITE_URL}/rooms/{room.slug}/\n\n"
#             f"Best,\n"
#             f"The Room Service Team"
#         )
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[friend_email],
#             fail_silently=False,
#         )
#         logger.info(f"Successfully sent email to {friend_email} for room {room_id}")
#     except Room.DoesNotExist:
#         # Log the error if the room doesn't exist
#         logger.error(f"Room with ID {room_id} does not exist")    
#     except Exception as e:
#         # Log any other errors during email sending
#         logger.error(f"Error sending email to {friend_email}: {str(e)}")

# # Send "room started" notification
# @shared_task
# def send_room_start_notification(schedule_id):
#     """
#     Send 'room_start' notifications to participants for a scheduled video call,
#     then mark the schedule as notified.
    
#     Args:
#         schedule_id (int): ID of the VideoCallSchedule.
#     """
#     connection = None
#     try:
#         with transaction.atomic():
#             # Lock the schedule to prevent concurrent updates
#             schedule = VideoCallSchedule.objects.select_for_update().get(id=schedule_id)
#             if schedule.is_notified:
#                 logger.info(f"Notification already sent for schedule {schedule_id}")
#                 return

#             logger.info(f"Processing schedule {schedule_id}, is_notified={schedule.is_notified}")

#             credentials = pika.PlainCredentials(
#                 os.getenv('RABBITMQ_USER', 'admin'),
#                 os.getenv('RABBITMQ_PASS', 'adminpassword')
#             )
#             connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(
#                     host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
#                     port=int(os.getenv('RABBITMQ_PORT', 5672)),
#                     credentials=credentials
#                 )
#             )
#             channel = connection.channel()
#             channel.queue_declare(queue="notification_queue", durable=True)

#             for participant in schedule.participants:
#                 notification_data = {
#                     "receiver_id": str(participant['id']),
#                     "message": f"Room '{schedule.room.name}' has started! Join now ",
#                     "type": "room_start",
#                     "friend_request_id": str(schedule.room.id),
#                 }
#                 channel.basic_publish(
#                     exchange="",
#                     routing_key="notification_queue",
#                     body=json.dumps(notification_data),
#                     properties=pika.BasicProperties(delivery_mode=2)
#                 )
#                 logger.info(f"Room start notification sent to user {participant['id']} for room {schedule.room.id}")

#             # Update is_notified, bypassing full_clean
#             schedule.is_notified = True
#             logger.info(f"Attempting to save schedule {schedule_id} with is_notified=True")
#             schedule.save(update_fields=["is_notified"], skip_validation=True)
#             logger.info(f"Successfully saved schedule {schedule_id} with is_notified=True")

#     except VideoCallSchedule.DoesNotExist:
#         logger.error(f"Schedule {schedule_id} does not exist")
#     except Exception as e:
#         logger.error(f"Error processing schedule {schedule_id}: {e}", exc_info=True)
#     finally:
#         if connection and not connection.is_closed:
#             connection.close()
#             logger.info(f"Closed RabbitMQ connection for schedule {schedule_id}")

# @shared_task
# def check_scheduled_video_calls():
#     """
#     Check for VideoCallSchedule instances due for notifications and trigger notification task.
#     """
#     try:
#         now = timezone.now()
#         with transaction.atomic():
#             schedules = VideoCallSchedule.objects.select_for_update().filter(
#                 scheduled_time__lte=now,
#                 is_notified=False
#             )
#             for schedule in schedules:
#                 logger.info(f"Triggering notifications for schedule {schedule.id} for room {schedule.room.name}")
#                 send_room_start_notification.delay(schedule.id)
#     except Exception as e:
#         logger.error(f"Error checking scheduled video calls: {e}")



import os
import pika
import json
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from rooms.models import Room, VideoCallSchedule
import logging

logger = logging.getLogger(__name__)

# @shared_task
# def send_room_invite_email(room_id, receiver_id, sender_email, friend_email):
#     """
#     Celery task to send an email invitation to a friend for a room.
    
#     Args:
#         room_id (int): ID of the room.
#         receiver_id (int): ID of the invited user.
#         sender_email (str): Email of the user sending the invite.
#         friend_email (str): Email of the friend being invited.
#     """
#     logger.info(f"Processing email task for {friend_email} for room {room_id}")
#     try:
#         room = Room.objects.get(id=room_id)
#         subject = f"Invitation to join {room.name}"
#         message = (
#             f"Hi,\n\n"
#             f"You have been invited by {sender_email} to join the room '{room.name}'!\n"
#             f"Description: {room.description or 'No description provided'}\n\n"
#             f"To join the room, please visit our platform and accept the invitation.\n"
#             f"Best,\n"
#             f"The Room Service Team"
#         )
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[friend_email],
#             fail_silently=False,
#         )
#         logger.info(f"Successfully sent email to {friend_email} for room {room_id}")
#     except Room.DoesNotExist:
#         logger.error(f"Room with ID {room_id} does not exist")    
#     except Exception as e:
#         logger.error(f"Error sending email to {friend_email}: {str(e)}")

# @shared_task
# def send_room_start_notification(schedule_id):
#     """
#     Send 'room_start' notifications to participants for a scheduled video call,
#     then delete the schedule.
    
#     Args:
#         schedule_id (int): ID of the VideoCallSchedule.
#     """
#     connection = None
#     try:
#         with transaction.atomic():
#             schedule = VideoCallSchedule.objects.select_for_update().get(id=schedule_id)
#             logger.info(f"Processing schedule {schedule_id}, scheduled_time={schedule.scheduled_time}, room_id={schedule.room_id}")

#             credentials = pika.PlainCredentials(
#                 os.getenv('RABBITMQ_USER', 'admin'),
#                 os.getenv('RABBITMQ_PASS', 'adminpassword')
#             )
#             connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(
#                     host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
#                     port=int(os.getenv('RABBITMQ_PORT', 5672)),
#                     credentials=credentials
#                 )
#             )
#             channel = connection.channel()
#             channel.queue_declare(queue="notification_queue", durable=True)

#             for participant in schedule.participants:
#                 notification_data = {
#                     "receiver_id": str(participant['id']),
#                     "message": f"Room '{schedule.room.name}' has started! Join now at http://localhost:3000/room/{schedule.room.id}",
#                     "type": "room_start",
#                     "friend_request_id": str(schedule.room.id),
#                 }
#                 channel.basic_publish(
#                     exchange="",
#                     routing_key="notification_queue",
#                     body=json.dumps(notification_data),
#                     properties=pika.BasicProperties(delivery_mode=2)
#                 )
#                 logger.info(f"Published notification to user {participant['id']} for room {schedule.room.id}: {notification_data}")

#             # Delete the schedule
#             schedule.delete()
#             logger.info(f"Deleted schedule {schedule_id} after sending notifications")

#     except VideoCallSchedule.DoesNotExist:
#         logger.error(f"Schedule {schedule_id} does not exist")
#     except Exception as e:
#         logger.error(f"Error processing schedule {schedule_id}: {e}", exc_info=True)
#     finally:
#         if connection and not connection.is_closed:
#             connection.close()
#             logger.info(f"Closed RabbitMQ connection for schedule {schedule_id}")

# @shared_task
# def check_scheduled_video_calls():
#     """
#     Check for VideoCallSchedule instances due for notifications and trigger notification task.
#     """
#     try:
#         now = timezone.now()
#         with transaction.atomic():
#             # Log all schedules for debugging
#             all_schedules = VideoCallSchedule.objects.all()
#             logger.info(f"Total schedules in database: {all_schedules.count()}")
#             for schedule in all_schedules:
#                 logger.info(f"Schedule {schedule.id}: scheduled_time={schedule.scheduled_time}, room_id={schedule.room_id}")

#             # Query due schedules
#             schedules = VideoCallSchedule.objects.select_for_update().filter(
#                 scheduled_time__lte=now
#             )
#             logger.info(f"Found {schedules.count()} schedules due for notification at {now}")
#             for schedule in schedules:
#                 logger.info(f"Triggering notifications for schedule {schedule.id}, room={schedule.room.name}, scheduled_time={schedule.scheduled_time}")
#                 send_room_start_notification.delay(schedule.id)
#     except Exception as e:
#         logger.error(f"Error checking scheduled video calls: {e}", exc_info=True)






#---------------------------------------------------------------------------------------


@shared_task
def send_room_invite_email(room_id, receiver_id, sender_email, friend_email):
    """
    Celery task to send an email invitation to a friend for a room.
    
    Args:
        room_id (int): ID of the room.
        receiver_id (int): ID of the invited user.
        sender_email (str): Email of the user sending the invite.
        friend_email (str): Email of the friend being invited.

    """
    logger.info(f"Processing email task for {friend_email} for room {room_id}")
    try:
        room = Room.objects.get(id=room_id)
        subject = f"Invitation to join {room.name}"
        message = (
            f"Hi,\n\n"
            f"You have been invited by {sender_email} to join the room '{room.name}'!\n"
            f"Description: {room.description or 'No description provided'}\n\n"
            f"To join the room, please visit our platform and accept the invitation.\n"
            # f"Room Link: {settings.SITE_URL}/rooms/{room.slug}/\n\n"
            f"Best,\n"
            f"The Room Service Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[friend_email],
            fail_silently=False,
        )
        logger.info(f"Successfully sent email to {friend_email} for room {room_id}")
    except Room.DoesNotExist:
        # Log the error if the room doesn't exist
        logger.error(f"Room with ID {room_id} does not exist")    
    except Exception as e:
        # Log any other errors during email sending
        logger.error(f"Error sending email to {friend_email}: {str(e)}")

# Send "room started" notification
@shared_task
def send_room_start_notification(schedule_id):
    try:
        schedule = VideoCallSchedule.objects.get(id=schedule_id)
        if schedule.is_notified:
            logger.info(f"Notification already sent for schedule {schedule_id}")
            return

        credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_USER', 'admin'),
            os.getenv('RABBITMQ_PASS', 'adminpassword')
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                port=int(os.getenv('RABBITMQ_PORT', 5672)),
                credentials=credentials
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue="notification_queue", durable=True)

        for participant in schedule.participants:
            notification_data = {
                "receiver_id": str(participant['id']),
                "message": f"Room '{schedule.room.name}' has started! Join now.",
                "type": "room_start",
                "friend_request_id": str(schedule.room.id),
            }
            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Room start notification sent to user {participant['id']} for room {schedule.room.id}")

        schedule.is_notified = True
        schedule.save()
        connection.close()
    except VideoCallSchedule.DoesNotExist:
        logger.error(f"Schedule {schedule_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending room start notification for schedule {schedule_id}: {e}")


@shared_task
def check_scheduled_video_calls():
    try:
        now = timezone.now()
        iso_time = now.isoformat().replace('+00:00', 'Z')
        schedules = VideoCallSchedule.objects.filter(
            scheduled_time__lte=now,
            is_notified=False
        )
        for schedule in schedules:
            logger.info(f"Processing schedule {schedule.id} for room {schedule.room.name}")
            send_room_start_notification.delay(schedule.id)
    except Exception as e:
        logger.error(f"Error checking scheduled video calls: {e}")