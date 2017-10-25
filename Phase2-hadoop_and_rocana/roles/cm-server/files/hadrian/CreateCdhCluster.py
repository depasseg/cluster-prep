#!/usr/bin/env python

"""
Copyright 2013 eBay Software Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from cm_api.api_client import ApiResource
from cm_api.api_client import ApiException
import ConfigParser
import time
import httplib
import os
import logging
CMD_TIMEOUT = 360
HA_ENABLE_TIMEOUT = 600

config = ConfigParser.ConfigParser()
# Added to keep ConfingParser from lowercasing. 
config.optionxform = str

# logging instantiation
FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(filename="hadrian-build.log",level=logging.INFO,format=FORMAT)

def config_grabber(section):
    temp = dict()
    for i in config.options(section):
        temp.update({i:config.get(section,i)})
    return temp

def get_cm_status(host):
    try:
        conn = httplib.HTTPConnection(host)
        conn.request("HEAD", "/")
        status = conn.getresponse().status
        return status
    except StandardError:
        return None
    finally:
        conn.close()


# Create HDFS and Format NN
def create_hdfs_service(cluster,api):
    
    """
    This section creates the HDFS service, assigns roles, and updates the configurations based on
    the configuration file and starts the service.
    
    If you choose to enable HA, then this will automatically set up HDFS HA and enable the automatic
    failover.
    """
   
    logging.info("Creating HDFS Service")
    hdfs = cluster.create_service("hdfs", "HDFS")
    # Create NN/SNN -determine host for NN and SNN

    host = config_grabber(cluster.name + "-hn")["name.node"]
    logging.info("Creating Namenode: " + host)
    hdfs.create_role("hdfs_NAMENODE_" + host.split(".")[0].translate(None,"-_"), "NAMENODE", host)
    
    host = config_grabber(cluster.name + "-hn")["secondary.namenode"]
    logging.info("Creating Secondary Namenode: " + host)
    hdfs.create_role("hdfs_SECONDARYNAMENODE_" + host.split(".")[0].translate(None,"-_"), "SECONDARYNAMENODE", host)
    
    for host in config_grabber(cluster.name + "-hn")["full.list"].split(","):    
        logging.info("Creating Gateway - Client Box: " + host)
        hdfs.create_role("hdfs_GATEWAY_" + host.split(".")[0].translate(None,"-_"), "GATEWAY", host)
    
    #Config the cluster
    logging.info("Updating HDFS configuration")
    hdfs.update_config(svc_config=config_grabber("hdfs-svc-config"))
    
    config_groups = config_grabber("HDFS")["config_groups"]
    
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = hdfs.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))
    
    
    # Create Data Nodes on the dn"s
    counter = 0
    for k,v in config_grabber(cluster.name + "-dn").iteritems():
        for host in v.split(","):      
            counter = counter + 1
            logging.info("Creating Datanode: " + host)
            hdfs.create_role("hdfs_DATANODE_" + host.split(".")[0].translate(None,"-_"), "DATANODE", host)
    
    if config_grabber("Globals")["hdfs_ha"].lower() == "true":
        jns = []
        for host in config_grabber(cluster.name + "-hn")["journal.node"].split(","):
            logging.info("Creating Journal Node list: " + host)
            jn = {}
            jn["jnHostId"] = str(api.get_host(host).hostId)
            jn["jnName"] = "hdfs_JOURNALNODE_" + host.split(".")[0].translate(None,"-_")
            if hdfs.get_role_config_group('hdfs-JOURNALNODE-BASE').get_config('full')['dfs_journalnode_edits_dir'].value is None:
                jn['jnEditsDir'] = '/dfs/jn'
            jns.append(jn)

        logging.info("Enabling NameNode HA with Quorum storage")

        primary_nn = hdfs.get_roles_by_type("NAMENODE")[0]
          
        logging.info("Enabling HDFS HA.")
        cmd = hdfs.enable_nn_ha(primary_nn.name, api.get_host(config_grabber(cluster.name + "-hn")["secondary.namenode"]).hostId, cluster.name, jns)
        if not cmd.wait(HA_ENABLE_TIMEOUT).success:
            logging.info("Problems with Enabling HA NameNodes.  Continuing on just to try.")
        else:
            logging.info("HDFS started.")

    else:
        logging.info("Formatting the NameNode")
        for nn in hdfs.get_roles_by_type("NAMENODE"):       
            cmd = hdfs.format_hdfs(nn.name)[0]
            if not cmd.wait(CMD_TIMEOUT).success:
              raise Exception("[" + time.strftime("%H:%M") + "] Failed to format HDFS")
            logging.info("Done formatting the NameNode: " + str(nn.hostRef.hostId))


    logging.info("Starting HDFS")
    cmd = hdfs.start()
    if not cmd.wait(CMD_TIMEOUT).success:
        raise Exception("[" + time.strftime("%H:%M") + "] Failed to start HDFS")
    logging.info("HDFS Started")
    cmd = hdfs.create_hdfs_tmp()
    if not cmd.wait(CMD_TIMEOUT).success:
        raise Exception("[" + time.strftime("%H:%M") + "] Failed to create /tmp in HDFS")
    logging.info("HDFS /tmp directory created successfully")

def create_yarn_service(cluster):
    
    """
    This section creates the Yarn service, assigns roles, and updates the configurations based on
    the configuration file and starts the service. 
    """
    
    logging.info("Creating Yarn Service")
    yarn = cluster.create_service("yarn", "YARN")
    
    logging.info("Updating Yarn configuration")
    yarn.update_config(svc_config=config_grabber("yarn-svc-config"))
    config_groups = config_grabber("YARN")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = yarn.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))
    
    host = config_grabber(cluster.name + "-hn")["resource.manager"]
    logging.info("Creating Resource Manager: " + host)
    yarn.create_role("yarn_RESOURCEMANAGER_" + host.split(".")[0].translate(None,"-_"), "RESOURCEMANAGER", host)
    
    host = config_grabber(cluster.name + "-hn")["job.history.server"]
    logging.info("Creating Job History Server: " + host)
    yarn.create_role("yarn_JOBHISTORY_" + host.split(".")[0].translate(None,"-_"), "JOBHISTORY", host)
    
    
    for host in config_grabber(cluster.name + "-hn")["full.list"].split(","):    
        logging.info("Creating Gateway - Client Box: " + host)
        yarn.create_role("yarn_GATEWAY_" + host.split(".")[0].translate(None,"-_"), "GATEWAY", host)
        
    # Create Node Managers on the dn"s
    for k,v in config_grabber(cluster.name + "-dn").iteritems():
        for host in v.split(","):      
            logging.info("Creating Node Managers: " + host)
            yarn.create_role("yarn_NODEMANAGER_" + host.split(".")[0].translate(None,"-_"), "NODEMANAGER", host)

    logging.info("Creating user's Mapred History Server directory")
    cmd = yarn.create_yarn_job_history_dir()
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to create yarn job history directory on HDFS.  Moving on.")
    else:
        logging.info("Job History server HDFS directory created successfully.")

 
    #logging.info("Starting Yarn")
    #cmd = yarn.start()
    #if not cmd.wait(CMD_TIMEOUT).success:
    #    logging.info("Problems Starting Yarn.  Continuing.")
    #logging.info("Yarn Started")

# Create Zookeeper Services
def create_zookeeper_service(cluster):
    
    """
    This section creates the Zookeeper service, assigns roles, and updates the configurations
    based on the configuration file.  It also does an init and start
    """
    
    logging.info("Creating Zookeeper Service")
    zk = cluster.create_service("zookeeper", "ZOOKEEPER")

    logging.info("Updating Zookeeper configuration")
    zk.update_config(svc_config=config_grabber("zookeeper-svc-config"))
    config_groups = config_grabber("ZOOKEEPER")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = zk.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))

    for host in config_grabber(cluster.name + "-hn")["zookeepers"].split(","):
        logging.info("Creating Zookeeper: " + host)
        zk.create_role("zookeeper_SERVER_" + host.split(".")[0].translate(None,"-_"), "SERVER", host)
        cmd = zk.init_zookeeper(host.split(".")[0].translate(None,"-_"))
    
    # snooze for a bit to let the ZKs initialize
    time.sleep(30)

    if config_grabber("Globals")["hdfs_ha"].lower() == "true":
        logging.info("Starting Zookeeper")
        cmd = zk.start()
        if not cmd.wait(CMD_TIMEOUT).success:
             logging.info("Failed to start Zookeeper.  Moving on. You can start ZK manually.")
        else:
             logging.info("Zookeeper Started")

# Create Hive Services
def create_hive_service(cluster):
        
    logging.info("Creating Hive Service")
    hive = cluster.create_service("hive", "HIVE")

    logging.info("Updating Hive configuration")
    hive.update_config(svc_config=config_grabber("hive-svc-config"))
    config_groups = config_grabber("HIVE")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = hive.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))
 
    for host in config_grabber(cluster.name + "-hn")["hive.metastores"].split(","):
        logging.info("Creating Hive Metastore: " + host)
        hive.create_role("hive_HIVEMETASTORE_" + host.split(".")[0].translate(None,"-_"), "HIVEMETASTORE", host)

    for host in config_grabber(cluster.name + "-hn")["hive.server2"].split(","):
        logging.info("Creating HiveServer2: " + host)
        hive.create_role("hive_HIVESERVER2_" + host.split(".")[0].translate(None,"-_"), "HIVESERVER2", host)      
        
    for host in config_grabber(cluster.name + "-hn")["full.list"].split(","):    
        logging.info("Creating Gateway - Client Box: " + host)
        hive.create_role("hive_GATEWAY_" + host.split(".")[0].translate(None,"-_"), "GATEWAY", host)
        
    logging.info("Creating Hive Metastore Database")
    cmd = hive.create_hive_metastore_tables()
    if not cmd.wait(CMD_TIMEOUT).success:
         logging.info("Failed to create Hive Metastore Tables.  Moving onto the Hive HDFS directories")
    else:
         logging.info("Hive Metastore database created")

    logging.info("Creating Hive Warehouse Directories in HDFS")
    cmd = hive.create_hive_warehouse()
    if not cmd.wait(CMD_TIMEOUT).success:
         logging.info("Failed to create Hive Warehouse Directories in HDFS.")
    else:
         logging.info("Hive Warehouse directories Created in HDFS")

    #logging.info("Starting Hive")
    #cmd = hive.start()
    #if not cmd.wait(CMD_TIMEOUT).success:
    #     logging.info("Failed to start the Hive Metastore. Moving on. You can configure the Hive Metastore manually")
    #else:
    #     logging.info("Hive Started")
         
# Create Impala Services
def create_impala_service(cluster):
    
    """
    This section creates the Impala service, assigns roles, and updates the configurations
    based on the configuration file.  It also does a directory create and start
    """
    
    logging.info("Creating Impala Service")
    impala = cluster.create_service("impala", "IMPALA")

    logging.info("Updating Impala configuration")
    impala.update_config(svc_config=config_grabber("impala-svc-config"))
    config_groups = config_grabber("IMPALA")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = impala.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))

    # Create Impalads on all datanodes
    counter = 0
    for k,v in config_grabber(cluster.name + "-dn").iteritems():
        for host in v.split(","):      
            counter = counter + 1
            logging.info("Creating Impala Daemon: " + host)
            impala.create_role("impala_IMPALAD_" + host.split(".")[0].translate(None,"-_"), "IMPALAD", host)  

    host = config_grabber(cluster.name + "-hn")["impala.state.store"]
    logging.info("Creating Impala State Store Server: " + host)
    impala.create_role("impala_STATESTORE_" + host.split(".")[0].translate(None,"-_"), "STATESTORE", host)

    host = config_grabber(cluster.name + "-hn")["impala.catalog.server"]
    logging.info("Creating Impala Catalog Server: " + host)
    impala.create_role("impala_CATALOGSERVER_" + host.split(".")[0].translate(None,"-_"), "CATALOGSERVER", host)

    if config_grabber("Globals")["system.database"] == "embedded":
        logging.info("Creating Impala database in the embedded database")
        cmd = impala.create_impala_catalog_database()
        if not cmd.wait(CMD_TIMEOUT).success:
             logging.info("Failed to create Impala Catalog database in embedded DB.  Moving on.")
        else:
             logging.info("Impala catalog database created in embedded DB.")

    
    logging.info("Creating Impala database catalog tables")
    impala.create_impala_catalog_database_tables()
    logging.info("Creating Impala HDFS User directory")
    cmd = impala.create_impala_user_dir()
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to create Impala user directory on HDFS.  Moving on.")
    else:
        logging.info("Impala HDFS user directory created.")


    #logging.info("Starting Impala")
    #cmd = impala.start()
    #if not cmd.wait(CMD_TIMEOUT).success:
    #    logging.info("Failed to start Impala.  Moving on.")
    #else:
    #    logging.info("Impala Started")

# Create Kafka Services
def create_kafka_service(cluster):
    
    """
    This section creates the Kafka service, assigns roles, and updates the configurations
    based on the configuration file.
    """

    logging.info("Creating Kafka Service")
    kafka = cluster.create_service("kafka", "KAFKA")

    logging.info("Updating Kafka configuration")
    kafka.update_config(svc_config=config_grabber("kafka-svc-config"))
    config_groups = config_grabber("KAFKA")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = kafka.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))

    for host in config_grabber(cluster.name + "-hn")["kafka.brokers"].split(","):
        logging.info("Creating Kafka Broker: " + host)
        kafka.create_role("kafka_KAFKA_BROKER_" + host.split(".")[0].translate(None,"-_"), "KAFKA_BROKER", host)
            
    #logging.info("Starting Kafka")
    #cmd = kafka.start()
    #if not cmd.wait(CMD_TIMEOUT).success:
    #    logging.info("Failed to start Kafka.  Moving on.")
    #else:
    #    logging.info("Kafka Started")


# Create Kafka Services
def enable_kerberos(cluster, cmanager):

    kdc_admin_user = "cloudera-scm/admin@%s" % (config_grabber("Globals")["kdc.realm"])

    cmd = cmanager.import_admin_credentials(kdc_admin_user, config_grabber("Globals")["kdc.admin.password"])
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to import kdc admin credentials.  Ending Kerberos set up.")
    else:
        logging.info("KDC Admin credentials imported")
        
    cmd = cluster.configure_for_kerberos()
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to configure for Kerberos")
    else:
        logging.info("Cluster configured for Kerberos")

    kafka = cluster.get_service("kafka")
    logging.info("Updating Kafka configuration")
    kafka.update_config(svc_config=config_grabber("kafka-svc-config"))
    config_groups = config_grabber("KAFKA")["config_groups"]
    for config_group in config_groups.split(","):
        logging.info("Updating Config Role Group: " + config_group)
        temp_config_group = kafka.get_role_config_group(config_group)
        temp_config_group.update_config(config_grabber(config_group))

    cmd = cmanager.generate_credentials()
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to configure for Kerberos")
    else:
        logging.info("Cluster configured for Kerberos")
        
    cmd = cluster.restart()
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to configure for Kerberos")
    else:
        logging.info("Cluster configured for Kerberos")   

########################################################################################################
#                                        End Services Section                                          #
########################################################################################################

def get_parcel(cluster, product, version):
    parcel = None
    retries = 0
    while retries < 10:
        try:
            parcel = cluster.get_parcel(product,version)
            break
        except ApiException:
            print "parcel not available yet: %s"  % (retries)
            retries = retries + 1
            time.sleep(30)
            continue
    return parcel

# Parcel distribution method
def distribute_parcel(cluster, product, version):

    parcel = get_parcel(cluster, product, version)
    if parcel is None:
        logging.info("Parcel %s: %s not found on remote server. Verify your parcel version and URLs" % (product, version))
        print "Parcel %s: %s not found on remote server. Verify your parcel version and URLs" % (product, version)
        exit(1)

    logging.info("" + product + " - Current parcel stage: " + str(parcel.stage))
    if parcel.stage == "UNAVAILABLE":
        logging.info("Giving CM time to find parcel information")
        while parcel.stage == "UNAVAILABLE":
            logging.info("Sleeping 2 seconds.")
            logging.info("" + product + " -  Parcel Status: " + parcel.stage)
            time.sleep(2)
            parcel = cluster.get_parcel(product,version)

    if parcel.stage == "AVAILABLE_REMOTELY":
        logging.info("Beginning Parcel " + product + ": " + version + " download.")
        parcel.start_download()
        while parcel.stage == "DOWNLOADING" or parcel.stage == "AVAILABLE_REMOTELY":
            parcel = cluster.get_parcel(product,version)
            time.sleep(10)
        logging.info("" + product + " -  Parcel Status: " + parcel.stage)
    
    logging.info("" + product + " - Current parcel stage: " + str(parcel.stage))
    if parcel.stage == "DOWNLOADED":
        parcel.start_distribution()
        while parcel.stage == "DOWNLOADED" or parcel.stage == "DISTRIBUTING":
            parcel = cluster.get_parcel(product,version)
            time.sleep(10)
        logging.info("" + product + " -  Parcel Status: " + parcel.stage)
    
    logging.info("" + product + " -  Current parcel stage: " + str(parcel.stage))
    if parcel.stage == "DISTRIBUTED":
        cmd = parcel.activate()
        if not cmd.wait(CMD_TIMEOUT).success:
            logging.info("Error activating parcel.  Exiting now.")
        else:
            logging.info("Parcel " + product + " " + version + " successfully downloaded and activated.")
        
def main():
    config.read(["./conf/hadrian.ini","./conf/cluster_specs.ini", "./conf/cloudera-manager/cm.ini"])

    cm_cluster_name = config_grabber("Globals")["cm.cluster.name"]
    cm_username = config_grabber("Globals")["cm.username"]
    cm_password = config_grabber("Globals")["cm.password"]
    cm_port = config_grabber("Globals")["cm.port"]
    version = config_grabber("Globals")["cdh.cluster.version"]
    cm_server = config_grabber(cm_cluster_name + "-hn")["cm.server"]
    
    #Grab all configuration files in the directory with the CM Cluster Name.
    
    for i in os.listdir("./conf/" + cm_cluster_name):
        config.read("./conf/" + cm_cluster_name + "/" + i)

    while (get_cm_status(cm_server + ":" + cm_port) != 200):
        logging.info("Waiting for CM Server to start... ")
        time.sleep(15)
    
    api = ApiResource(cm_server, cm_port, cm_username, cm_password, version=12)
    # create cluster or get existing cluster
    cluster_exists = False
    for i in api.get_all_clusters():
        if i.name == cm_cluster_name:
            cluster_exists = True 

    if cluster_exists == False:
        cluster = api.create_cluster(cm_cluster_name, version.upper())
        planned_nodes = config_grabber(cm_cluster_name + "-hn")["full.list"].split(",")
        for k, v in config_grabber(cm_cluster_name + "-dn").iteritems():
            for j in v.split(","):
                planned_nodes.append(j)
    
        # TODO make this smarter.  show which agents haven't checked in.  Add the option to continue without them.
        if len(api.get_all_hosts()) != len(planned_nodes):
            logging.info("Waiting for all agents to check into the CM Server before continuing.")
        
            while len(planned_nodes) > api.get_all_hosts():
                logging.info("Waiting for the final set of CM Agent nodes to check in.")
                time.sleep(5)
        
        logging.info("Updating Rack configuration for data nodes.")
        all_hosts = list()
        for host in api.get_all_hosts():
            all_hosts.append(host.hostId)
            for k,v in config_grabber(cm_cluster_name + "-dn").iteritems():
                if host.hostname in v:
                    logging.info("Setting host: " + host.hostname + " to rack /" + k)
                    host.set_rack_id("/" + k)
    
        logging.info("Adding all hosts to cluster.")
        cluster.add_hosts(all_hosts)

    else:
        cluster = api.get_cluster(cm_cluster_name)

    #Config CM
    logging.info("Applying any configuration changes to Cloudera Manager")
    cmanager = api.get_cloudera_manager()
    cmanager.update_config(config_grabber("cloudera-manager-updates"))
    if os.path.exists("/root/hadrian/cm_license.txt"):
       with open("/root/hadrian/cm_license.txt","r") as license:
          logging.info("Applying Enterprise License to Cloudera Manager")
          cmanager.update_license(license.read());

    if config_grabber('Globals')['cdh.distribution.method'] == 'parcels':
        # increase the parcel refresh frequency to one minute to find parcel repos in a more timely manner
        cmanager.update_config({"PARCEL_UPDATE_FREQ": 1})
        distribute_parcel(cluster, 'CDH', config_grabber('Globals')['cdh.parcel.version'])
        distribute_parcel(cluster, 'KAFKA', config_grabber('Globals')['kafka.parcel.version'])
        # restore parcel refresh time period to original 60 minutes
        cmanager.update_config({"PARCEL_UPDATE_FREQ": 60})
    
    # grab current services, so that we can skip services already defined to make this script reentrant
    current_services = []
    for i in cluster.get_all_services():
        current_services.append(i.type)
    
    if "ZOOKEEPER" not in current_services:
        create_zookeeper_service(cluster)
    
    if "HDFS" not in current_services:
        create_hdfs_service(cluster,api)    

    if "YARN" not in current_services:
        create_yarn_service(cluster)
    
    if "HIVE" not in current_services:
        create_hive_service(cluster)
    
    if "IMPALA" not in current_services:
        create_impala_service(cluster)
    
    if "KAFKA" not in current_services:
        create_kafka_service(cluster)
    
    if config_grabber("Globals")["kerberos.enabled"].lower() == "true":
        enable_kerberos(cluster, cmanager)
    else:
        logging.info("Starting remaining services.")
        cmd = cluster.start()

        if not cmd.wait(CMD_TIMEOUT).success:
             logging.info("Error in cluster services start. Please review Cloudera Manager for details.")
        else:
             logging.info("Remaining cluster services started.")

    logging.info("Starting final client configuration deployment for all services.")
    cmd = cluster.deploy_client_config()
    
    if not cmd.wait(CMD_TIMEOUT).success:
        logging.info("Failed to deploy client configuration.")
    else:
        logging.info("Client configuration deployment complete.  The cluster is all yours.  Happy Hadooping.")
        

if __name__ == "__main__":
        main()


