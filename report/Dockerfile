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
#RUN pip install dill

ADD run.sh /
RUN chmod 770 /run.sh

RUN mkdir -p /opt/tree/
ADD src/ /opt/

ENV PYTHONPATH $PYTHONPATH:/opt/tree/

CMD [ "/run.sh" ]