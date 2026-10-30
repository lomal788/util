FROM python:3.12.7-alpine3.20
# The server pushes local wall-clock time to the boiler (its schedule runs on it)
RUN apk add --no-cache tzdata
ENV TZ=Asia/Seoul
WORKDIR /app
COPY navien_local_server.py .
EXPOSE 7000 8080
ENTRYPOINT ["python", "-u", "navien_local_server.py"]
