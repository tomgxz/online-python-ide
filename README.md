# Online Python IDE

## Build locally

To build a local docker image and container, run:

```
docker build -t online-python-ide:latest .
docker run --privileged -p 8000:8000 online-python-ide:latest
```