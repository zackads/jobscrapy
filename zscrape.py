#!/usr/bin/env python3
"""
ZScrape: scrape job listings from Indeed.com.
"""

__author__ = "Zack Adlington"
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

URL = "http://www.indeed.co.uk"

def main(args):
    """ Main entry point of the app """
    scrapeAllJobAds(args.what, args.where)

def scrapeAllJobAds(what, where):
    '''Returns list of JobAd instances scraped from Indeed for given args'''
    job_ads = []
    first_results_page = ResultsPage(0, what, where)    
    total_job_count = getTotalResultCount(first_results_page.DOM)

    with tqdm(total = total_job_count) as progress_bar:
        page_counter = 0
        job_counter = 0
        while True:
            current_results_page = ResultsPage(page_counter, what, where)
            result_elements = current_results_page.results_elements
            for element in result_elements:         
                # Do scraping (in JobAd's constructor method)
                job_ads[job_counter] = JobAd(element)

                # Do geocoding if required
                if args.geocode is True: 
                    job_ads[job_counter].geocodeLocation

                job_counter += 1
                progress_bar.update(1)

def getTotalResultCount(results_page):
        '''Return int of total number of results'''
        total_result_count = results_page.find(id="searchCountPages")
        total_result_count = int(total_result_count.string.split()[3].replace(',', ''))
        return total_result_count

class ResultsPage():
    def __init__(self, page_number, what, where):
        self.DOM = self.getDOM(page_number, what, where)
        self.results_elements = self.getResultElements(self.DOM)

    @retry(wait_random_min=2000, wait_random_max=3000)
    def getDOM(self, page_number, what, where):
        '''Return BeautifulSoup object containing single page of results'''
        query = "/jobs?q=" + what + "&l=" + where + "&start=" + str(page_number)  
        site = requests.get(url + query)
        site.raise_for_status()

        return BeautifulSoup(site.text, "html.parser")

    def getResultElements(self, results_page):
        '''Returns iterable of individual result elements from results page'''
        return results_page.find_all(name="div", attrs={"class":"jobsearch-SerpJobCard"})

class JobAd():
    def __init__(self, element):
        self.title = self.getTitle(element)
        self.company = self.getCompany(element)
        self.raw_location = self.getRawLocation(element)
        self.raw_salary = self.getRawSalary(element)
        self.min_salary = self.parseMinSalary(element)
        self.max_salary = self.parseMaxSalary(element)
        self.mid_salary = self.calcMidSalary(element)
        self.detail_url = self.getDetailURL(element)
        self.description = self.getDescription(self.detail_url)
        
    def getTitle(self, element):
        '''Return job title'''
        return str(element.a["title"])
        
    def getCompany(self, element):
        '''Return company'''
        for div in element.find_all(attrs={"class":"sjcl"}):
            if div.find_all(name="a"):
                for company in div.find_all(name="a"):
                    if company.string:
                        return str(company.string.strip("\n"))
            else:
                for company in div.find_all(name="span", attrs={"class":"company"}):
                    return str(company.string.strip("\n"))
    
    def getRawLocation(self, element):
        '''Return location as a raw string literal'''
        location = element.find_all(attrs={"class":"location"})
        return str(location.string)

    def getRawSalary(self, element):
        if element.find_all(name="span", attrs={"class":"salaryText"}):
            for div in element.find_all(name="span", attrs={"class":"salaryText"}):
                return div.string.strip("\n")
        else:
            return None
    
    def parseMinSalary(self, raw_salary):
        '''
        Returns lowest value in salary range or salary value if not a range
        Disregards non-annual wages, e.g. 'per day' or 'per week' rates for contractors
        '''
        if raw_salary == None:
            return None
        else:
            if "year" in raw_salary and " - " in raw_salary:
                salary_range = raw_salary.split(" - ")
                # salary_range[0] contains number to  left of " - ", lower value in range
                min_salary = Price.fromstring(salary_range[0]).amount_float
                return min_salary
            elif "year" in raw_salary:
                annual_salary = raw_salary.rstrip(" a year")
                return annual_salary
    
    def parseMaxSalary(self, raw_salary):
        '''
        Returns highest value in salary range or salary value if not a range
        Disregards non-annual wages, e.g. 'per day' or 'per week' rates for contractors
        '''
        if raw_salary == None:
            return None
        else:
            if "year" in raw_salary and " - " in raw_salary:
                salary_range = raw_salary.split(" - ")
                # salary_range[0] contains number to  left of " - ", lower value in range
                max_salary = Price.fromstring(salary_range[1]).amount_float
                return max_salary
            elif "year" in raw_salary:
                annual_salary = raw_salary.rstrip(" a year")
                return annual_salary
    
    def calcMidSalary(self, min_salary, max_salary):
        '''Return mid point between min_salary and max_salary'''
        return min_salary + (max_salary - min_salary) / 2
        
    def getDetailURL(self, element):
        '''Return URL for page containing job listing detail'''
        for link in element.find_all(attrs={"class":"title"}):
            return str(URL + str(link.a.get("href")))

    def getDescription(self, detail_url):
        details = requests.get(detail_url)
        description = BeautifulSoup(details.text, "html.parser")

        for blurb in description.find_all(attrs={"id":"jobDescriptionText"}):
            job_description = str(blurb.contents).replace('"','\\\"')
            job_description = job_description.replace("'", "\\\'")
            return job_description
    
    def geocodeLocation(self, element):
        def geocodeCompany(self, element):
            pass
        
        def geocodeLocation(self, element):
            pass
    
        def geocodeCity(self, element):
            pass

        try: 
            geocodeCompany(element)
        except:
            pass

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

    if args.geocode == True:
        try:
            API_KEY = os.environ['API_KEY']
        except KeyError:
            print("Environmental variable API_KEY must be set to a Google Maps credential for geocoding.")
            sys.exit("Try running again with API_KEY set, or remove '-g' argument.")
            
    main(args)