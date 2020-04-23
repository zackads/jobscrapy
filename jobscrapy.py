#!/usr/bin/env python3
"""
jobscrapy: scrape job listings from Indeed.com, optionally geocode and output to a .json file.
"""

"""
To-do: 
    [ ] Change functions in to methods of classes.
    [ ] Remove side effects from functions/classes.
"""
__author__ = "Zack Adlington (github.com/zackads)"
__version__ = "0.1.0"
__license__ = "MIT"

from bs4 import BeautifulSoup
from tqdm import tqdm
from retrying import retry
from price_parser import Price
from geopy.geocoders import GoogleV3
import requests
import argparse
import os
import sys
import json
import datetime
import geopy

def main(args):
    try:
        first_results_page = ResultsPage(0, args.what, args.where)
        print(f"Scraping {first_results_page.getTotalResultCount()} job vacancies for '{args.what}' in '{args.where}'...")

        now = datetime.datetime.now()
        data = {
            "what" : args.what,
            "where" : args.where,
            "datetime" : str(now),
            "content" : scrapeAllJobAds(args.what, args.where)
        }

        if len(data['content']) == 0:
            print("No jobs found.  Try searching for a more general 'what' or a more specific 'where'.")
        else:
            filename_metadata = now.strftime("%Y%m%d") + "_" + args.what + "_" + args.where 
            filename = writeJsonToFile(data, filename_metadata)
            print(f"Success! Job vacancy data written to {filename}.  Thank you for using jobscrapy.")

    except OSError as err:
        print ("Looks like something went wrong with the file operation...")
        raise SystemExit(err)
    except requests.RequestException as err:
        print ("Looks like something went wrong with the requests operation...")
        raise SystemExit(err) 
    except geopy.exc.GeopyError as err:
        print ("Looks like something went wrong with the geocoding operation...")
        raise SystemExit(err)
    except Exception as err:
        print("Unexpected error.")
        raise SystemExit(err)

def scrapeAllJobAds(what, where):
    '''Returns list of JobAd dictionaries scraped from Indeed for given args'''
    job_ads = []
    first_results_page = ResultsPage(0, what, where)

    total_job_count = first_results_page.getTotalResultCount()

    with tqdm(total = total_job_count) as progress_bar:
        page_counter = 0
        while len(job_ads) < total_job_count:
            current_results_page = ResultsPage(page_counter, what, where)
            for result_element in current_results_page.result_elements:         
                # Do scraping (in JobAd's constructor method)
                this_ad = JobAd(result_element, what, where)

                # Do geocoding if required
                if args.geocode is True: 
                    this_ad.geocodeLocation()
                
                job_ads.append(this_ad.__dict__)

                progress_bar.update(1)
    return job_ads

def writeJsonToFile(data, filename_metadata):
    ''' Writes data to new file in current folder.  Returns filename.'''
    counter = 0
    success = False
    while success is not True:
        try:
            filename = filename_metadata + "_" + str(counter) + ".json"
            with open(filename, "x") as outfile:
                json.dump(data, outfile)
            success = True
        except FileExistsError:
            counter += 1
    return filename

class ResultsPage():
    def __init__(self, page_number, what, where):
        self.DOM = self.getDOM(page_number, what, where)
        self.result_elements = self.getResultElements(self.DOM)

    # https://pypi.org/project/retrying/
    @retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def getDOM(self, page_number, what, where):
        '''Returns BeautifulSoup object containing single page of results'''
        query = "/jobs?q=" + what + "&l=" + where + "&start=" + str(page_number)  
        site = requests.get(URL + query, timeout=5)
        site.raise_for_status() # Raise exception if occurs https://requests.readthedocs.io

        return BeautifulSoup(site.text, "html.parser")

    def getResultElements(self, results_page):
        '''Returns iterable of individual result elements from results page'''
        return results_page.find_all(name="div", attrs={"class":"jobsearch-SerpJobCard"})

    def getTotalResultCount(self):
        '''Return int of total number of results'''
        total_result_count = self.DOM.find(id="searchCountPages")

        if total_result_count == None:
            total_result_count = 0
        else:
            total_result_count = int(total_result_count.string.split()[3].replace(',', ''))

        return total_result_count   

