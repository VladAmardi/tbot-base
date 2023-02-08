# syntax=docker/dockerfile:1
FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
RUN apt-get update && apt-get install -y iputils-ping less vim telnet net-tools python3-dev iproute2
COPY requirements.txt /code/
RUN /usr/local/bin/python -m pip install --upgrade pip && pip install -r requirements.txt
COPY entrypoint.sh /entrypoint.sh
RUN mkdir /src
COPY procname-0.2 /src/procname-0.2
RUN cd /src/procname-0.2 && make build
ENTRYPOINT ["/entrypoint.sh"]
