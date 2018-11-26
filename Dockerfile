FROM ubuntu:cosmic

WORKDIR /code
ADD badcode /code/badcode
ADD setup.py /code/
ADD requirements.txt /code/

RUN \
	apt-get update && \
	apt-get install -y python3-dev python3-pip libxml2-dev libssl-dev git libgit2-dev build-essential && \
	cd /code && \
	pip3 install -r requirements.txt && \
	pip3 install . && \
	apt-get remove -y build-essential && \
	apt-get autoremove -y && \
	rm -rf /var/lib/apt/lists

ENTRYPOINT ["/usr/local/bin/badcode"]
