# jobscrapy

Command line tool to scrape job listings from Indeed.co.uk, optionally geocode with location data from Google Maps and output to a .json file. Features progress bar and error handling.

## Usage:

1.  Optional: if geocoding is required, set environmental variable API_KEY to your [Google Maps credential](https://cloud.google.com/maps-platform/) by running `export API_KEY=yourGoogleMapsAPIkeyhere` from the command line.

2.  `python scrapy.py --what "developer" --where "Bristol"` (add `-g` flag if geocoding)

## To-do:

- Allow user to select different output formats (e.g. CSV);
- Allow user to select locale. (Current default of Indeed.co.uk doesn't work with 'where's outside the UK, e.g. where = 'Scan Francisco');
- ~~Make geocoding optional by adding a new arg;~~
- ~~Combine three progress bars in to one single progress bar to rule them all;~~
- ~~Refactor in OOP to make Uncle Bob happy by creating a classes + methods.~~
