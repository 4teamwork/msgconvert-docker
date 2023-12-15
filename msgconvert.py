#!/usr/bin/env python3
"""
msgconvert server

A tiny aiohttp based web server that wraps the msgconvert Perl script.
It expects a multipart/form-data upload containing a .msg file with the name
msg and returns the converted eml file.
"""
from aiohttp import web
import asyncio
import tempfile
import os.path
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
        return web.Response(status=400, text="Multipart request required.")

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

            res = await run(
                'msgconvert', '--outfile', outfilename, form_data['msg'].encode(),
                timeout=request.app['config']['call_timeout'],
            )

            if res is not None and res.returncode == 0:
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
                if res is None:
                    logger.error('Conversion failed.')
                    return web.Response(
                        status=500, text='Conversion failed.')

                else:
                    logger.error('Conversion failed. %s', res.stderr)
                    return web.Response(
                        status=500, text=f"Conversion failed. {res.stderr}")

    logger.info('Bad request. No msg provided.')
    return web.Response(status=400, text="No msg provided.")


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
    return web.Response(status=200, text="OK")


async def run(*cmd, input=None, timeout=30):
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input), timeout=timeout)
    except asyncio.exceptions.TimeoutError:
        logger.error('Calling %s timed out.', cmd)
        return None
    except Exception:
        logger.exception('Calling %s failed', cmd)
        return None

    return proc


def get_config():
    config = {}

    try:
        call_timeout = int(os.environ.get('MSGCONVERT_CALL_TIMEOUT', '30'))
    except (ValueError, TypeError):
        call_timeout = 30
    config['call_timeout'] = call_timeout

    return config


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        level=logging.INFO,
    )
    app = web.Application()
    app['config'] = get_config()
    logger.info('Using config=%s', app['config'])
    app.add_routes([web.post('/', msgconvert)])
    app.add_routes([web.get('/healthcheck', healthcheck)])
    web.run_app(app)
