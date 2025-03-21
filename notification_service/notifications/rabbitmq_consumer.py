from utils.rabbitmq import RabbitMQClient

def setup_rabbitmq_queues():
    rabbitmq_client = RabbitMQClient()
    rabbitmq_client.connect()
    
    #declare queues for notifications
    rabbitmq_client.declare_queue("friend_request_notifications")
    rabbitmq_client.declare_queue("room_invite_notifications")
    rabbitmq_client.declare_queue("public_room_notifications")
    
    return rabbitmq_client

if __name__ == "__main__":
    setup_rabbitmq_queues()
