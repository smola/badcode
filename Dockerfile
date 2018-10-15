FROM ubuntu:bionic

ADD badcode /code/badcode
ADD setup.py /code/
ADD requirements.txt /code/
WORKDIR /code

RUN \
	apt-get update && \
	apt-get install -y python3-dev python3-pip libxml2-dev libgit2-dev libssl-dev git build-essential cmake wget && \
	rm -rf /var/lib/apt/lists

RUN \
	wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz && \
	tar xzf v0.27.0.tar.gz && \
	cd libgit2-0.27.0/ && \
	cmake . && \
	make && \
	make install && \
	cd /code && \
	rm -rf v0.27.0.tar.gz libgit2-0.27.0/

RUN \
	cd /code && \
	pip3 install -r requirements.txt && \
	pip3 install .

ENTRYPOINT ["/usr/local/bin/badcode"]
