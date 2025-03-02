<<<<<<< HEAD
# AMAZON WEB SCRAPPING APPLICATION WITH AIRFLOW

!['Architeture Image'](assets/Archicteture.png)
This project involves extracting product data from Amazon using Selenium for dynamic web page interaction and BeautifulSoup for parsing structured information. The scraped data undergoes an ETL process orchestrated by Apache Airflow, running within Docker containers for seamless deployment. The workflow consists of multiple Airflow DAGs: an extraction task to scrape product details, a transformation task to clean and standardize data, and a loading task to store the processed data in PostgreSQL.

## Project Goal

- Implement Selenium Webdriver and BeautifulSoup to scrape raw data from Amazon Websales
- Perform full ETL using Python to create cleaned dataset file from raw scrapped data
- Use Airflow as orcestra to create Dags and PostgreSQL PgAdmin as database using Docker

## Tech Stack

- Python
- Airflow
- PostgreSQL / PgAdmin
- SQLAlchemy
- Selenium
- Docker
- BeautifulSoup4

## Pipeline Process

For Full Dags Documentation, Check : [`Dags`](dags\etl_dags.py)

`Setting Up Project Virtual Envirovment`

```Shell
python -m venv .venv
.venv/Scripts/activate
```
=======
# WEB SCRAPPING PIPELINE WITH AIRFLOW
>>>>>>> ca5f5de48c0e9d39f2e4b00c42c3ab2a6a77320b
