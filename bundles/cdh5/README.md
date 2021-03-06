# Apache Hadoop with Spark

This bundle is a 7 node cluster designed to scale out. Built around Apache
Hadoop components, it contains the following units:

* 1 HDFS Master
* 1 HDFS Secondary Namenode
* 1 YARN Master
* 3 Compute Slaves
* 1 Spark
  - 1 Plugin (colocated on the Spark unit)


## Usage
Deploy this bundle using juju-quickstart:

    juju quickstart u/bigdata-dev/apache-hadoop-spark

See `juju quickstart --help` for deployment options, including machine 
constraints and how to deploy a locally modified version of the
apache-hadoop-spark bundle.yaml.


## Testing the deployment

### Smoke test HDFS admin functionality
Once the deployment is complete and the cluster is running, ssh to the HDFS
Master unit:

    juju ssh hdfs-master/0

As the `ubuntu` user, create a temporary directory on the Hadoop file system.
The steps below verify HDFS functionality:

    hdfs dfs -mkdir -p /tmp/hdfs-test
    hdfs dfs -chmod -R 777 /tmp/hdfs-test
    hdfs dfs -ls /tmp # verify the newly created hdfs-test subdirectory exists
    hdfs dfs -rm -R /tmp/hdfs-test
    hdfs dfs -ls /tmp # verify the hdfs-test subdirectory has been removed
    exit

### Smoke test YARN and MapReduce
Run the `terasort.sh` script from the Spark unit to generate and sort data. The
steps below verify that Spark is communicating with the cluster via the plugin
and that YARN and MapReduce are working as expected:

    juju ssh spark/0
    ~/terasort.sh
    exit

### Smoke test HDFS functionality from user space
From the Spark unit, delete the MapReduce output previously generated by the
`terasort.sh` script:

    juju ssh spark/0
    hdfs dfs -rm -R /user/ubuntu/tera_demo_out
    exit

### Smoke test Spark
SSH to the Spark unit and run the SparkPi demo as follows:

    juju ssh spark/0
    ~/sparkpi.sh
    exit


## Scale Out Usage
This bundle was designed to scale out. To increase the amount of Compute
Slaves, you can add units to the compute-slave service. To add one unit:

    juju add-unit compute-slave

Or you can add multiple units at once:

    juju add-unit -n4 compute-slave


## Contact Information

- <bigdata-dev@lists.launchpad.net>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
