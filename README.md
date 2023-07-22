To run:

Install Docker, then build the container locally:

`docker build -t <container-name>`

(Use your own container name)

Then run the container from the folder that contains the app folder:

`docker run -v ${PWD}/app:/app <container-name>`

In the above call, `-v` means to bind a volume; the local `app` directory is bound to the container's `app` folder, so that any input/output files can be accessed locally even though the container is run in isolation.
