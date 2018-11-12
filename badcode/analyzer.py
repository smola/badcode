#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor

import collections
import grpc
import os
import sys
import time

from lookout.sdk import service_analyzer_pb2_grpc
from lookout.sdk import service_analyzer_pb2
from lookout.sdk import service_data_pb2_grpc
from lookout.sdk import service_data_pb2

from .bblfshutil import bblfsh_monkey_patch
from .extract import TreeExtractor
from .settings import *
from .stats import Stats

#TODO(smola): set from single source
version = "alpha"
grpc_max_msg_size = 100 * 1024 * 1024 #100mb

class Analyzer(service_analyzer_pb2_grpc.AnalyzerServicer):
    def __init__(self, data_srv_addr):
        super(Analyzer).__init__()
        self.data_srv_addr = data_srv_addr
        self.tree_extractor = TreeExtractor(
            min_depth=DEFAULT_MIN_SUBTREE_DEPTH,
            max_depth=DEFAULT_MAX_SUBTREE_DEPTH,
            min_size=DEFAULT_MIN_SUBTREE_SIZE,
            max_size=DEFAULT_MAX_SUBTREE_SIZE
        )
        merged_path = str(DEFAULT_STATS_PATH) + '_merged'
        ranked_path = merged_path + '_ranked'
        pruned_path = ranked_path + '_pruned'
        self.stats = Stats.load(pruned_path)

    def NotifyReviewEvent(self, request, context):
        logger.info("got review request {}".format(request))

        # client connection to DataServe
        channel = grpc.insecure_channel(self.data_srv_addr, options=[
                ("grpc.max_send_message_length", grpc_max_msg_size),
                ("grpc.max_receive_message_length", grpc_max_msg_size),
            ])
        stub = service_data_pb2_grpc.DataStub(channel)
        changes = stub.GetChanges(
            service_data_pb2.ChangesRequest(
                head=request.commit_revision.head,
                base=request.commit_revision.base,
                include_pattern='.*\\.go$', #FIXME: allow more languages
                want_contents=True,
                want_uast=True,
                want_language=True,
                exclude_vendored=True))

        comments = []
        for change in changes:
            logger.debug("analyzing '{}' in {}".format(change.head.path, change.head.language))
            if change.head.uast is None:
                continue
            
            #TODO(smola): better handling of change.added_lines
            lines = set(range(1, len(change.head.content.splitlines()) + 1))

            for line, snippet in self.tree_extractor.get_snippets(
                    file=change.head,
                    lines=lines):
                if snippet in self.stats.totals:
                    service_analyzer_pb2.Comment(
                        file=change.head.path,
                        line=line,
                        text="Something looks wrong here: %s" % snippet.uast)
        logging.info("{} comments produced".format(len(comments)))
        return service_analyzer_pb2.EventResponse(analyzer_version=version, comments=comments)

    def NotifyPushEvent(self, request, context):
        pass

def serve(args):
    host_to_bind = args.host
    port_to_listen = args.port
    data_srv_addr = args.data_service

    print("starting gRPC Analyzer server at port {}".format(port_to_listen))
    server = grpc.server(thread_pool=ThreadPoolExecutor(max_workers=10))
    service_analyzer_pb2_grpc.add_AnalyzerServicer_to_server(Analyzer(data_srv_addr), server)
    server.add_insecure_port("{}:{}".format(host_to_bind, port_to_listen))
    server.start()

    one_day_sec = 60*60*24
    try:
        while True:
            time.sleep(one_day_sec)
    except KeyboardInterrupt:
        server.stop(0)

