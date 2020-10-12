FROM alpine:3.12 as pkg-builder

RUN apk -U add \
    sudo \
    alpine-sdk \
    apkbuild-cpan \
    perl-doc

RUN mkdir -p /var/cache/distfiles && \
    adduser -D packager && \
    addgroup packager abuild && \
    chgrp abuild /var/cache/distfiles && \
    chmod g+w /var/cache/distfiles && \
    echo "packager ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

WORKDIR /work
USER packager

COPY --chown=packager:packager .abuild /home/packager/.abuild/
COPY .abuild/packager-5f82cd49.rsa.pub /etc/apk/keys/
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


FROM alpine:3.12

RUN addgroup --system msgconvert \
     && adduser --system --ingroup msgconvert msgconvert

COPY --from=pkg-builder /home/packager/packages/work/ /packages/
COPY .abuild/packager-5f82cd49.rsa.pub /etc/apk/keys/

RUN apk add --no-cache --repository /packages \
    perl-email-outlook-message \
    py3-aiohttp

WORKDIR /app
USER msgconvert

EXPOSE 8080

COPY msgconvert.py .
CMD ["python3", "msgconvert.py"]
