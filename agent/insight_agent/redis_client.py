import redis

from .config import settings


class RedisStreams:
    def __init__(self, url: str = settings.redis_url) -> None:
        self.client = redis.from_url(url, decode_responses=True)

    def ensure_group(self, stream: str, group: str) -> None:
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError:
            # Group already exists.
            pass

    def publish(self, stream: str, payload: dict) -> str:
        return self.client.xadd(stream, payload, maxlen=10_000)

    def consume(self, stream: str, group: str, consumer: str, count: int = 1, block: int = 5_000):
        try:
            response = self.client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block)
        except redis.ResponseError:
            self.ensure_group(stream, group)
            return []
        messages = []
        if response:
            for _, entries in response:
                for message_id, fields in entries:
                    messages.append((message_id, fields))
        return messages

    def ack(self, stream: str, group: str, message_id: str) -> None:
        self.client.xack(stream, group, message_id)
