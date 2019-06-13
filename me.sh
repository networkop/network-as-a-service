#!/bin/sh
wget -O- --post-data='{"devices":["all"]}' --header='Content-Type:application/json' http://api.naas/configure
