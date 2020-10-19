import os.path
import pytest
import requests
import shlex
import socket
import subprocess
import time


def test_convert_msg_to_eml(msgconvert, msg):
    with open(msg, 'rb') as msg_file:
        resp = requests.post(msgconvert, files={'msg': msg_file})

    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'message/rfc822'
    assert 'MIME-Version: 1.0' in resp.text


def test_convert_without_multipart_request(msgconvert):
    resp = requests.post(msgconvert)

    assert resp.status_code == 400
    assert resp.text == 'Multipart request required.'


def test_convert_without_msg(msgconvert):
    resp = requests.post(msgconvert, files={'foo': 'bar'})

    assert resp.status_code == 400
    assert resp.text == 'No msg provided.'


def test_convert_with_invalid_msg(msgconvert):
    resp = requests.post(msgconvert, files={'msg': 'bar'})

    assert resp.status_code == 500
    assert resp.text.startswith('Conversion failed.')


@pytest.fixture(scope="module")
def msgconvert():
    """Builds the docker image, starts the container and returns its URL.
    """
    context = os.path.dirname(os.path.dirname(__file__))
    run(f'docker build -t msgconvert:latest {context}')
    port = find_free_port()
    run(f'docker run -d -p {port}:8080 --name msgconvert msgconvert:latest')
    wait_until_ready(f'http://localhost:{port}/healthcheck')
    yield f'http://localhost:{port}'
    run('docker stop msgconvert')
    run('docker rm msgconvert')


@pytest.fixture(scope="module")
def msg():
    return os.path.join(os.path.dirname(__file__), 'sample.msg')


def wait_until_ready(url, timeout=10):
    start = now = time.time()
    while now - start < timeout:
        try:
            requests.get(url)
        except requests.ConnectionError:
            pass
        else:
            return True
        time.sleep(0.1)
        now = time.time()
    return False


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run(cmd):
    args = shlex.split(cmd)
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.fail(proc.stderr, pytrace=False)
