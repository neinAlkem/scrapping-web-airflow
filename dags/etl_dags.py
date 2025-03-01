from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime,timedelta
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from sqlalchemy import create_engine
from airflow.operators.email import EmailOperator
from airflow.sensors.filesystem import FileSensor
from sqlalchemy import create_engine
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import logging
import time
import os


# --------------------------------- function --------------------------------- #
def extract_file(base_url='https://www.amazon.com/s?k=macbook&page={}&crid=3CHS3289UBR9B&qid=1740647689&sprefix=macb%2Caps%2C322&xpid=h062vM3nTWtUZ&ref=sr_pg_{}', max_pages=5):
    """
    Function to extract product details from Amazon Web.

    Parameters:
    :params base_url (str): The URL of the Amazon page containing the desired items.
    :params max_pages (int): The maximum number of pages to scrape.
    """
    
    products = []
    logging.basicConfig(level=logging.INFO)
    
    # Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    service = Service('chromedriver.exe')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
    options.add_argument("--disable-webrtc")  # Disable WebRTC
    
    REMOTE_SELENIUM_URL = "http://remote_chromedriver:4444/wd/hub"

    driver = webdriver.Remote(
        command_executor=REMOTE_SELENIUM_URL,  
        options=options
    )

    for page in range(1, max_pages + 1):
        url = base_url.format(page, page)
        logging.info(f"Scraping page {page}: {url}")

        driver.get(url)
        driver.save_screenshot("home.png")
        driver.set_window_size(1300,800)
        time.sleep(5)  # Wait for the page to load

        # Dynamic Scrolling
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  
            last_height = new_height
            
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
       # Find all products
        product_all = soup.find_all("div", {"data-component-type": "s-search-result"})

        # Extract product details
        for product in product_all:
            try:
                # Product Name
                product_name = product.find("h2", class_="a-size-medium a-spacing-none a-color-base a-text-normal")
                product_name = product_name.text.strip() if product_name else "No Title"

                #  Price
                price_tag = product.find("span", class_="a-price-whole")
                price_tag = price_tag.text.strip() if price_tag else "No Price Tag"

                # Rating
                rating = product.find("span", class_="a-icon-alt")
                rating = rating.text.strip() if rating else "No Rating"

                # Product Link
                link_tag = product.find("a", href=True)  # Cari elemen <a> yang punya 'href'
                link_produk = "https://www.amazon.com" + link_tag['href'] if link_tag else "No Link"

                products.append({
                    "product_name": product_name,
                    "price": price_tag,
                    "rating": rating,
                    "product_link" : link_produk
                })

            except Exception as e:
                logging.error(f"Error scraping an item: {e}")

        time.sleep(2) 

    driver.quit() 

    # Save to CSV
    df = pd.DataFrame(products)
    df.to_csv('/opt/airflow/dags/raw_data.csv', index=False, encoding="utf-8-sig")
    logging.info("Data berhasil disimpan: raw_data.csv")

def transform(dataframe = '/opt/airflow/dags/raw_data.csv') :
    """ 
    Function to transform extracted products file to a cleaned version.
    
    :param dataframe{str}: scraped file from extract_data function.
    """
    
    # Read params
    df = pd.read_csv(dataframe)
    logging.basicConfig(level=logging.INFO)
    
    # Delete '.' from price column and take only the products rating from rating column
    df['price'] = df['price'].replace(r'\.', '', regex=True)
    df['rating'] = df['rating'].str[:3]
    
    # Change failed scrapped value to Null
    df.loc[df['product_name'] == 'No Title', 'product_name'] = pd.NA
    df.loc[df['price'] == 'No Price Tag', 'price'] = pd.NA
    df.loc[df['rating'] == 'No ', 'rating'] = pd.NA
    df.loc[df['product_link'] == 'No Link', 'product_link'] = pd.NA
    
    # Change price column to integer type and rating column to float type
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    
    # Drop null and duplicated values
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    
    # Create new column for categorizing each products
    # Feel free to remove if you want to scape different products
    df['subcategory'] = 'Other'
    df.loc[df['product_name'].str.contains(r'Case|Casing|Bag|Shell'), 'subcategory'] = 'Laptop Case'
    df.loc[df['product_name'].str.contains(r'Charger|USB C|Docker|Port'), 'subcategory'] = 'Charger and Cable'
    df.loc[df['product_name'].str.contains(r'Mouse|Keyboard'), 'subcategory'] = 'Mouse and Keyboard'
    df.loc[df['product_name'].str.contains(r'Screen|External|Display'), 'subcategory'] = 'Screen Protector and External Display'
       
    # Save cleaned file to new file called 'cleaned_product.csv
    df.to_csv('/opt/airflow/dags/cleaned_data.csv', index=False)
    logging.info("Data berhasil disimpan: cleaned_products.csv")

