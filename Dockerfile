FROM ubuntu:bionic

ENV LIBGIT2_VERSION=0.27.0

WORKDIR /code

RUN \
	apt-get update && \
	apt-get install -y python3-dev python3-pip libxml2-dev libssl-dev git build-essential cmake wget && \
	rm -rf /var/lib/apt/lists

RUN \
	wget https://github.com/libgit2/libgit2/archive/v${LIBGIT2_VERSION}.tar.gz && \
	tar xzf v${LIBGIT2_VERSION}.tar.gz && \
	cd libgit2-${LIBGIT2_VERSION}/ && \
	cmake . -DCMAKE_INSTALL_PREFIX=/usr && \
	make && \
	make install && \
	cd /code && \
	rm -rf v${LIBGIT2_VERSION}.tar.gz libgit2-${LIBGIT2_VERSION}/

ADD badcode /code/badcode
ADD setup.py /code/
ADD requirements.txt /code/

RUN \
	cd /code && \
	pip3 install -r requirements.txt && \
	pip3 install .

ENTRYPOINT ["/usr/local/bin/badcode"]
