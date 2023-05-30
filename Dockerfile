FROM python:3.8 AS webserver

WORKDIR /app/oppia

# installing the pre-requisites
RUN apt-get update && apt-get upgrade
RUN apt-get -y install curl
RUN apt-get -y install git
# RUN apt-get -y install software-properties-common
# RUN apt-get update
# RUN add-apk-repository ppa:webupd8team/java
# RUN apt-get install openjdk-8-jre
# TODO: install openjdk-8-jre (ps: I am using python:3.8 base image that is implemented on Debian10 - and openjdk-8 is not avaialble on Debian10).

RUN apt-get -y install python3-dev
RUN apt-get -y install python3-setuptools
RUN apt-get -y install python3-pip
RUN apt-get -y install unzip
RUN apt-get -y install python3-yaml
# RUN apt-get -y install python-matplotlib
RUN apt-get -y install python3-matplotlib
RUN pip install --upgrade pip==21.2.3
# RUN npm install -g yarn

RUN pip install pip-tools==6.6.2
RUN pip install setuptools==58.5.3

# installing python dependencies from the requirements.txt file
COPY requirements.in .
COPY requirements.txt .
COPY requirements_dev.in .
COPY requirements_dev.txt .

RUN pip-compile --generate-hashes requirements.in
RUN pip-compile --generate-hashes requirements_dev.in
RUN pip install cmake
# TODO: not installing pyarrow for now as facing problem while installing in my M1: refer - https://github.com/streamlit/streamlit/issues/2774
RUN pip install --require-hashes --no-deps -r requirements.txt
RUN pip install --require-hashes --no-deps -r requirements_dev.txt

## installing packages from the package.json file
COPY package.json .
COPY scripts/linters/custom_eslint_checks ./scripts/linters/custom_eslint_checks
RUN apt-get -y install npm

RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs
RUN apt-get -y install chromium

RUN npm install -g yarn
RUN yarn install
# RUN npm install --legacy-peer-deps

RUN apt-get -y install python2
COPY . .

EXPOSE 8181
# RUN ./node_modules/.bin/ng build --watch
CMD ["./node_modules/.bin/ng", "build", "--watch"]

# STAGE 2 for webpack bundling
FROM webserver AS webpack-compiler

WORKDIR /app/oppia

# COPY . .

CMD ["node", "./node_modules/webpack/bin/webpack.js", "--config", "webpack.dev.config.ts", "--watch"]
# TODO: tasks for the day: 1) find a way how to run these 2 live processes in this dockerfile? 2) install the packages from the dependencies.json! 3) connect with google cloud sdk, and launch app.
# RUN ./node_modules/.bin/ng build --watch
# RUN node ./node_modules/webpack/bin/webpack.js --config webpack.dev.config.ts --watch

# CMD ["./node_modules/webpack/bin/webpack.js --config webpack.dev.config.ts --watch;./node_modules/.bin/ng build --watch"]
# CMD [ "node_modules/.bin/ng", "serve", "--host", "0.0.0.0" ]
#
## NOTE :
## I am currently skipping the frontend build and the webpack compilation steps --
## (using the pre-built files in this prototype)
## command for compiling the webpack bundles: ./node_modules/webpack/bin/webpack.js --config webpack.dev.config.ts
## command for building the frontend application: ./node_modules/.bin/ng build --host 0.0.0.0

## NOTE:
## I am using Google App Engine to serve our app in to the browser (by serving the built webpack bundles) using
## the `app_dev.yaml` file. For the prototype to work, I am using the already installed `Google Cloud SDK- 364.0.0`
## from the /oppia-tools directory (copied to our root directory). This is a temporary solution,
## and I will be using the official docker image for the google cloud SDK while working in the GSoC project
## [link for the verified Google Cloud SDK image](https://hub.docker.com/r/google/cloud-sdk).
# CMD [ "./oppia_tools/google-cloud-sdk-364.0.0/google-cloud-sdk/bin/dev_appserver.py", "app_dev.yaml", "--runtime", "python38", "--host", "0.0.0.0"]