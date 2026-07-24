echo "-Xms128M" >> /apache-cassandra-5.0.8/conf/jvm-server.options
echo "-Xmx128M" >> /apache-cassandra-5.0.8/conf/jvm-server.options

PROJECT=${PROJECT}

sed -i "s/^listen_address:.*/listen_address: "`hostname`"/" /apache-cassandra-5.0.8/conf/cassandra.yaml
sed -i "s/^rpc_address:.*/rpc_address: "`hostname`"/" /apache-cassandra-5.0.8/conf/cassandra.yaml
sed -i "s/- seeds:.*/- seeds: ${PROJECT}-cassandra-1,${PROJECT}-cassandra-2,${PROJECT}-cassandra-3/" /apache-cassandra-5.0.8/conf/cassandra.yaml

/apache-cassandra-5.0.8/bin/cassandra -R
sleep infinity
