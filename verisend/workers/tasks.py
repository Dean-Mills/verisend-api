import httpx
from verisend.workers.celery_app import celery_app


@celery_app.task
def test_task(url: str):
    print(f"Worker received URL: {url}")
    response = httpx.get(url)
    print(f"Downloaded {len(response.content)} bytes from blob")
    print("Worker done!")