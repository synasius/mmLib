#!/usr/bin/env python

## TLS Motion Determination (TLSMD)
## Copyright 200-20052 by TLSMD Development Group (see AUTHORS file)
## This code is part of the TLSMD distribution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.

import os
import sys
import time
import socket

import xmlrpclib

from tlsmdlib import const, conf

SECS_IN_DAY = float(60*60*24)
DELETE_DAYS = 12

## GLOBALS
webtlsmdd = xmlrpclib.ServerProxy(conf.WEBTLSMDD)

def check_remove(jdict):
    state = jdict.get("state")
    if state==None:
        print "[ERROR] job_id=%s has no state" % (jdict["job_id"])
	return False

    submit_time = jdict.get("submit_time")
    if submit_time==None:
        return False

    email = jdict.get("email")
    if email: pass

    days = round((time.time() - submit_time) / SECS_IN_DAY)
    jdict["days"] = days
   
    if days>DELETE_DAYS:
        return True

    if state=="submit1" and days>1:
        return True

    return False

def main():
    print "WebTLSMD Job Cleanup: Checking database for old jobs to remove."

    job_list = webtlsmdd.job_list()
    jdict_remove_list = []

    for jdict in job_list:
        if check_remove(jdict):
            jdict_remove_list.append(jdict)

    for jdict in jdict_remove_list:
        print "%10s  %40s  %d Days Old" % (jdict["job_id"], jdict.get("email", "No Email"), jdict["days"])
        webtlsmdd.remove_job(jdict["job_id"])


if __name__=="__main__":
    main()
