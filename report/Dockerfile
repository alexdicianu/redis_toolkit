FROM golang:1.8
MAINTAINER Pantheon Systems

RUN apt-get update -y --fix-missing

WORKDIR /go/src/app
COPY app/ .

ENV GOPATH /go/src/app

RUN go get github.com/mediocregopher/radix.v2/redis
RUN go get github.com/olekukonko/tablewriter

RUN go build main.go

ADD run.sh /
RUN chmod 770 /run.sh

CMD [ "/run.sh" ]