ARG K_DISTRO=jammy
ARG K_COMMIT
ARG UV_VERSION=0.7.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM runtimeverificationinc/kframework-k:ubuntu-${K_DISTRO}-${K_COMMIT}
RUN    apt-get update        \
    && apt-get upgrade --yes \
    && apt-get install --yes \
         curl

COPY --from=uv /uv /uvx /bin/

ARG USER=user
ARG GROUP=$USER
ARG USER_ID=1000
ARG GROUP_ID=$USER_ID
RUN groupadd -g ${GROUP_ID} ${GROUP} && useradd -m -u ${USER_ID} -s /bin/sh -g ${GROUP} ${USER}
USER ${USER}:${GROUP}

ENV PATH="/home/${USER}/.cargo/bin:${PATH}"
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
RUN rustup toolchain install nightly-2024-11-29 --component llvm-tools --component rustc-dev --component rust-src
RUN rustup default nightly-2024-11-29-x86_64-unknown-linux-gnu

RUN mkdir /home/${USER}/workspace
WORKDIR /home/${USER}/workspace
