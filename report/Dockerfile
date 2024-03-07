FROM golang:1.22.0

RUN apt-get update -y 

WORKDIR /go/src/app

# ENV GOPATH /go/src/app

COPY app/ .

RUN go install github.com/olekukonko/tablewriter
RUN go install github.com/mediocregopher/radix.v2/redis

#ENV GO111MODULE=on
#ENV GOFLAGS=-mod=vendor

RUN go build main.go

ADD run.sh /
RUN chmod 770 /run.sh

CMD [ "/run.sh" ]