from redis import Redis
from rq import Worker, Queue

listen = ["exec"]
def get_redis():
    url = os.getenv("REDIS_URL")
    return Redis.from_url(url) if url else Redis(host="redis", port=6379, db=0)

if __name__ == "__main__":
    conn = get_redis()
    Worker([Queue(n, connection=conn) for n in listen]).work(with_scheduler=True)
