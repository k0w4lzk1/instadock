FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 socat netcat curl && \
    useradd -ms /bin/bash appuser
USER appuser
WORKDIR /home/appuser
COPY ./start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
