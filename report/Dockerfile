FROM golang:1.20.0
MAINTAINER Pantheon Systems

RUN apt-get update -y 

WORKDIR /go/src/app

ENV GOPATH /go/src/app

COPY app/ .

RUN go install github.com/olekukonko/tablewriter@latest
RUN go install github.com/mediocregopher/radix.v2/redis@latest

ENV GO111MODULE=on
ENV GOFLAGS=-mod=vendor

RUN go build main.go

ADD run.sh /
RUN chmod 770 /run.sh

CMD [ "/run.sh" ]