# jobscrapy

Command line tool to scrape job listings from Indeed.co.uk, optionally geocode with location data from Google Maps and output to a .json file. Features progress bar and error handling.

## Usage

1. Optional: if geocoding is required, set environmental variable API_KEY to your [Google Maps credential](https://cloud.google.com/maps-platform/) by running `export API_KEY=yourGoogleMapsAPIkeyhere`.

2. `python jobscrapy.py --what "developer" --where "Bristol"` (add `-g` flag if geocoding).

This results in:

![Screenshot showing command line use.](https://raw.githubusercontent.com/zackads/jobscrapy/master/static/screenshot1.png)

The output .json data schema looks like this: _(not a real job ad)_

```json
{
    "what": "python developer",
    "where": "Bristol",
    "datetime": "2020-04-17 17:48:33.726183",
    "content": [{
        "title": "Python/ Go Developer \u00a340-60k",
        "company": "Company name",
        "raw_location": "South West",
        "raw_salary": "\n\u00a340,000 - \u00a360,000 a year",
        "min_salary": 40000.0,
        "max_salary": 60000.0,
        "mid_salary": 50000.0,
        "detail_url": "http://www.indeed.co.uk/...",
        "description": "[<p><b>Are you a Developer who is keen to bleed the edges of your experience?</b></p>, <p>If so, we would love to hear from you! ... ",
        "search_term_what": "python developer",
        "search_term_where": "Bristol",
        "geocoded_location": {
            "latitude": 50.2212345,
            "longitude": -5.2712345
            }
        }
}
```

You can use the resulting .json file to work with the data, such as by using the [Plotly](https://plotly.com/python/) library to create visualisations:

![Screenshot showing a bubble map using job vacancy location and salary data, created with the Python library Plotly.](https://raw.githubusercontent.com/zackads/jobscrapy/master/static/screenshot2.png)

Happy job hunting!

## To-do

- Allow user to select different output formats (e.g. CSV).
- Allow user to select locale. (Current default of Indeed.co.uk doesn't work with 'where's outside the UK, e.g. where = 'San Francisco').
- ✅ ~~Make geocoding optional by adding a new arg.~~
- ✅ ~~Combine three progress bars in to one.~~
- ✅ ~~Refactor in OOP by creating classes + methods.~~
