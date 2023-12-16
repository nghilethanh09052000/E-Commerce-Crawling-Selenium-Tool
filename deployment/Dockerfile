FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
# set LANG to avoid encoding errors
ENV LANG C.UTF-8

#============================================
# Install Python 3 and prerequisites
#============================================
RUN apt-get update \
    && apt-get install -y python3-pip python3-dev \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && pip3 install --upgrade pip

RUN apt-get install -y wget curl unzip xvfb libxi6 libgconf-2-4 \
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
    && apt-get install -y fonts-noto-cjk

RUN apt-get install -y tor

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

WORKDIR /specific-scraper

COPY _packages/ _packages/
COPY deployment/requirements.txt requirements.txt
COPY automated_moderation/deployment/requirements.txt automated_moderation_requirements.txt
COPY eb_infex_worker/information_extraction/requirements.txt infex_requirements.txt
RUN pip3 install -r requirements.txt -r automated_moderation_requirements.txt -r infex_requirements.txt
COPY . .

ARG ENVIRONMENT_NAME=production
ENV ENVIRONMENT_NAME="${ENVIRONMENT_NAME}"

ENV PYTHONPATH=/specific-scraper

EXPOSE 8000
CMD gunicorn -b 0.0.0.0:8000 --timeout 300 --max-requests 10 --workers=20 run:app
