FROM python:3.12-slim
RUN useradd --create-home agent
WORKDIR /app
COPY --chown=agent:agent program.py /app/program.py
RUN chown agent:agent /app
