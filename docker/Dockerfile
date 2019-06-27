FROM python:3.7-slim

RUN apt-get update && \
    apt-get install --no-install-recommends -qy \
    curl \
    tcpdump \
    vim && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    kubernetes \
    ipython \
    jinja2 \
    flask \
    pyeapi \
    jsonpatch \
    jsondiff \
    nornir

COPY ./entrypoint.sh /

ENTRYPOINT [ "/entrypoint.sh" ]

CMD ["sleep"]