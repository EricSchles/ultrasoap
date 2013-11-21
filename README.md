# ultrasoap

[ultradns](https://www.ultradns.net) api client

## Overview

* [`ultrasoap library`](http://github.com/zoidbergwill/ultrasoap/ultrasoap/ultrasoap.py): Python wrapper for interacting with UltraDNS.

## Usage
```python
>>> import ultrasoap
>>> client = ultrasoap.UltraDNSClient(url, user, password, account_id)
>>> client.get_resource_records_of_zone(zone_name)

[(ResourceRecord){
   ...
    },
 (ResourceRecord){
    ...
 },
 ...
]
```


<!-- ## Documentation

[API Documentation](http://docs.yola.net/yodomains)
 -->
## Testing

Install development requirements:

    pip install -r requirements.txt

Tests can then be run by doing:

    nosetests

<!-- Integration tests are available, but are not run automatically. To run:

    nosetests tests.test_integration
 -->
Run the linting (pep8, pyflakes) with:

    flake8 ultrasoap

## API documentation

<!-- To generate the documentation:

    cd docs && PYTHONPATH=.. make singlehtml -->