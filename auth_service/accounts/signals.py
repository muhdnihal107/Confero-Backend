# # auth_service/accounts/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import FriendRequest
# from .tasks import send_notification_task
# import logging

# logger = logging.getLogger(__name__)
# @receiver(post_save, sender=FriendRequest)
# def handle_friend_request(sender, instance: FriendRequest, created: bool, **kwargs):
#     if created:
#         logger.info(f"Signal triggered for new FriendRequest: {instance.id}, receiver: {instance.receiver.id}")
#         # New friend request
#         send_notification_task.delay(
#             receiver_id=str(instance.receiver.id),
#             message=f"{instance.sender.username} sent you a friend request.",
#             notification_type="friend_request",
#             friend_request_id=str(instance.id)
#         )
#     else:
#         # Status updated (accepted or rejected)
#         if instance.status in ['accepted', 'rejected']:
#             logger.info(f"Signal triggered for updated FriendRequest: {instance.id}, status: {instance.status}")
#             send_notification_task.delay(
#                 receiver_id=str(instance.sender.id),
#                 message=f"Your friend request was {instance.status}.",
#                 notification_type=f"friend_request_{instance.status}",
#                 friend_request_id=str(instance.id)
#             )