#!/bin/bash
[ ! -d /dev/net ] && mkdir /dev/net
mknod /dev/net/tun c 10 200 > /dev/null 2>&1
openvpn --config /ovpn-server.conf &
while ! ip li sh tap0 > /dev/null 2>&1; do sleep 1; done
ip li set tap0 up
addr="`ip -br ad sh "$1" | awk '{ print $3 }'`"
ip addr fl "$1"
brctl addbr br0
brctl addif br0 "$1"
brctl addif br0 tap0
ip addr add "$addr" dev br0
ip li set br0 up