#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime
import hashlib
import os
import subprocess
import sys

def list_packages_in_env(env_name):
    result = subprocess.run(['conda', 'list', '-p', env_name], stdout=subprocess.PIPE, text=True)
    lines = result.stdout.splitlines()
    packages = {}
    for line in lines[3:]:  # Skip the header lines
        name, version, *_ = line.split()
        packages[name] = version
    return packages

class CondaWatch:
    #
    # This init requires no packages to be installed.
    #
    def __init__(self, data_file="conda-watch.hidden.ttl", dot_file='conda-watch.hidden.dot'):
        self.data_file = data_file
        self.dot_file = dot_file
        self.env_name = os.getenv('CONDA_DEFAULT_ENV')
        self.env_path = os.getenv('CONDA_PREFIX')
        self.datestamp = str(datetime.datetime.now().replace(microsecond=0))
        self.changes_made = False
        self.graph = None

    def is_conda_env_active(self):
        return self.env_name is not None

    #
    # pylance complains about the type of the graph, but it is correct.
    #
    def add_singleton_to_graph(self, s, p, o):
        triples = list(self.graph.triples((s, p, o))) # type: ignore
        if not triples:
            self.graph.add((s, p, o)) # type: ignore
            self.changes_made = True

    def add_conda_environment_to_graph(self):
        s = URIRef(f"urn:{str(self.env_name).replace(' ', '_')}")
        p = URIRef("cw:is")
        o = Literal("conda-environment")
        self.add_singleton_to_graph(s, p, o)
        s = URIRef(f"urn:{str(self.env_name).replace(' ', '_')}")
        p = URIRef("cw:location")
        o = Literal(self.env_path)
        self.add_singleton_to_graph(s, p, o)

    def do_it(self):
        if self.env_name is None:
            print('No conda environment is active.')
            return

        self.graph = Graph()
        if os.access(self.data_file, os.F_OK):
            self.graph.parse(self.data_file, format="turtle")
        else:
            self.graph.bind("cw", Namespace("http://conda-watch/#"))

        self.datestamp_uri = URIRef(f"urn:{self.datestamp.replace(' ', '_')}")

        self.add_conda_environment_to_graph()

        data = []

        # Find the previous datestamp.
        p = URIRef("cw:hasHash")
        triples = list(self.graph.triples((None, p, None)))
        sorted_triples = sorted(triples, key=lambda triple: str(triple[0]), reverse=True)
        previous_datestamp_uri, _, previous_md5_hash = sorted_triples[0]

        #
        # Add the command for a command history.
        #
        s = self.datestamp_uri
        p = URIRef("cw:command")
        o = Literal(complete_command)
        self.add_singleton_to_graph(s, p, o)     
        s = self.datestamp_uri
        p = URIRef("cw:in_env")
        o = Literal(self.env_name)
        self.add_singleton_to_graph(s, p, o)

        packages = list_packages_in_env(self.env_path)
        md5_hash = hashlib.md5(str(packages).encode('utf-8')).hexdigest()

        #
        # Store the md5 hash so future runs can compare to it.
        #
        s = self.datestamp_uri
        p = URIRef("cw:has_hash")
        o = Literal(md5_hash)
        self.add_singleton_to_graph(s, p, o)

        #
        # If the environment has not changed, then set a flag to indicate that.
        #
        if previous_md5_hash == md5_hash:
            s = self.datestamp_uri
            p = URIRef("cw:same_as_previous")
            o = Literal(previous_datestamp_uri)
            self.add_singleton_to_graph(s, p, o)     
        else:
            for package_name, package_version in packages.items():
                s = self.datestamp_uri
                p = URIRef("cw:has_package")
                o = URIRef(f"urn:{package_name}")
                self.add_singleton_to_graph(s, p, o)

                s = URIRef(f"urn:{package_name}")
                p = URIRef("cw:versioned")
                o = Literal(package_version)
                self.add_singleton_to_graph(s, p, o)

        if self.changes_made:
            self.graph.serialize(self.data_file, format="turtle")

