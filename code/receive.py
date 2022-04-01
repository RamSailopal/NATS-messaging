import argparse
import asyncio
import os
import signal
import sys

import nats


def show_usage():
    usage = """
nats-pub [-s SERVER] <subject>
Example:
nats-sub -s demo.nats.io help -q workers 
"""
    print(usage)


def show_usage_and_die():
    show_usage()
    sys.exit(1)


async def run():
    parser = argparse.ArgumentParser()

    # e.g. nats-sub hello -s nats://nats:4222
    parser.add_argument('subject', default='hello', nargs='?')
    parser.add_argument('-s', '--servers', default="")
    parser.add_argument('-q', '--queue', default="")
    parser.add_argument('--creds', default="")
    args = parser.parse_args()

    async def error_cb(e):
        print("Error:", e)

    async def closed_cb():
        # Wait for tasks to stop otherwise get a warning.
        await asyncio.sleep(0.2)
        loop.stop()

    async def reconnected_cb():
        print(f"Connected to NATS at {nc.connected_url.netloc}...")

    async def subscribe_handler(msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print(
            "Received a message on '{subject} {reply}': {data}".format(
                subject=subject, reply=reply, data=data
            )
        )

    options = {
        "error_cb": error_cb,
        "closed_cb": closed_cb,
        "reconnected_cb": reconnected_cb
    }

    if len(args.creds) > 0:
        options["user_credentials"] = args.creds

    nc = None
    try:
        if len(args.servers) > 0:
            options['servers'] = args.servers

        nc = await nats.connect(**options)
    except Exception as e:
        print(e)
        show_usage_and_die()

    print(f"Listening on [{args.subject}]")

    def signal_handler():
        if nc.is_closed:
            return
        asyncio.create_task(nc.drain())

    for sig in ('SIGINT', 'SIGTERM'):
        asyncio.get_running_loop().add_signal_handler(getattr(signal, sig), signal_handler)

    await nc.subscribe(args.subject, args.queue, subscribe_handler)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    try:
        loop.run_forever()
    finally:
        loop.close()
