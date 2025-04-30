from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from rooms.models import Room,VideoCallSchedule
import logging
import pika
import os
import json


logger = logging.getLogger(__name__)

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

        for participant_id in schedule.participants:
            notification_data = {
                "receiver_id": str(participant_id),
                "message": f"Room '{schedule.room.name}' has started! Join now.",
                "type": "room_start",
                "friend_request_id": str(schedule.room.id),  # Room ID
            }
            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Room start notification sent to user {participant_id} for room {schedule.room.id}")

        connection.close()
        schedule.is_notified = True
        schedule.save()
    except VideoCallSchedule.DoesNotExist:
        logger.error(f"Schedule {schedule_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending room start notification for schedule {schedule_id}: {e}")

# New task: Send invites for scheduled video call
@shared_task
def send_scheduled_invites(schedule_id):
    try:
        schedule = VideoCallSchedule.objects.get(id=schedule_id)
        room = schedule.room
        creator = schedule.creator

        for participant_id in schedule.participants:
            try:
                participant = User.objects.get(id=participant_id)
                if participant_id not in room.invited_users:
                    room.invited_users.append(participant_id)
                    room.save()
                send_room_invite_email.delay(
                    room_id=room.id,
                    receiver_id=participant_id,
                    sender_email=creator.email,
                    friend_email=participant.email
                )
                logger.info(f"Queued invite email for {participant.email} for room {room.id}")
            except User.DoesNotExist:
                logger.error(f"User {participant_id} does not exist")
            except Exception as e:
                logger.error(f"Error sending invite to {participant_id} for room {room.id}: {e}")
    except VideoCallSchedule.DoesNotExist:
        logger.error(f"Schedule {schedule_id} does not exist")
    except Exception as e:
        logger.error(f"Error processing invites for schedule {schedule_id}: {e}")

# New task: Check for due video call schedules
@shared_task
def check_scheduled_video_calls():
    try:
        now = timezone.now()
        schedules = VideoCallSchedule.objects.filter(
            scheduled_time__lte=now,
            is_notified=False
        )
        for schedule in schedules:
            logger.info(f"Processing schedule {schedule.id} for room {schedule.room.name}")
            send_room_start_notification.delay(schedule.id)
            send_scheduled_invites.delay(schedule.id)
    except Exception as e:
        logger.error(f"Error checking scheduled video calls: {e}")