from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

# user btpivkgp
# password RF8l3TViyZQRPu-zWWBkIRy3JY8bq_SZ
# amqps://btpivkgp:RF8l3TViyZQRPu-zWWBkIRy3JY8bq_SZ@gerbil.rmq.cloudamqp.com/btpivkgp
broker = RabbitBroker(
    "amqps://btpivkgp:RF8l3TViyZQRPu-zWWBkIRy3JY8bq_SZ@gerbil.rmq.cloudamqp.com/btpivkgp"
)
app = FastStream(broker)
exchange = RabbitExchange("exchange_chat", durable=True)
# queue_clients_greeting = RabbitQueue("greeting_with_clients")
# queue_notifying_client_operator = RabbitQueue("notifying_client_operator_connection")
queue_notify_client = RabbitQueue("notify_client")
queue_clients = RabbitQueue("from_clients")
queue_operators = RabbitQueue("from_operators")
