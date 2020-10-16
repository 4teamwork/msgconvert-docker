# msgconvert

A dockerized webservice to convert Microsoft Outlook .msg files to .eml
(message/rfc822) format.

## Description

msgconvert uses the Perl module Email::Outlook::Message for conversion.
It exposes just a single endpoint for uploading an .msg file and returns the
converted .eml. The webservice is written in Python using the aiohttp web server.

## Usage

To start the webservice just run
```
docker-compose up
```

The .msg file must be uploaded as multipart/form-data with a part named `msg`
containing the .msg file.

Example:

```
curl -F "msg=@tests/sample.msg" http://localhost:3000/
```

## Testing

To execute the tests, Python 3.8 with pytest and requests is required.

```
python3.8 -m venv venv
./venv bin/activate
pip install pytest requests
```

Tests are run by executing pytest:

```
pytest
```
