#!/bin/bash

# Check if Google Chrome is already installed
if [ -x "$(command -v google-chrome)" ]; then
  installed_version=$(google-chrome --version | awk '{print $3}')
  echo "Google Chrome is already installed (Version $installed_version)."
  exit 0
fi

# Download and install Google Chrome
chrome_version="107.0.0.0"  # Replace with the desired version
download_url="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

# Download the .deb package
wget "$download_url" -O /tmp/google-chrome.deb

# Install the downloaded package
sudo dpkg -i /tmp/google-chrome.deb

# Install any missing dependencies
sudo apt-get install -f

# Check if the installation was successful
if [ -x "$(command -v google-chrome)" ]; then
  installed_version=$(google-chrome --version | awk '{print $3}')
  echo "Google Chrome $installed_version has been installed."
  exit 0
else
  echo "Failed to install Google Chrome."
  exit 1
fi
