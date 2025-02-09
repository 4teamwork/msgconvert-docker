FROM alpine:3.21 AS alpine-upgrader
RUN apk upgrade --no-cache

FROM scratch AS alpine-upgraded
COPY --from=alpine-upgrader / /
CMD ["/bin/sh"]

FROM alpine-upgraded AS pkg-builder

RUN apk -U add \
    sudo \
    alpine-sdk \
    apkbuild-cpan \
    perl-doc \
    perl-email-address-xs

RUN mkdir -p /var/cache/distfiles && \
    adduser -D packager && \
    addgroup packager abuild && \
    chgrp abuild /var/cache/distfiles && \
    chmod g+w /var/cache/distfiles && \
    echo "packager ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

WORKDIR /work
RUN chown packager /work
USER packager

RUN abuild-keygen -a -i -n

COPY --chown=packager:packager packages/ ./

RUN cd perl-io-all && \
    abuild -r && \
    cd ../perl-pod-usage && \
    abuild -r && \
    cd ../perl-throwable && \
    abuild -r && \
    cd ../perl-email-abstract && \
    abuild -r && \
    cd ../perl-email-sender && \
    abuild -r && \
    cd ../perl-email-outlook-message && \
    abuild -r


FROM alpine-upgraded

RUN addgroup --system msgconvert \
     && adduser --system --ingroup msgconvert msgconvert

RUN --mount=from=pkg-builder,source=/home/packager/packages/work,target=/packages \
    --mount=from=pkg-builder,source=/etc/apk/keys,target=/etc/apk/keys \
    apk add --no-cache --repository /packages \
    perl-email-outlook-message \
    py3-aiohttp

ENV PYTHONUNBUFFERED 1
WORKDIR /app
USER msgconvert

EXPOSE 8080

COPY msgconvert.py .
CMD ["python3", "msgconvert.py"]
