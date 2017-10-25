# Rocana Ansible Playbooks

A set of utilities used to build a CDH or HDP hadoop cluster and deploys Rocana with Rocana Search.
* Rocana Search
* Rocana DLM
* Rocana Analytics
* Rocana WebApp
* Rocana HDFS Consumer
* Rocana Metrics Consumer
* Rocana Metadata Consumer
* Rocana Echo
* Rocana Scheduler
* Rocana Supervisors

## Features
 * An updated version of the Hadrian codebase was modified to configure and deploy relevant CDH6 (https://github.com/eBay/hadrian)
 * Hadrian supports the following Hadoop Components: HDFS/Yarn, Zookeeper, Hive, Impala and Kafka
 * CDH5/Kafka Parcel download and distribution
 * Cloudera Manager 5.x+ is also supported and deployed to manage the Hadoop instances. Follow Cloudera Documentation regarding CDH/CM compatibility.
 * Kerberos Support is included, but ONLY for DEV.  It uses this project to set up the KDC: https://github.com/joey/krb-bootstrap

* HDP cluster deployment is handled using the Ambari Blueprint framework.  Similar features to CDH, but a rocana-impala repository is required.
 * No Kerberos Support


## Getting Started - Prerequisites
1. Machines are online and ssh access is up and running
2. sudo permissions or root login access.
3. Password or passwordless authentication allowed between machines for either root user or a user with sudo privileges.
4. selinux disabled or permissive. Ideally, you disable it.
5. storage volumes formatted and mounted.
6. Forward and reverse DNS is set up on the boxes. Preferably a current /etc/hosts file has been distributed
7. A yum repository server with two repos
8. EPEL repo (internet or mirror) installed/configured on each host
9. Ansible is installed

## Required Repositories for Rocana and Hadoop
- rocana-<version> for CDH or rocana-<version>-hdp2.3.0 containing all of the Rocana rpms
- rocana-tools containing a valid Oracle jdk rpm (1.7.0_79 or jdk8)

NOTE: if you need instructions on setting up a yum repo server, see the bottom of this doc.

### Configuring Ansible
1. Edit the hosts inventory file to include your machines (FQDNs required).
2. The example hosts should be removed.  You can verify the overall list of hosts by running the following ansible command:
```
# this gives you a deduplicated list of hostnames in the inventory file
ansible -i hosts all -m setup --list-hosts
```
NOTE: hosts can be in multiple groups, it just determines where software is installed.

### Configuring the deployment - group_vars/all.yml
* The group_vars/all-example.yml has notes and instructions on how to properly configure the different variables. Please refer to that document for instructions.
* copy that file so that you have a all.yml
```
cp group_vars/all-example.yml group_vars/all.yml
```

### Configuring Rocana and Hadoop

There is an example configuration directory in configs/example. This contains all of the configuration files pushed to the Rocana cluster.  This maps directly to the name of the cluster in group_vars/all-example.yml (group_vars/all.yml post user update). If hdfs_ha is set to true, then this name becomes the HDFS nameservice as well. Example, hdfs://example/user/rocana


#### Hadoop Cluster Configurations
##### configs/<cluster_name>/hadrian/service_configs folder

* This folder contains the configuration files used by Hadrian to set up your Hadoop Cluster. This should have all the basic configurations that you need to run a small scale (single developer sized) cluster.  Larger installations should review the configurations and set accordingly.
* NOTE: The values in the .ini files are for the non-default values.

#### Example Directory

* ./configs/example/hadrian
* ./service_configs/hdfs.ini
* ./service_configs/yarn.ini
* ./service_configs/kafka.ini
* ./service_configs/zookeeper.ini
* ./service_configs/hive.ini
* ./service_configs/impala.ini

#### Example Configuration File - CDH5 HDFS
```
######################################################################################################
# HDFS Configurations
# NOTE: list all configurations that you want to apply in a comma separated list called config groups
# If you want to create additional Role Config Groups, simply create a section below with the configs
# and add the section name to the config_groups list
######################################################################################################

[HDFS]
config_groups=hdfs-DATANODE-BASE,hdfs-FAILOVERCONTROLLER-BASE,hdfs-NAMENODE-BASE,hdfs-GATEWAY-BASE,hdfs-BALANCER-BASE,hdfs-SECONDARYNAMENODE-BASE,hdfs-JOURNALNODE-BASE,hdfs-HTTPFS-BASE,hdfs-NFSGATEWAY-BASE

[hdfs-svc-config]
dfs_block_local_path_access_user=impala
zookeeper_service=zookeeper
dfs_block_size=268435456

[hdfs-DATANODE-BASE]
datanode_java_heapsize=1073741824
dfs_datanode_data_dir_perm=755
dfs_datanode_du_reserved=1864518041
dfs_datanode_max_locked_memory=469762048
dfs_data_dir_list=/dfs/dn

[hdfs-FAILOVERCONTROLLER-BASE]

[hdfs-NAMENODE-BASE]
namenode_java_heapsize=1073741824
dfs_name_dir_list=/dfs/nn
dfs_namenode_servicerpc_address=8022


[hdfs-GATEWAY-BASE]
dfs_client_use_trash=true
dfs_client_read_shortcircuit=true

[hdfs-BALANCER-BASE]
balancer_java_heapsize=163577856

[hdfs-SECONDARYNAMENODE-BASE]
secondary_namenode_java_heapsize=1073741824
fs_checkpoint_dir_list=/dfs/snn

[hdfs-JOURNALNODE-BASE]
dfs_journalnode_edits_dir=/dfs/jn

[hdfs-HTTPFS-BASE]

[hdfs-NFSGATEWAY-BASE]


```
At the top, there's the section HDFS.  That is a mapping to the Cloudera Manager Service Type.

* config_groups=comma separated list of section names

When Hadrian runs, it sets up the various services (HDFS, Yarn, etc).  Hadrian grabs the config_groups list, splits it, then applies the configurations to the service's role configuration groups.  By default, Hadrian uses the default config groups

NOTE: If you need/want to add multiline entries, it just needs to be idented.  See example below.

```
[mapreduce-JOBTRACKER-BASE]
jobtracker_mapred_local_dir_list=/x/cdh/mapred/jt/local
jobtracker_log_dir=/x/cdh/log/hadoop/jt
mapred_job_tracker_handler_count=40
jobtracker_java_heapsize=134217728
mapred_jobtracker_taskScheduler=org.apache.hadoop.mapred.FairScheduler
mapred_fairscheduler_poolnameproperty=mapred.job.queue.name
mapred_queue_names_list=default,dev
mapred_fairscheduler_allocation=<?xml version="1.0"?>
                                <allocations>
                                    <pool name="dev">
                                        <minMaps>4</minMaps>
                                        <minReduces>2</minReduces>
                                    </pool>
                                    <pool name="default">
                                        <minMaps>2</minMaps>
                                        <minReduces>1</minReduces>
                                    </pool>
                                </allocations>

```

### ./configs/example/hadrian/cm.ini
Cloudera Manager also has some configurations that can be modified.  The cm.ini file is slightly different than the cluster configurations.  For one, the defaults are in a section below for easy reference.  To overide, copy and paste the overrid and values in the top section.  See the two examples below.

- REMOTE_PARCEL_REPO_URLS is set based on what is in group_vars/all.yml, so no need to modify normally.  This is just an example, we're not using ebay repo servers.

```
[cloudera-manager-updates]
REMOTE_PARCEL_REPO_URLS=http://repo1.dev.rocana.com/altrepo/cdh/parcel-4.1.4-p110.11/,http://repo2.dev.rocana.com/altrepo/cdh/parcel-4.1.4/lzo-parcel/
PARCEL_DISTRIBUTE_RATE_LIMIT_KBS_PER_SECOND=51200

[cloudera-manager-defaults]
SYSTEM_IDENTIFIER=default
PARCEL_PROXY_PASSWORD=None
MANAGES_PARCELS=true
...
```

## Playbook Execution
1. yum install the EPEL - Only required if you don't have Ansible and dependencies available or already installed on your Ansible host
  - sudo yum install epel-release
2. sudo yum install ansible -y
3. copy the playbooks directory to your host.
4. cd rocana
5. Collect SSH keys because no one likes getting prompted.  Something similar to this, just replace host domain with a uniq string identifier for your hosts.
    - ```for i in `grep <host domain> hosts | sort | uniq`; do ssh-keyscan -t rsa $i >> ~/.ssh/known_hosts; done```
6. ```ansible-playbook -i hosts rocana.yml -f (# of parallel processes generally 40 or less) -s```

NOTE: execution is reentrant.  You can re-run if there are failures, so don't be shy about re-executing once you do a bit of tweaking.

## Setting up a yum repository server (almost simplest approach)
1. sudo yum install httpd createrepo
2. cd /var/www/html
3. mkdir rocana-2.1.3 rocana-tools
4. download Rocana rpms to rocana-2.1.3
5. cd rocana-2.1.3
6. createrepo .
7. copy jdk rpm to rocana-tools, repeat createrepo in that directory
8. verify that all files have at least 644 permissions otherwise your download attempts will fail
9. sed -i "s/SELINUX=enforcing/SELINUX=disabled/g" /etc/sysconfig/selinux #disable SELINUX
10. systemctl disable firewalld && systemctl stop firewalld #firewalld
11. systemctl disable iptables && systemctl stop iptables #iptables
10. service httpd start
11. chkconfig httpd on
