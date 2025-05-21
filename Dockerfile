FROM docker:dind

RUN apk add --no-cache python3 py3-pip py3-dotenv tini

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --break-system-packages -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["/sbin/tini", "--"]

CMD ["sh", "-c", "dockerd-entrypoint.sh & while(! docker info > /dev/null 2>&1); do sleep 1; done; python3 run_server.py"]
