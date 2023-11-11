#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rdflib import Graph
import argparse
import datetime
import hashlib
import os
import rdflib
import subprocess
import sys

compete_command = ' '.join(sys.argv[1:])

do_watch = 0

if "conda install" in compete_command:
    do_watch = 1
if "conda remove" in compete_command:
    do_watch = 1
if "conda update" in compete_command:
    do_watch = 1

def list_packages_in_env(env_name):
    result = subprocess.run(['conda', 'list', '-p', env_name], stdout=subprocess.PIPE, text=True)
    lines = result.stdout.splitlines()
    packages = []
    for line in lines[3:]:  # Skip the header lines
        name, version, *_ = line.split()
        packages.append({'name': name, 'version': version})
    return packages

class CondaWatch:
    def __init__(self, data_file="conda-watch.hidden.ttl"):
        self.data_file = data_file
        self.env_name = os.getenv('CONDA_DEFAULT_ENV')
        self.env_path = os.getenv('CONDA_PREFIX')
        self.datestamp = str(datetime.datetime.now().replace(microsecond=0))
        self.datestamp_uri = rdflib.URIRef(f"urn:{self.datestamp.replace(' ', '_')}")
        self.changes_made = False

        self.graph = Graph()
        if os.access(self.data_file, os.F_OK):
            self.graph.parse(self.data_file, format="turtle")
        else:
            self.graph.bind("cw", rdflib.Namespace("http://conda-watch/#"))

    def add_singleton_to_graph(self, s, p, o):
        triples = list(self.graph.triples((s, p, o)))
        if not triples:
            self.graph.add((s, p, o))
            self.changes_made = True

    def add_conda_environment_to_graph(self):
        s = rdflib.URIRef(f"urn:{str(self.env_name).replace(' ', '_')}")
        p = rdflib.URIRef("cw:is")
        o = rdflib.Literal("conda-environment")
        self.add_singleton_to_graph(s, p, o)
        s = rdflib.URIRef(f"urn:{str(self.env_name).replace(' ', '_')}")
        p = rdflib.URIRef("cw:location")
        o = rdflib.Literal(self.env_path)
        self.add_singleton_to_graph(s, p, o)

    def do_it(self):
        if self.env_name is None:
            print('No conda environment is active.')
            return

        self.add_conda_environment_to_graph()

        data = []
        packages = list_packages_in_env(self.env_path)

        # Find the previous datestamp.
        p = rdflib.URIRef("cw:hasHash")
        triples = list(self.graph.triples((None, p, None)))
        sorted_triples = sorted(triples, key=lambda triple: str(triple[0]), reverse=True)
        previous_datestamp_uri, _, previous_md5_hash = sorted_triples[0]

        #
        # Add the command for a command history.
        #
        s = self.datestamp_uri
        p = rdflib.URIRef("cw:command")
        o = rdflib.Literal(compete_command)
        self.add_singleton_to_graph(s, p, o)     
        s = self.datestamp_uri
        p = rdflib.URIRef("cw:in_env")
        o = rdflib.Literal(self.env_name)
        self.add_singleton_to_graph(s, p, o)

        md5_hash = hashlib.md5(str(packages).encode('utf-8')).hexdigest()

        #
        # Store the md5 hash so future runs can compare to it.
        #
        s = self.datestamp_uri
        p = rdflib.URIRef("cw:has_hash")
        o = rdflib.Literal(md5_hash)
        self.add_singleton_to_graph(s, p, o)

        #
        # If the environment has not changed, then set a flag to indicate that.
        #
        if previous_md5_hash == md5_hash:
            s = self.datestamp_uri
            p = rdflib.URIRef("cw:same_as_previous")
            o = rdflib.Literal(previous_datestamp_uri)
            self.add_singleton_to_graph(s, p, o)     
        else:
            for package in packages:
                s = self.datestamp_uri
                p = rdflib.URIRef("cw:has_package")
                o = rdflib.URIRef(f"urn:{package['name']}")
                self.add_singleton_to_graph(s, p, o)

                s = rdflib.URIRef(f"urn:{package['name']}")
                p = rdflib.URIRef("cw:versioned")
                o = rdflib.Literal(package['version'])
                self.add_singleton_to_graph(s, p, o)

        if self.changes_made:
            self.graph.serialize(self.data_file, format="turtle")

def cw_subjects():
    cw = CondaWatch()
    unique_subjects = set(triple[0] for triple in cw.graph)
    sorted_unique_subjects = sorted(unique_subjects, key=str)
    for s in sorted_unique_subjects:
        print(f'{s}')

def cw_dates():
    cw = CondaWatch()
    p = rdflib.URIRef("cw:has_hash")
    filtered_triples = list(cw.graph.triples((None, p, None)))
    unique_subjects = set(triple[0] for triple in filtered_triples)
    sorted_unique_subjects = sorted(unique_subjects, key=str)
    for s in sorted_unique_subjects:
        print(f'{s}')

def cw_predicates():
    cw = CondaWatch()
    unique_predicates = set(triple[1] for triple in cw.graph)
    sorted_unique_predicates = sorted(unique_predicates, key=str)
    for p in sorted_unique_predicates:
        print(f'{p}')

def cw_triples():
    cw = CondaWatch()
    sorted_triples = sorted(cw.graph, key=lambda triple: (str(triple[0]), str(triple[1]), str(triple[2])))
    for s, p, o in sorted_triples:
        print(f'"{s}","{p}","{o}"')

def cw_history():
    cw = CondaWatch()
    p = rdflib.URIRef("cw:command")
    triples = list(cw.graph.triples((None, p, None)))
    sorted_triples = sorted(triples, key=lambda triple: str(triple[0]))
    headers = ("Timestamp", "Command")
    table = "| {:<23} | {:<20}\n".format(*headers)
    table += "| {:-<23} | {:-<22}\n".format("", "", "")
    for s, p, o in sorted_triples:
        table += "| {:<22} | {:<20}\n".format(str(s), str(o))
    print(table)

if do_watch == 1:
    cw = CondaWatch()
    cw.do_it()
else:
    #
    # When the script is called directly, instead of by the DEBUG trap, it will
    # actually be called twice. The second time, no arguments will be provided.
    # Therefore, if there are no arguments, then we should not do anything.
    #
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
            commands[args.command]()
