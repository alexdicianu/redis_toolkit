FROM ubuntu:20.04
MAINTAINER Pantheon Systems

RUN apt-get update -y 
RUN apt-get install redis-server -y

RUN apt-get install -y \
    build-essential \
    python \
    python-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    && apt-get autoremove -y \
    && apt-get clean

RUN pip install redis

ADD run.sh /
RUN chmod 770 /run.sh

ADD src/injector.py /opt/
RUN chmod 770 /opt/injector.py

WORKDIR /opt/

CMD [ "/run.sh" ]