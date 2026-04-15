FROM python:3.13.1-slim-bookworm
WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY /verisent /app/verisent
COPY /alembic /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
CMD ["/app/entrypoint.sh"]