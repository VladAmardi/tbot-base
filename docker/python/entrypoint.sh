#!/usr/bin/env bash

set -x
set -e

function fix_linux_internal_host() {
  DOCKER_INTERNAL_HOST="host.docker.internal"

  if ! grep $DOCKER_INTERNAL_HOST /etc/hosts > /dev/null ; then
    DOCKER_INTERNAL_IP=$(getent hosts docker.for.mac.host.internal | awk '{ print $1 }')
    if [ -z "$DOCKER_INTERNAL_IP" ]
    then
      DOCKER_INTERNAL_IP=$(/sbin/ip route | awk '/default/ { print $3 }' | awk '!seen[$0]++')
    fi
    echo -e "$DOCKER_INTERNAL_IP\t$DOCKER_INTERNAL_HOST" | tee -a /etc/hosts > /dev/null
    echo "Added $DOCKER_INTERNAL_HOST to hosts /etc/hosts"
  fi
}

# shellcheck disable=SC2046
if [ $(ping host.docker.internal -c 1 2>&1 | grep -c 'Name or service not known') -gt 0 ]; then fix_linux_internal_host; fi;

# [...] some other things you may want in your entrypoint
# Make sure you use the same magic as the FROM php:whatever you are using such as:
# https://github.com/docker-library/php/blob/master/7.3-rc/stretch/apache/docker-php-entrypoint
# https://github.com/docker-library/php/blob/master/7.3-rc/stretch/cli/docker-php-entrypoint
exec "$@"
