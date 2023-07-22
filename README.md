To run:

Install Docker, then build the container locally:

`docker build -t <container-name>`

(Use your own container name)

Then run the container from a folder where you want the data to be dumped:

docker run -v ${PWD}/app:/app <container-name>
