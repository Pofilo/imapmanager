# Same official python image but without restrictions of official docker registry
FROM registry.pofilo.fr/python:3.14.6-alpine3.24

LABEL maintainer="Pofilo <git@pofilo.fr>"

ENV IMAPMANAGER_CONFIG_PATH="/etc/imapmanager.conf.yml"
ENV IMAPMANAGER_HEARTBEAT_PATH="/run/imapmanager.heartbeat"
ENV PYTHONUNBUFFERED=1

WORKDIR /imapmanager
COPY src pyproject.toml ./
RUN pip install . --root-user-action=ignore && rm -fr /imapmanager

# imapmanager writes the timestamp until it should be considered alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD test "$(date +%s)" -le "$(cat "$IMAPMANAGER_HEARTBEAT_PATH" 2>/dev/null || echo 0)"

ENTRYPOINT ["imapmanager"]