def insert_csv_to_postgres():
    """Insert Cleaned File Value to PostgreSQL Database"""

    # PostgreSQL Connection
    engine = create_engine("postgresql+psycopg2://airflow:airflow@172.18.0.2:5432/amazon_products")
    
    # File Path
    file_path = "/opt/airflow/dags/cleaned_data.csv"
    
    # Cek apakah file ada sebelum melanjutkan
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} tidak ditemukan!")

    # Read CSV
    df = pd.read_csv(file_path)

    # Insert Data dengan metode bulk insert untuk efisiensi
    df.to_sql(
        name="products",  # Gunakan nama tabel yang valid
        con=engine,
        if_exists='append',
        index=False,
        method='multi',  # Optimasi bulk insert
        chunksize=500  # Batasi batch untuk efisiensi
    )

    print("Data berhasil dimasukkan ke PostgreSQL.")

# ----------------------------------- DAGS ----------------------------------- #
default_args = {
    'owner' : 'airflow',
    'start_date' : datetime(2025, 2, 28),
    'email_on_failure' : False,
    'retries' : 1,
    'retry_delay' : timedelta(minutes=5)
}

dag = DAG(
    'etl_scrapper_pipeline',
    default_args=default_args,
    description='Scrape -> Clean -> Load to MSSQL & Email',
    schedule_interval=timedelta(weeks=1)
)

extract_data = PythonOperator(
    task_id = 'scrapping_data',
    python_callable = extract_file,
    dag = dag,
)

wait_for_raw_file = FileSensor(
    task_id="wait_for_raw_file",
    filepath="/opt/airflow/dags/raw_data.csv",
    poke_interval=30, 
    timeout=300,  
    mode="poke",
    dag=dag,
)


transform_data = PythonOperator(
    task_id = 'transform_raw_data',
    python_callable=transform,
    dag = dag,
)

wait_for_cleaned_file = FileSensor(
    task_id="wait_for_cleaned_file",
    filepath="/opt/airflow/dags/cleaned_data.csv",
    poke_interval=30, 
    timeout=300,  
    mode="poke",
    dag=dag,
)

create_table_task = SQLExecuteQueryOperator(
    task_id = 'create_table_task',
    conn_id = 'amazon_products_connection',
    sql =  """ 
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        product_name TEXT NOT NULL,
        price INT NOT NULL,
        rating FLOAT NOT NULL,
        product_link TEXT NOT NULL,
        subcategory TEXT NOT NULL
    );
    """,
    dag=dag
)

insert_csv_task = PythonOperator(
    task_id='insert_csv',
    python_callable=insert_csv_to_postgres,
    dag=dag
)

# send_to_email = EmailOperator(
#     task_id = 'send_to_email',
#     to = 'kaptenbagaz@gmail.com',
#     subject = 'Scrapped Products File',
#     html_content = 'Scrapped File Attached Whitin this Massage',
#     files= ['/opt/airflow/dags/cleaned_data.csv'],
#     dag=dag,
# )

extract_data >> wait_for_raw_file >>  transform_data  >> wait_for_cleaned_file >> create_table_task >> insert_csv_task
