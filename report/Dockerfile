FROM ubuntu:16.04
MAINTAINER Pantheon Systems

RUN apt-get update -y --fix-missing
RUN apt-get install redis-server -y

RUN apt-get install -y \
    build-essential \
    python \
    python-dev \
    python-pip \
    && apt-get autoremove -y \
    && apt-get clean

RUN pip install redis
RUN pip install python-levenshtein

ADD run.sh /
RUN chmod 770 /run.sh

ADD scripts/report_tree.py /scripts/report.py
RUN chmod 770 /scripts/report.py

WORKDIR /scripts/

CMD [ "/run.sh" ]