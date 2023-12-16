FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update -y \
    && apt-get install -y python3-pip python3-dev \
    && apt-get install -y wget \
    && apt-get install -y libfontconfig1 libxrender1 libxtst6 libxi6  \
    && apt-get install -y libxmlsec1-dev pkg-config \
    && apt-get install -y libcurl4-openssl-dev libssl-dev \
    && apt-get install -y libsm6 libxext6 libxrender-dev \
    && apt-get install -y firefox \
    && apt-get install -y whois \
    # install asian fonts to be able to screenshot asian websites
    && apt-get install -y language-pack-ja \
    && apt-get install -y japan* \
    && apt-get install -y language-pack-zh* \
    && apt-get install -y chinese* \
    && apt-get install -y language-pack-ko \
    && apt-get install -y korean* \
    && apt-get install -y fonts-arphic-ukai \
    && apt-get install -y fonts-arphic-uming \
    && apt-get install -y fonts-ipafont-mincho \
    && apt-get install -y fonts-ipafont-gothic \
    && apt-get install -y fonts-unfonts-core \
    && apt-get install -y fonts-noto-cjk \
    && cd ~

RUN apt-get install -y build-essential libgl1-mesa-glx libgtk-3-dev


#============================================
# Install Google Chrome
#============================================
RUN wget --no-verbose -O /tmp/chrome.deb http://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_110.0.5481.177-1_amd64.deb \
    && apt install -y /tmp/chrome.deb \
    && apt-mark hold google-chrome-stable \
    && rm /tmp/chrome.deb

#============================================
# Install ChromeDriver
#============================================
RUN wget https://chromedriver.storage.googleapis.com/110.0.5481.77/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip

#============================================
# Configure ChromeDriver
#============================================
RUN mv chromedriver /usr/bin/chromedriver \
    && chown root:root /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver

COPY eb_infex_worker/deployment/requirements.txt worker_requirements.txt
COPY deployment/requirements.txt requirements.txt
COPY _packages/ _packages/
RUN pip3 install -U pip setuptools
RUN pip3 install -r requirements.txt -r worker_requirements.txt

COPY . .

ARG ENVIRONMENT_NAME=development
ENV ENVIRONMENT_NAME="${ENVIRONMENT_NAME}"
ARG APPLICATION_NAME=
ENV APPLICATION_NAME="${APPLICATION_NAME}"
ARG SENTRY_RELEASE=no_release
ENV SENTRY_RELEASE="${SENTRY_RELEASE}"

EXPOSE 8000
