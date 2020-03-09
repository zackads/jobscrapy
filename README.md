# scrapy
Python command line tool to scrape job listings from Indeed.com and geocode with location data from Google Maps.

## Usage:
1.  Set environmental variable `API_KEY` to your Google Maps credentials;
2.  `python scrapy.py --what "developer" --where "Bristol"`

## To-do:
- Make geocoding optional by adding a new arg;
- Add ability to select output (e.g. .json file, CSV, SQLite) with another arg;
- Combine three progress bars in to one single progress bar to rule them all;
- Refactor in OOP to make Uncle Bob happy by creating a class + methods to replace functions + data structures.
