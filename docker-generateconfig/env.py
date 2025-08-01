#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

cfg = {
    'inputFile': '.env.default',
    'overrideFile': '.env.override',
    'outputFile': '.env',
    'overrideVarMap': {
        'ANY_SYNC_NODE_VERSION': 'pkg::any-sync-node',
        'ANY_SYNC_FILENODE_VERSION': 'pkg::any-sync-filenode',
        'ANY_SYNC_COORDINATOR_VERSION': 'pkg::any-sync-coordinator',
        'ANY_SYNC_CONSENSUSNODE_VERSION': 'pkg::any-sync-consensusnode',
    },
    'versionsUrlMap': {
        'prod': 'https://puppetdoc.anytype.io/api/v1/prod-any-sync-compatible-versions/',
        'stage1': 'https://puppetdoc.anytype.io/api/v1/stage1-any-sync-compatible-versions/',
    },
    'outputFileHeader': '''# !!! PLEASE DO NOT EDIT THIS FILE !!!
# To make changes to the '.env', use the '.env.override' file
# https://github.com/anyproto/any-sync-dockercompose/wiki/Configuration

''',
}

# load variables from inputFile
logging.info(f"Loading variables from input file: {cfg['inputFile']}")
envVars = dict()
if os.path.exists(cfg['inputFile']) and os.path.getsize(cfg['inputFile']) > 0:
    with open(cfg['inputFile']) as file:
        for line in file:
            if line.startswith('#') or not line.strip():
                continue
            key, value = line.strip().split('=', 1)
            if key in envVars:
                logging.warning(f"Duplicate key={key} in env file={cfg['inputFile']}")
            envVars[key] = value
    logging.info(f"Loaded {len(envVars)} variables from {cfg['inputFile']}")
else:
    logging.error(f"File={cfg['inputFile']} not found or size=0")
    exit(1)

# override variables from overrideFile
if os.path.exists(cfg['overrideFile']) and os.path.getsize(cfg['overrideFile']) > 0:
    logging.info(f"Loading override variables from: {cfg['overrideFile']}")
    override_count = 0
    with open(cfg['overrideFile']) as file:
        for line in file:
            if line.startswith('#') or not line.strip():
                continue
            key, value = line.strip().split('=', 1)
            if key in envVars:
                logging.info(f"Overriding {key}: {envVars[key]} -> {value}")
            else:
                logging.info(f"Adding new variable {key}={value}")
            envVars[key] = value
            override_count += 1
    logging.info(f"Applied {override_count} overrides from {cfg['overrideFile']}")
else:
    logging.info(f"No override file found at {cfg['overrideFile']} or file is empty")

# api request
def apiRequest(url):
    logging.info(f"Making API request to: {url}")
    try:
        response = requests.get(url, timeout=(3.05, 5))
        jsonResponse = response.json()
        logging.info(f"API request successful, received {len(jsonResponse)} items")
    except Exception as e:
        logging.error(f"Failed response url={url}, error={str(e)}")
        exit(1)
    if response.status_code != 200:
        logging.error(f"Failed response url={url}, status_code={response.status_code}, text={response.text}")
        exit(1)
    return jsonResponse

# get latest version
def getLatestVersions(role):
    logging.info(f"Getting latest versions for role: {role}")
    versions = apiRequest(cfg['versionsUrlMap'][role])
    sortedVersions = dict(sorted(versions.items(), key=lambda x: int(x[0])))
    lastVersionsTimestamp, lastVersions = next(reversed(sortedVersions.items()))
    logging.info(f"Latest versions timestamp: {lastVersionsTimestamp}, found {len(lastVersions)} packages")
    return lastVersions

# process variables
logging.info("Processing variables for version updates")
updated_count = 0
for key,value in envVars.items():
    if key in cfg['overrideVarMap'].keys():
        logging.info(f"Processing version variable: {key}={value}")
        if value in cfg['versionsUrlMap'].keys():
            latestVersions = getLatestVersions(value)
            lastVersionKey = cfg['overrideVarMap'].get(key)
            lastVersionValue = latestVersions.get(lastVersionKey)
            if lastVersionKey and lastVersionValue:
                old_value = envVars[key]
                envVars[key] = 'v'+str(lastVersionValue)
                logging.info(f"Updated {key}: {old_value} -> {envVars[key]}")
                updated_count += 1
            else:
                logging.warning(f"Could not find version for {lastVersionKey} in latest versions")
        else:
            logging.info(f"Skipping {key}={value} (not in versions URL map)")
logging.info(f"Updated {updated_count} version variables")

# save in output file
logging.info(f"Writing {len(envVars)} variables to output file: {cfg['outputFile']}")
with open(cfg['outputFile'], 'w') as file:
    file.write(cfg['outputFileHeader'])
    for key, value in envVars.items():
        file.write(f"{key}={value}\n")
logging.info(f"Successfully generated {cfg['outputFile']} with {len(envVars)} variables")
