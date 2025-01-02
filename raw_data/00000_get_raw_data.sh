#!/bin/bash

MODELS=("H6066" "H61A8")

for MODEL in "${MODELS[@]}"; do

	# Set filename with date

	FILENAME=${MODEL}_`date +%F`_scenes_raw.json

	# Pull the scene data from Govee. The publicly available (no-key-required) API works. Write to data to $FILENAME

	curl "https://app2.govee.com/appsku/v1/light-effect-libraries?sku=${MODEL}" -H 'AppVersion: 9999999' -s > ${FILENAME}

	############
	# Make raw data "pretty" =

	rm -f pretty_temp.json
	jq . <${FILENAME} >pretty_temp.json
	mv pretty_temp.json ${FILENAME}

done
