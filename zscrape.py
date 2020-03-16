# CLI app to scrape job details (what, where) from Indeed into a new table in db.

from bs4 import BeautifulSoup
from cs50 import SQL
import requests
import re
import string
import datetime
import time
import argparse
import sys
from price_parser import Price
from geopy.geocoders import GoogleV3
import geopy.geocoders
import os
import logging
from tqdm import tqdm

KEY = os.getenv('API_KEY')

def main():
    # Set logging preferences
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("geopy").setLevel(logging.WARNING)

    # Command line help
    parser = argparse.ArgumentParser(description = 'A web scraper for Indeed.com')
    parser.add_argument('--what', required = 'True', help = 'Job search team, e.g. "software developer"')
    parser.add_argument('--where', required = 'True', help = 'Location, e.g. "Bristol".')
    args = parser.parse_args()

    if not KEY:
        print("Error: Environmental variable 'API_KEY' must be set to a Google Maps credential.")
        return 1

    db_path = "jobs.db"

    # Execute
    vacancies = scrape(args.what, args.where)
    vacancies = geocode(vacancies, args.where)
    table_name = store(vacancies, args.what, args.where, db_path)

def scrape(what, where):
    '''
    Function to scrape listings from Indeed.  Returns list of job vacancy dictionaries.
    '''
    url = "https://www.indeed.co.uk"

    # Get total number of vacancies
    page = 0
    query = "/jobs?q=" + what + "&l=" + where + "&start=" + str(page)
    site = requests.get(url + query)
    whole_page = BeautifulSoup(site.text, "html.parser")
    total_vacancies = whole_page.find(id="searchCountPages")
    total_vacancies = int(total_vacancies.string.split()[3].replace(',', ''))

    print("Scraping ~" + str(total_vacancies) + " vacancies for '" + what + "' in '" + where + "'...")
    vacancies = []

    index = 0
    with tqdm(total = total_vacancies) as progress_bar:
        while True:
            # Set page to scrape from
            query = "/jobs?q=" + what + "&l=" + where + "&start=" + str(page)
            site = requests.get(url + query)
            whole_page = BeautifulSoup(site.text, "html.parser")

            for listing in whole_page.find_all(name="div", attrs={"class":"jobsearch-SerpJobCard"}):
                vacancies.append({})

                # Scrape job title
                for title in listing.find_all(attrs={"class":"title"}):
                    vacancies[index].update({"title" : str(listing.a["title"])})

                # Scrape salary
                if listing.find_all(name="span", attrs={"class":"salaryText"}):
                    for div in listing.find_all(name="span", attrs={"class":"salaryText"}):
                        vacancies[index].update({ "salary_raw" : div.string.strip("\n")})
                    if "year" in vacancies[index]["salary_raw"] and " - " in vacancies[index]["salary_raw"]:
                        bracket = vacancies[index]["salary_raw"].split(" - ")
                        vacancies[index].update({ "salary_min" : Price.fromstring(bracket[0]).amount_float, "salary_max" : Price.fromstring(bracket[1]).amount_float })
                        vacancies[index].update({ "salary_mid" : vacancies[index]["salary_max"] - (vacancies[index]["salary_max"] - vacancies[index]["salary_min"])/2 })
                    elif "year" in vacancies[index]["salary_raw"]:
                        annual_salary = vacancies[index]["salary_raw"].rstrip(" a year")
                        vacancies[index].update({ "salary_mid" : Price.fromstring(annual_salary).amount_float })
                        vacancies[index].update({ "salary_min" : None, "salary_max" : None })
                    else:
                        vacancies[index].update({"salary_raw" : None, "salary_min" : None, "salary_max" : None, "salary_mid" : None })
                else:
                    vacancies[index].update({"salary_raw" : None, "salary_min" : None, "salary_max" : None, "salary_mid" : None })

                # Scrape company
                for div in listing.find_all(attrs={"class":"sjcl"}):
                    if div.find_all(name="a"):
                        for company in div.find_all(name="a"):
                            if company.string:
                                vacancies[index].update({"company" : str(company.string.strip("\n"))})
                    else:
                        for company in div.find_all(name="span", attrs={"class":"company"}):
                            vacancies[index].update({"company" : str(company.string.strip("\n"))})

                # Scrape location
                for location in listing.find_all(attrs={"class":"location"}):
                    vacancies[index].update({"location" : str(location.string) })

                # Scrape URL and get description from the page at that URL
                for link in listing.find_all(attrs={"class":"title"}):
                    vacancies[index].update({"link" : str(url + str(link.a.get("href")))})
                    details = requests.get(url + link.a.get("href")) # Optimise here as Indeed redirects from this URL, reduce number of requests
                    description = BeautifulSoup(details.text, "html.parser")

                    for blurb in description.find_all(attrs={"id":"jobDescriptionText"}):
                        text = str(blurb.contents).replace('"','\\\"')
                        text = text.replace("'", "\\\'")
                        vacancies[index].update({"description" : text })

                index += 1

                progress_bar.update(1)

            # Check if on last page
            if whole_page.find_all(name="span", attrs={"class":"np"}, string=re.compile("Next")):
                page += 10
                time.sleep(0.5)
            else:
                break

    print ('Scraping successful!')
    return(vacancies)

