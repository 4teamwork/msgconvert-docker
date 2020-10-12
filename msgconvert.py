#!/usr/bin/env python3
"""
msgconvert server

A tiny aiohttp based web server that wraps the msgconvert Perl script.
It expects a multipart/form-data upload containing a .msg file with the name
msg and returns the converted eml file.
"""
from aiohttp import web
from tempfile import mkdtemp
import os.path
import subprocess
import shutil

CHUNK_SIZE = 65536


async def msgconvert(request):

    filename = None
    temp_dir = None

    if not request.content_type == 'multipart/form-data':
        return web.Response(status=400, text=f"Multipart request required.")

    reader = await request.multipart()
    while True:
        part = await reader.next()

        if part is None:
            break

        if part.name == 'msg':
            temp_dir = mkdtemp()
            filename = os.path.join(temp_dir, part.filename)
            with open(os.path.join(temp_dir, filename), 'wb') as msg_file:
                while True:
                    chunk = await part.read_chunk(CHUNK_SIZE)
                    if not chunk:
                        break
                    msg_file.write(chunk)

    if filename is not None:
        outfilename = os.path.join(
            os.path.dirname(filename), os.path.basename(filename) + '.eml')
        res = subprocess.run(
            ['msgconvert', '--outfile', outfilename, filename],
            capture_output=True,
            text=True,
        )

        if res.returncode == 0:
            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={'Content-Type': 'message/rfc822'},
            )
            await response.prepare(request)

            with open(outfilename, 'rb') as outfile:
                while True:
                    data = outfile.read(CHUNK_SIZE)
                    if not data:
                        break
                    await response.write(data)

            await response.write_eof()
            shutil.rmtree(temp_dir)
            return response
        else:
            shutil.rmtree(temp_dir)
            return web.Response(
                status=500, text=f"Conversion failed. {res.stderr}")

    return web.Response(status=400, text=f"No msg provided.")


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.post('/', msgconvert)])
    web.run_app(app)
