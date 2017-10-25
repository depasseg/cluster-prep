#!/usr/bin/env python


import json
import ConfigParser
import time
import os

config = ConfigParser.ConfigParser()
# Added to keep ConfingParser from lowercasing.
config.optionxform = str

def config_grabber(section):
    temp = dict()
    for i in config.options(section):
        temp.update({i:config.get(section,i)})
    return temp

def logger(message):
    return "%s %s" % (time.strftime("%Y-%m-%d %H:%M"), message)


# Generate Service configuration object
def get_ambari_configurations(service_configs):
    ambari_configurations = []

    if config_grabber("Globals")["hdfs.ha"].lower() == "true":
        config.read(["./hdfs-ha.ini"])

    for i in service_configs:
        logger("Reading %s configs" % (i))
        if (i == "hdfs-site" or i == "core-site") and config_grabber("Globals")["hdfs.ha"].lower() == "true":
            temp = config_grabber(i)
            temp.update(config_grabber("hdfs-ha-%s" % (i)))
            ambari_configurations.append({i : {"properties": temp}})
        else:
            ambari_configurations.append({i : {"properties": config_grabber(i)}})

    return ambari_configurations

def get_host_role_mapping(ambari_cluster_name):
    host_roles = {}
    for i in config_grabber(ambari_cluster_name)["headnode.full.list"].split(","):
        host_roles.update({i:config_grabber(ambari_cluster_name)["client.roles"].split(",")})

    cluster_roles_hosts = config_grabber(ambari_cluster_name + "-hn")
    if config_grabber("Globals")["hdfs.ha"].lower() == "true":
        ha_hosts_roles = config_grabber(ambari_cluster_name + "-hn-hdfs-ha")
        cluster_roles_hosts.update(ha_hosts_roles)

    # iterate through roles in cluster_specs.ini for head nodes and apply to each host.
    for k, v in cluster_roles_hosts.iteritems():
        hosts = v.split(",")
        if len(hosts) > 1:
            for i in hosts:
                host_roles[i].append(k)
        else:
            if k == "SECONDARY_NAMENODE" and config_grabber("Globals")["hdfs.ha"].lower() == "true":
                host_roles[v].append("NAMENODE")
            else:
                host_roles[v].append(k)

    # all right, this is a bit crazy.  we iterate through the list of datanodes and apply roles
    # if the host is already defined, then it does an update after using a Set so that there are no
    # duplicates.  awesome stuff.
    for i in config_grabber(ambari_cluster_name + "-dn")["full.list"].split(","):
        if host_roles.has_key(i):
            tmp_roles = host_roles[i]
            host_roles[i] = list(set(tmp_roles + config_grabber(ambari_cluster_name)["datanode.roles"].split(",")))

    host_roles.update({"datanodes":config_grabber(ambari_cluster_name)["datanode.roles"].split(",")})

    host_groups = []
    for key in host_roles.keys():
        components = []
        for i in host_roles[key]:
            components.append({"name":i})
        host_groups.append({"name": key, "configurations":[], "components": components, "cardinality": "1"})

    return host_groups

def generate_create_cluster(ambari_cluster_name, host_groups):
    create_cluster = {"blueprint": ambari_cluster_name, "host_groups":[]}
    headnode_list = config_grabber(ambari_cluster_name)["headnode.full.list"].split(",")
    full_datanode_list = config_grabber(ambari_cluster_name + "-dn")["full.list"].split(",")
    datanodes = []
    for host in host_groups:
        hostname = host["name"]
        if hostname == "datanodes":
            for datanode in full_datanode_list:
                if datanode not in headnode_list:
                    datanodes.append({"fqdn": datanode})
        else:
            create_cluster["host_groups"].append({"name":hostname, "hosts": [ { "fqdn" : hostname}]})
    if len(datanodes) > 0:
        create_cluster["host_groups"].append({"name":"datanodes", "hosts":datanodes})

    return create_cluster

def main():
    config.read(['./hadrian-hdp.ini','./cluster-specs.ini'])


    ambari_cluster_name = config_grabber("Globals")['ambari.cluster.name']
    ambari_username = config_grabber("Globals")['ambari.username']
    ambari_password = config_grabber("Globals")['ambari.password']
    ambari_port = config_grabber("Globals")['ambari.port']
    hdp_version = config_grabber("Globals")['hdp.version']

    #Grab all configuration files in the directory with the cluster Name.
    service_configs = []
    for i in os.listdir('./service_configs/'):
        service_configs.append(i.rstrip(".ini"))
        config.read('./service_configs/%s' % (i))

    service_configs = get_ambari_configurations(service_configs)
    host_groups = get_host_role_mapping(ambari_cluster_name)
    blueprint = {"configurations": service_configs,"host_groups": host_groups,"Blueprints": {"stack_name" : "HDP", "stack_version" : hdp_version}}

    with open("./rocana-blueprint.json", "w") as blueprint_file:

        blueprint_file.write(json.dumps(blueprint, indent=4))

    create_cluster = generate_create_cluster(ambari_cluster_name, host_groups)
    with open("./create-cluster.json", "w") as create_cluster_file:
        create_cluster_file.write(json.dumps(create_cluster, indent=4))


if __name__ == '__main__':
        main()
