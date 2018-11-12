#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor

import collections
import difflib
import grpc
import os
import sys
import time

from lookout.sdk import service_analyzer_pb2_grpc
from lookout.sdk import service_analyzer_pb2
from lookout.sdk import service_data_pb2_grpc
from lookout.sdk import service_data_pb2

from .extract import TreeExtractor
from .settings import *
from .stats import Stats

#TODO(smola): remove this
from .bblfshutil import bblfsh_monkey_patch
bblfsh_monkey_patch()

#TODO(smola): set from single source
version = "alpha"
grpc_max_msg_size = 100 * 1024 * 1024 #100mb

class Analyzer(service_analyzer_pb2_grpc.AnalyzerServicer):
    def __init__(self, data_srv_addr, model_path):
        super(Analyzer).__init__()
        self.data_srv_addr = data_srv_addr
        self.tree_extractor = TreeExtractor(
            min_depth=DEFAULT_MIN_SUBTREE_DEPTH,
            max_depth=DEFAULT_MAX_SUBTREE_DEPTH,
            min_size=DEFAULT_MIN_SUBTREE_SIZE,
            max_size=DEFAULT_MAX_SUBTREE_SIZE
        )

        logger.info('Loading model: %s' % model_path)
        self.stats = Stats.load(model_path)
        logger.info('Loaded model: %s' % model_path)

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
            seqm = difflib.SequenceMatcher(
                None,
                change.base.content.splitlines(),
                change.head.content.splitlines(),
                )
            opcodes = seqm.get_opcodes()
            lines = set()
            for opcode in opcodes:
                if opcode[0] in ('insert', 'replace'):
                    lines |= set(range(opcode[3]+1, opcode[4]+1))

            for line, snippet in self.tree_extractor.get_snippets(
                    file=change.head,
                    lines=lines):
                #TODO(smola): speed up matching
                snippet = self.stats.match(snippet.uast)
                if snippet:
                    comment = service_analyzer_pb2.Comment(
                        file=change.head.path,
                        line=line,
                        text="Something looks wrong here: %s" % snippet.uast)
                    comments.append(comment)
        logging.info("{} comments produced".format(len(comments)))
        return service_analyzer_pb2.EventResponse(analyzer_version=version, comments=comments)

    def NotifyPushEvent(self, request, context):
        pass

def serve(args):
    host_to_bind = args.host
    port_to_listen = args.port
    data_srv_addr = args.data_service
    model_path = args.model

    logger.info("starting gRPC Analyzer server at port {}".format(port_to_listen))
    server = grpc.server(thread_pool=ThreadPoolExecutor(max_workers=10))
    analyzer = Analyzer(data_srv_addr, model_path)
    service_analyzer_pb2_grpc.add_AnalyzerServicer_to_server(analyzer, server)
    server.add_insecure_port("{}:{}".format(host_to_bind, port_to_listen))
    server.start()

    one_day_sec = 60*60*24
    try:
        while True:
            time.sleep(one_day_sec)
    except KeyboardInterrupt:
        server.stop(0)

