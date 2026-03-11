# Server Cron jobs

## Creating a new Cron
All crons are loaded once a second from the `cron` subfolder of the server. Each cronfile must be prefixed with `cron_`, otherwise it will not be registered.
A valid cronjob is inherited from `cron.cron.Base`, and implemented.

The cron job will be instantiated right before it is run. If you want to make requests, the `async_run` function has an `aiohttp` session object passed in with
pre-registered auth headers.

Only one cron job will be loaded from each file. It is not guaranteed the same cron will be loaded every time

## Interfacing with POTBOT
You cannot communicate with POTBOT directly. Instead, all messages must be sent as a `POST` to `/api/v1/realtime`. View that endpoints documentation for more
information.
