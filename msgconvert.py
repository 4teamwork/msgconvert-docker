#!/usr/bin/env python3
"""
msgconvert server

A tiny aiohttp based web server that wraps the msgconvert Perl script.
It expects a multipart/form-data upload containing a .msg file with the name
msg and returns the converted eml file.
"""
from aiohttp import web
import tempfile
import os.path
import subprocess
import logging

CHUNK_SIZE = 65536

logger = logging.getLogger('msgconvert')


async def msgconvert(request):

    form_data = {}
    temp_dir = None

    if not request.content_type == 'multipart/form-data':
        logger.info(
            'Bad request. Received content type %s instead of multipart/form-data.',
            request.content_type,
        )
        return web.Response(status=400, text=f"Multipart request required.")

    reader = await request.multipart()

    with tempfile.TemporaryDirectory() as temp_dir:
        while True:
            part = await reader.next()

            if part is None:
                break

            if part.name == 'msg':
                form_data['msg'] = await save_part_to_file(part, temp_dir)

        if 'msg' in form_data:
            outfilename = os.path.join(
                temp_dir, os.path.basename(form_data['msg']) + '.eml')
            res = subprocess.run(
                ['msgconvert', '--outfile', outfilename, form_data['msg']],
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
                return response
            else:
                logger.error('Conversion failed. %s', res.stderr)
                return web.Response(
                    status=500, text=f"Conversion failed. {res.stderr}")

    logger.info('Bad request. No msg provided.')
    return web.Response(status=400, text=f"No msg provided.")


async def save_part_to_file(part, directory):
    filename = os.path.join(directory, part.filename)
    with open(os.path.join(directory, filename), 'wb') as file_:
        while True:
            chunk = await part.read_chunk(CHUNK_SIZE)
            if not chunk:
                break
            file_.write(chunk)
    return filename


async def healthcheck(request):
    return web.Response(status=200, text=f"OK")


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        level=logging.INFO,
    )
    app = web.Application()
    app.add_routes([web.post('/', msgconvert)])
    app.add_routes([web.get('/healthcheck', healthcheck)])
    web.run_app(app)