class JobAd():
    def __init__(self, result_element, what, where):
        self.title = self.getTitle(result_element)
        self.company = self.getCompany(result_element)
        self.raw_location = self.getRawLocation(result_element)
        self.raw_salary = self.getRawSalary(result_element)
        self.min_salary = self.parseMinSalary()
        self.max_salary = self.parseMaxSalary()
        self.mid_salary = self.calcMidSalary()
        self.detail_url = self.getDetailURL(result_element)
        self.description = self.getDescription(self.detail_url)
        self.search_term_what = what
        self.search_term_where = where
        
    def getTitle(self, result_element):
        '''Return job title'''
        title_element = result_element.find('a', attrs={"class":"jobtitle"})
        title = title_element['title']
        return (title)
        
    def getCompany(self, result_element):
        '''Return company'''
        for div in result_element.find_all(attrs={"class":"sjcl"}):
            if div.find_all(name="a"):
                for company in div.find_all(name="a"):
                    if company.string:
                        return str(company.string.strip("\n"))
            else:
                for company in div.find_all(name="span", attrs={"class":"company"}):
                    return str(company.string.strip("\n"))
    
    def getRawLocation(self, result_element):
        '''Return location as a raw string literal'''
        location_element = result_element.find(attrs={"class":"location"})
        location = str(location_element.string)
        return location

    def getRawSalary(self, result_element):
        salary_element = result_element.find(attrs={"class":"salaryText"})
        if salary_element is None:
            return None
        else:
            return salary_element.string
    
    def parseMinSalary(self):
        '''
        Returns lowest value in salary range or salary value if not a range
        Disregards non-annual wages, e.g. 'per day' or 'per week' rates for contractors
        '''
        if self.raw_salary == None:
            return None
        else:
            if "year" in self.raw_salary and " - " in self.raw_salary:
                salary_range = self.raw_salary.split(" - ")
                # salary_range[0] contains number to left of " - ", i.e. the lower value in range
                return Price.fromstring(salary_range[0]).amount_float
            elif "year" in self.raw_salary:
                min_salary = self.raw_salary.rstrip(" a year")
                return Price.fromstring(min_salary).amount_float
    
    def parseMaxSalary(self):
        '''
        Returns highest value in salary range or salary value if not a range
        Disregards non-annual wages, e.g. 'per day' or 'per week' rates for contractors
        '''
        if self.raw_salary == None:
            return None
        else:
            if "year" in self.raw_salary and " - " in self.raw_salary:
                salary_range = self.raw_salary.split(" - ")
                # salary_range[0] contains number to  left of " - ", i.e. lower value in range
                return Price.fromstring(salary_range[1]).amount_float
            elif "year" in self.raw_salary:
                max_salary = self.raw_salary.rstrip(" a year")
                return Price.fromstring(max_salary).amount_float 

    def calcMidSalary(self):
        '''Return mid point between self.min_salary and self.max_salary'''
        if self.min_salary == None or self.max_salary == None:
            return None
        else:
            return self.min_salary + (self.max_salary - self.min_salary) / 2
        
    def getDetailURL(self, result_element):
        '''Return URL for page containing job listing detail'''
        for link in result_element.find_all(attrs={"class":"title"}):
            return str(URL + str(link.a.get("href")))

    def getDescription(self, url):
        description_page = requests.get(url)
        description_page = BeautifulSoup(description_page.text, "html.parser")
        return description_page.find(id='jobDescriptionText').get_text(" ")

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def geocodeLocation(self):
        '''
        Returns [latitude, longitude] for job listing.
        Many job listings use generic, wide, areas for the 'location' field.  
        E.g. 'London' rather than 'EC12' or 'Bristol' rather than 'BS6'.
        This function attempts to get around this by searching Google Maps for the 'company' near to the 'location' field.
        If this fails, it searches for the 'location' field near to the 'where' search term entered by the user.
        If that fails, it just geocodes 'where'.
        '''

        def geocodeCompany(self):
            '''Attempt to geocode based on 'company' near 'raw_location'.  Return False if unable.'''
            try:
                geocode_search_term = "{} {}".format(self.company, self.raw_location)
                company_location = geolocator.geocode(geocode_search_term, exactly_one = True)
                return {'latitude' : company_location.latitude, 'longitude' : company_location.longitude }
            except ValueError as error_message:
                print("Error: geocode failed on input {} with message {}".format(geocode_search_term, error_message))
                return False
            
        def geocodeLocation(self):
            '''Attempt to geocode based on 'location' near 'where'.  Return False if unable.'''
            try:
                geocode_search_term = "{} {}".format(self.raw_location, self.search_term_where)
                listing_location = geolocator.geocode(geocode_search_term, exactly_one = True)
                return {'latitude' : listing_location.latitude, 'longitude' : listing_location.longitude}
            except ValueError as error_message:
                print("Error: geocode failed on input {} with message {}".format(geocode_search_term, error_message))
                return False
    
        def geocodeWhere(self):
            '''Geocode 'where' search term.'''
            try:
                geocode_search_term = self.search_term_where
                search_term_location = geolocator.geocode(search_term_location, exactly_one = True)
                return {'latitude' : search_term_location.longitude, 'longitude' : search_term_location.latitude}
            except ValueError as error_message:
                print("Error: geocode failed on input {} with message {}".format(geocode_search_term, error_message))
                return False

        geopy.geocoders.options.default_timeout = 7
        geolocator = GoogleV3(api_key=API_KEY, domain='maps.google.com')
        city = geolocator.geocode(self.search_term_where, exactly_one = True)

        try:
            self.geocoded_location = geocodeCompany(self)
        except:
            try:
                self.geocoded_location = geocodeLocation(self)
            except:
                self.geocoded_location = geocodeWhere(self)

if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser(description = 'A web scraper for Indeed.com.')

    # Required positional argument
    parser.add_argument("what", help="String to search for.  E.g., 'Python developer'")
    parser.add_argument("where", help="City or location to sarch in.  E.g. 'London'")

    # Optional argument flag which defaults to False
    parser.add_argument("-g", "--geocode", action="store_true", default=False, help="Attempt to find location of job vacancy by company name, location and city.  Requires environmental variable 'API_KEY' to be set to a Google Maps credential.")

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()

    URL = "http://www.indeed.co.uk"

    if args.geocode == True:
        try:
            API_KEY = os.environ['API_KEY']
        except KeyError:
            sys.exit("Environmental variable API_KEY must be set to a Google Maps credential for geocoding.")
            
    main(args)