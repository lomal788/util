#!/bin/sh
# Redirect only the boiler's cloud host; every other name goes to the upstream DNS.
set -eu
cat > /etc/dnsmasq.conf <<EOF
no-resolv
no-hosts
# Naming the interface turns off dnsmasq's default "local-service" filter, which
# would otherwise drop LAN clients whose queries arrive through Docker's port mapping.
interface=eth0
server=${UPSTREAM_DNS_1}
server=${UPSTREAM_DNS_2}
# local= keeps every record type for this name in-house (AAAA must not leak the real cloud)
local=/krst2.naviensmartcontrol.com/
address=/krst2.naviensmartcontrol.com/${HOST_IP}
cache-size=1000
log-facility=-
EOF
exec dnsmasq --keep-in-foreground --conf-file=/etc/dnsmasq.conf
