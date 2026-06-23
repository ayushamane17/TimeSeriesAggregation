# Time Series Aggregation Tool

## Project Overview

The Time Series Aggregation Tool is a web-based data processing application developed using Python, Flask, Pandas, and multiple database technologies. The application allows users to upload time-series datasets, configure aggregation rules, execute aggregation jobs, and store the aggregated output in different database systems.

The tool supports both SQL and NoSQL databases including SQLite, MySQL, PostgreSQL, MongoDB, and Apache Cassandra. Users can perform various aggregation operations on time-series data and export the results for further analysis.

---

# Objective

The objective of this project is to provide a flexible and user-friendly platform for aggregating large volumes of time-series data using configurable intervals and aggregation functions while supporting multiple database backends.

---

# Technologies Used

## Backend

* Python 3.x
* Flask
* Pandas
* NumPy
* SQLAlchemy

## Databases

* SQLite
* MySQL
* PostgreSQL
* MongoDB
* Apache Cassandra

## Frontend

* HTML5
* CSS3
* JavaScript

## Additional Technologies

* WSL2 Ubuntu (for Cassandra)
* Apache Cassandra 4.1.8
* Cassandra Python Driver

---

# Key Features

## CSV Upload

Upload time-series datasets directly through the web interface.

## Multiple Database Support

The tool supports:

* SQLite
* MySQL
* PostgreSQL
* MongoDB
* Apache Cassandra

## Aggregation Functions

Supported aggregation operations:

* SUM
* AVG (MEAN)
* MIN
* MAX
* COUNT
* STDDEV
* VARIANCE
* MEDIAN
* FIRST
* LAST

## Time-Based Aggregation

Supported intervals:

* 1 Minute
* 5 Minutes
* 15 Minutes
* 30 Minutes
* 1 Hour
* 4 Hours
* 12 Hours
* 1 Day

## Job Execution

Users can create and execute aggregation jobs through the web interface.

## Job Monitoring

Track:

* Job Status
* Aggregation Type
* Execution Time
* Duration
* Rows Read
* Rows Written

## CSV Export

Download aggregated output as CSV files.

## Responsive Web Interface

Modern UI for data upload, aggregation configuration, job execution, and result visualization.

---

# System Architecture

User Interface

↓

Flask Application

↓

Database Connector Layer

↓

Aggregation Engine (Pandas)

↓

Target Database

↓

Results & Job History

---

# Database Connector Architecture

The application uses a connector-based architecture.

Supported connectors:

* SQLiteConnector
* MySQLConnector
* PostgreSQLConnector
* MongoDBConnector
* CassandraConnector

Each connector provides:

* Database Connection
* Connection Testing
* Data Retrieval
* Result Storage

---

# Apache Cassandra Integration

## Cassandra Setup

Apache Cassandra was integrated using:

* WSL2 Ubuntu
* Java 17
* Apache Cassandra 4.1.8
* Cassandra Python Driver

## Cassandra Connection Flow

Flask Application

↓

get_connector()

↓

CassandraConnector

↓

Cassandra Driver

↓

Apache Cassandra

## Connection Verification

Connection was successfully verified using:

```python
from cassandra.cluster import Cluster

cluster = Cluster(['127.0.0.1'])
session = cluster.connect()

print("Connected to Cassandra successfully!")
```

---

# Project Structure

TimeSeriesAggregationTool/

├── app.py

├── aggregation/

│ └── engine.py

├── connectors/

│ ├── sqlite_connector.py

│ ├── mysql_connector.py

│ ├── postgres_connector.py

│ ├── mongodb_connector.py

│ ├── cassandra_connector.py

│ └── **init**.py

├── templates/

│ └── index.html

├── static/

│ ├── style.css

│ └── script.js

├── database/

├── output/

├── uploads/

└── README.md

---

# Installation

## Step 1

Clone the repository:

```bash
git clone <repository-url>
```

## Step 2

Navigate to project folder:

```bash
cd TimeSeriesAggregationTool
```

## Step 3

Install dependencies:

```bash
pip install -r requirements.txt
```

or

```bash
pip install flask pandas numpy sqlalchemy pymysql psycopg2-binary pymongo cassandra-driver
```

## Step 4

Start the application:

```bash
python app.py
```

## Step 5

Open browser:

```text
http://127.0.0.1:5000
```

---

# Testing

Successfully tested:

* CSV Upload
* Aggregation Engine
* SQLite Integration
* MySQL Integration
* PostgreSQL Integration
* MongoDB Integration
* Apache Cassandra Integration
* CSV Export
* Job History Tracking
* UI Workflow

---

# Future Enhancements

* Real-Time Streaming Aggregation
* Kafka Integration
* Interactive Charts & Dashboards
* User Authentication
* Role-Based Access Control
* Scheduled Aggregation Jobs
* Cloud Database Support
* Docker Deployment

---

# Conclusion

The Time Series Aggregation Tool provides a complete solution for processing and aggregating time-series datasets using configurable aggregation rules. The application successfully supports multiple SQL and NoSQL databases including SQLite, MySQL, PostgreSQL, MongoDB, and Apache Cassandra. The project demonstrates database connectivity, data processing, aggregation workflows, and modern web application development using Flask and Python.
