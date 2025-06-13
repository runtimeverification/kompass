ARG K_DISTRO=jammy
ARG KMIR_VERSION
ARG UV_VERSION=0.7.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM runtimeverificationinc/kmir:ubuntu-${K_DISTRO}-${KMIR_VERSION}

USER root
COPY --from=uv /uv /uvx /bin/

USER kmir:kmir
RUN mkdir /home/kmir/workspace
WORKDIR /home/kmir/workspace
