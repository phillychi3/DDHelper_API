cd images
waitress-serve --listen=*:8000 server.wsgi:application
pause