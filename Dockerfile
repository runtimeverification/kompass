ARG K_DISTRO=jammy
ARG KMIR_VERSION
ARG UV_VERSION=0.7.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM runtimeverificationinc/kmir:ubuntu-${K_DISTRO}-${KMIR_VERSION}

USER root
COPY --from=uv /uv /uvx /bin/

COPY . /home/kmir/.kompass
RUN chown -R kmir:kmir /home/kmir/.kompass

USER kmir:kmir
RUN bash -c 'rustup default $(rustup toolchain list)' && \
    echo  "alias kompass='uv --project /home/kmir/.kompass run -- kompass'" >> /home/kmir/.bashrc && \
    cd /home/kmir/.kompass && \
    ls -l && \
    make
