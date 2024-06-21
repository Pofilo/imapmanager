# Same official python image but without restrictions of official docker registry
FROM registry.pofilo.fr/python:3.12.4-alpine3.20

LABEL maintainer="Pofilo <git@pofilo.fr>"

ENV IMAPMANAGER_CONFIG_PATH="/etc/imapmanager.conf.yml"
ENV PYTHONUNBUFFERED 1

WORKDIR /imapmanager
COPY . .
RUN pip install . --root-user-action=ignore && rm -fr /imapmanager

ENTRYPOINT ["imapmanager"]
