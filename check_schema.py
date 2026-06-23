from cassandra.cluster import Cluster
try:
    cluster = Cluster(['127.0.0.1'])
    session = cluster.connect('timeseries')
    rows = session.execute("SELECT column_name FROM system_schema.columns WHERE keyspace_name = 'timeseries' AND table_name = 'aggregation_results'")
    print("Columns found:")
    for row in rows:
        print(f"- {row.column_name}")
except Exception as e:
    print(f"Error: {e}")
