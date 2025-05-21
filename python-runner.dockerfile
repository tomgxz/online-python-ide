FROM python:3.12-slim

RUN useradd -ms /bin/bash runner
RUN mkdir /sandbox && chown runner:runner /sandbox

WORKDIR /sandbox
USER runner

RUN python -m venv /sandbox/venv

ENV PATH="/sandbox/venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]
