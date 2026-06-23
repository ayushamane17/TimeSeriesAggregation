from cassandra.cluster import Cluster
try:
    cluster = Cluster(['127.0.0.1'])
    session = cluster.connect('timeseries')
    # This adds the missing column to your database
    session.execute("ALTER TABLE aggregation_results ADD energy double")
    print("Successfully added the 'energy' column to the table!")
except Exception as e:
    print(f"Error: {e}")
