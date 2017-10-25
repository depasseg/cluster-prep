#!/usr/bin/env python
import json
import sys

def parse_blueprint_json(filename):
    with open(filename,'r') as bp:
        blueprint = json.load(bp)
        blueprint['items']
        if len(blueprint['items']) > 0:
            for i in blueprint['items']:
                 print i['Blueprints']['blueprint_name']

def parse_cluster_json(filename):
    with open(filename,'r') as bp:
        clusters = json.load(bp)
        clusters['items']
        if len(clusters['items']) > 0:
            for i in clusters['items']:
                print i['Clusters']['cluster_name']

def main():
    if len(sys.argv) != 3:
        print "Incorrect number of arguments."
        print "Usage: ./ParseResponse.py response.json <clusters|blueprints>"
        exit(1)
    else:
        if sys.argv[2] == "clusters":
            parse_cluster_json(sys.argv[1])
        elif sys.argv[2] == "blueprints":
            parse_blueprint_json(sys.argv[1])

        else:
            print "Unknown parse request"
            exit(1)

if __name__ == '__main__':
    main()