def geocode(vacancies, where):
    '''
    Function to add lat and long to vacancy data using GeoPy and MapBox.
    '''
    geolocator = GoogleV3(api_key=KEY, domain='maps.google.co.uk')
    city = geolocator.geocode(where, exactly_one = True)

    print ('Geocoding...')

    for index, listing in enumerate(tqdm(vacancies)):
        company_location = geolocator.geocode((vacancies[index]["company"] + " " + vacancies[index]["location"]), exactly_one = True)
        if company_location is None:
            company_location = geolocator.geocode(vacancies[index]["location"], exactly_one = True)
            if company_location is None:
                company_location = city

        vacancies[index].update({ "latitude" : company_location.latitude, "longitude" : company_location.longitude })

        time.sleep(0.2)

    print("Geocoding successful!")
    return(vacancies)

def store(vacancies, what, where, db_path):
    '''
    Function to move list of job vacancies to SQLite database
    '''

    db = SQL("sqlite:///" + db_path)

    # Make args database friendly so they can be used to create the table name
    pattern = re.compile('[\W_]+')
    what_db = what; where_db = where
    pattern.sub('', what_db)
    pattern.sub('', where_db)

    # Create new table
    print("Adding to database...")
    table = what_db + "_" + where_db + "_"
    counter = 0
    while counter < 20:
        try:
            db.execute("CREATE TABLE :table ("
                            "job_id INTEGER PRIMARY KEY, "
                            "title TEXT, "
                            "company TEXT, "
                            "salary_raw TEXT, "
                            "salary_min REAL, "
                            "salary_max REAL, "
                            "salary_mid REAL, "
                            "location TEXT, "
                            "latitude TEXT, "
                            "longitude TEXT, "
                            "url TEXT, "
                            "description TEXT)",
                            table = table + str(counter))
            break
        except:
            counter += 1
    else:
        print("Error: too many tables for this search term.  Try dropping some tables.")
        return 1

    table_name = table + str(counter)

    # Record metadata
    db.execute("INSERT INTO metadata ("
                "'q_what', 'q_where', 'table_name') "
            "VALUES (:what, :where, :table_name)",
            what = what,
            where = where,
            table_name = table_name)

    # Move jobs from memory to table
    for job in tqdm(vacancies):
        db.execute("INSERT INTO :table_name ("
                    "title, company, salary_raw, salary_min, salary_max, salary_mid, location, latitude, longitude, url, description) "
                "VALUES ("
                    ":title, :company, :salary_raw, :salary_min, :salary_max, :salary_mid, :location, :latitude, :longitude, :link, :description);",
                table_name = table_name,
                title = job["title"],
                company = job["company"],
                salary_raw = job["salary_raw"],
                salary_min = job["salary_min"],
                salary_max = job["salary_max"],
                salary_mid = job["salary_mid"],
                location = job["location"],
                latitude = job["latitude"],
                longitude = job["longitude"],
                link = job["link"],
                description = job["description"])

    print ("Table " + table_name + " created successfully.  Find your job vacancies there :-)")

    return(table_name)

if __name__ == "__main__":
    main()