def cw_subjects(cw):
    unique_subjects = set(triple[0] for triple in cw.graph) # type: ignore
    sorted_unique_subjects = sorted(unique_subjects, key=str)
    for s in sorted_unique_subjects:
        print(f'{s}')

def cw_dates(cw):
    p = URIRef("cw:has_hash")
    filtered_triples = list(cw.graph.triples((None, p, None))) # type: ignore
    unique_subjects = set(triple[0] for triple in filtered_triples)
    sorted_unique_subjects = sorted(unique_subjects, key=str)
    for s in sorted_unique_subjects:
        print(f'{s}')

def cw_predicates(cw):
    unique_predicates = set(triple[1] for triple in cw.graph) # type: ignore
    sorted_unique_predicates = sorted(unique_predicates, key=str)
    for p in sorted_unique_predicates:
        print(f'{p}')

def cw_triples(cw):
    sorted_triples = sorted(cw.graph, key=lambda triple: (str(triple[0]), str(triple[1]), str(triple[2]))) # type: ignore
    for s, p, o in sorted_triples:
        print(f'"{s}","{p}","{o}"')

def cw_history(cw):
    p = URIRef("cw:command")
    triples = list(cw.graph.triples((None, p, None))) # type: ignore
    sorted_triples = sorted(triples, key=lambda triple: str(triple[0]))
    headers = ("Timestamp", "Command")
    table = "| {:<23} | {:<20}\n".format(*headers)
    table += "| {:-<23} | {:-<22}\n".format("", "", "")
    for s, p, o in sorted_triples:
        table += "| {:<22} | {:<20}\n".format(str(s), str(o))
    print(table)


###############################################################################
###############################################################################
# The script begins here.
#
###############################################################################
###############################################################################

#
# When the script is called directly, instead of by the DEBUG trap, it will
# actually be called twice. The second time, no arguments will be provided.
# Therefore, if there are no arguments, then we should not do anything.
#
if len(sys.argv[2:]) == 0:
    sys.exit(0)

complete_command = ' '.join(sys.argv[1:])

#
# No need to do anything if the command is not a conda command.
#
if not (complete_command.startswith('conda') or complete_command.startswith('./conda')):
    sys.exit(0)

#
# If a conda environment is being activated, don't track anything. Just exit.
#
if "conda activate" in complete_command:
    sys.exit(0)

cw = CondaWatch()

#
# If we are not in a conda env, then exit.
#
if not cw.is_conda_env_active():
    sys.exit(0)

packages = list_packages_in_env(cw.env_path)
if 'rdflib' not in packages:
    print('Please install the rdflib package so the conda-watch script can work or change to a different conda environment.')
    sys.exit(0)

from rdflib import Graph, Literal, Namespace, URIRef

do_watch = 0

if "conda install" in complete_command:
    do_watch = 1
if "conda remove" in complete_command:
    do_watch = 1
if "conda update" in complete_command:
    do_watch = 1

cw.graph = Graph()
if os.access(cw.data_file, os.F_OK):
    cw.graph.parse(cw.data_file, format="turtle")
else:
    cw.graph.bind("cw", Namespace("http://conda-watch/#"))

if do_watch == 1:
    cw.do_it()
else:
    if len(sys.argv[2:]) > 0:
        commands = {
            'cw-subjects': cw_subjects,
            'cw-dates': cw_dates,
            'cw-predicates': cw_predicates,
            'cw-triples': cw_triples,
            'cw-history': cw_history,
        }

        parser = argparse.ArgumentParser(description='Conda Watch command line interface.')
        parser.add_argument(
            'command', 
            choices = list(commands.keys()), 
            help = 'Command to execute.'
        )
        args = parser.parse_args(sys.argv[2:])

        if args.command in commands:
            commands[args.command](cw)
