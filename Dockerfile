# Same official python image but without restrictions of official docker registry
FROM registry.pofilo.fr/python:3.7.9-slim

LABEL maintainer="Pofilo <git@pofilo.fr>"

ENV IMAPMANAGER_CONFIG_PATH="/etc/imapmanager.conf"

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

WORKDIR /usr/bin/local
COPY imapmanager/*\.py imapmanager/

ENTRYPOINT ["imapmanager/imapmanager.py"]

