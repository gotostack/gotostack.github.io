..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Layer 3 IPs rate limit
======================

blueprint: https://blueprints.launchpad.net/neutron/+spec/layer-3-rate-limit

RFE: https://bugs.launchpad.net/neutron/+bug/1596611

Flyer 3 IP bandwidth is unrestricted now. But the NIC and the DC export of
data center may have a limitation for a cloud deployment. Then layer 3 IPs
rate limit is needed.

This spec describes how to add a buld-in extension to limit the layer 3 IPs
bandwidth.


Problem Description
===================

Neutron now has layer 3 IPs: floating IP and router gateway IP, which bandwidth
is not restricted, then here are several reasons for adding rate limit to layer
3 IPs:

* (a) Currently, neutron qos implementation only affects neutron ports, more
  detail is that the bandwidth restriction is based on the OVS port, so all
  the VM traffic will be limited under that restriction, including l3 traffic.

* (b) North/South traffic always rely on infrastructure networking capacity.

* (c) Floating IP traffic, Cloud deployment does not have such bandwidth to meet
  the total bandwith requirement of all tenants at same time, then the SLA of
  user networing traffic cloud not guarantee. For instance, base on (a), So if
  give VM NICs a high qos value, the export of DC will get busy, one day with
  the increased floating IP, it will not meet demand. If a lower value, the
  Ease/West traffic may not happy.

* (d) SNAT traffic in centralized network node will not meet the needs of all
  tenant bandwidth. A network node NIC has one limit bandwidth.


Proposed Change
===============

Overview
--------
We want to limit the bandwith of floating IP and router gateway (SNAT traffic).
At the same time, the ease/west traffic should have no affect.

In order to make the implementation simple and efficient, we need to make the
following agreement:

* The minimum unit of the floating rate/bandwidth is Mbps, aka a floating IP
  will have a minimum bandwidth 1Mbps.

* The ingress and egress traffic will have a equal bandwidth value.

* A value of 0 will be avaliable only for admin users, then it implicitly means
  not to limit a floating IP traffic.

How the change works:

* Linux TC(Traffic Control) [1]_ will be used to implement such functionality.
  And for egress traffic a HTB [2]_ tc filter will be used to limit the floating
  IP outgoing bandwidth.

Where to install the TC rules:

* For HA/legacy routers, rules will be installed into network node qouter
  namespace, and the traffice control device is qg-device.

* For DVR routers, it's compute node qouter namespace, but the traffice control
  device is rfp-device (one of qrouter-namespace to fip-namespace pair).

Solution Proposed
-----------------

Floating IP
+++++++++++
* 1. User create a floating IP with ``rate_limit``.
* 2. Floating IP is binded to a port.
* 3. L3 agent process the router and it's floating IPs.
* 4. L3 agent set the TC rules to the qrouter-namespace relevant device.

After this the floating IP is under a bandwidth restriction. Proposed CLI:

::

  $ neutron floatingip-create --rate-limit 10 public
  Created a new floatingip:
  +---------------------+--------------------------------------+
  | Field               | Value                                |
  +---------------------+--------------------------------------+
  | description         |                                      |
  | dns_domain          |                                      |
  | dns_name            |                                      |
  | fixed_ip_address    |                                      |
  | floating_ip_address | 172.16.6.171                         |
  | floating_network_id | 2cad629d-e523-4b83-90b9-c0cc0ba1250d |
  | id                  | 87a6bd65-dca8-4520-97ed-f82d05c0a57f |
  | name                |                                      |
  | port_id             |                                      |
  | rate_limit          | 10                                   |
  | router_id           |                                      |
  | status              | DOWN                                 |
  | tenant_id           | 5ff1da9c235c4ebcaefeecf3fff7eb11     |
  +---------------------+--------------------------------------+

  $ neutron port-create 9826c8f0-3269-4546-a333-49d31046edcd
  Created a new port:
  +-----------------------+---------------------------------------------------------------------------------------+
  | Field                 | Value                                                                                 |
  +-----------------------+---------------------------------------------------------------------------------------+
  | admin_state_up        | True                                                                                  |
  | allowed_address_pairs |                                                                                       |
  | binding:host_id       |                                                                                       |
  | binding:profile       | {}                                                                                    |
  | binding:vif_details   | {}                                                                                    |
  | binding:vif_type      | unbound                                                                               |
  | binding:vnic_type     | normal                                                                                |
  | created_at            | 2016-09-21T05:13:16                                                                   |
  | description           |                                                                                       |
  | device_id             |                                                                                       |
  | device_owner          |                                                                                       |
  | dns_name              |                                                                                       |
  | extra_dhcp_opts       |                                                                                       |
  | fixed_ips             | {"subnet_id": "b7006a22-0f6e-4911-a6bc-156bcd7e8a7f", "ip_address": "192.168.199.24"} |
  | id                    | 4b79988f-ede4-478a-88e5-2443cac203dc                                                  |
  | mac_address           | fa:16:3e:41:20:a8                                                                     |
  | name                  |                                                                                       |
  | network_id            | 9826c8f0-3269-4546-a333-49d31046edcd                                                  |
  | port_security_enabled | True                                                                                  |
  | security_groups       | d3ebbd92-c127-4a7f-b9e9-15fb92c5b781                                                  |
  | status                | DOWN                                                                                  |
  | tenant_id             | 5ff1da9c235c4ebcaefeecf3fff7eb11                                                      |
  | updated_at            | 2016-09-21T05:13:16                                                                   |
  +-----------------------+---------------------------------------------------------------------------------------+

  $ neutron floatingip-associate 87a6bd65-dca8-4520-97ed-f82d05c0a57f 4b79988f-ede4-478a-88e5-2443cac203dc
  Associated floating IP 87a6bd65-dca8-4520-97ed-f82d05c0a57f

Router Gateway IP
+++++++++++++++++
* 1. Create router gateway with the ``rate_limit`` attibutes.
* 2. L3 agent process the router and it's gateway IPs.
* 3. L3 agent set the TC rules to the qrouter-namespace(snat ns) relevant device.

After this the router gateway (SNAT traffic) is under a bandwidth restriction.
Proposed CLI:

::

  $ neutron router-create test
  Created a new router:
  +-------------------------+--------------------------------------+
  | Field                   | Value                                |
  +-------------------------+--------------------------------------+
  | admin_state_up          | True                                 |
  | availability_zone_hints |                                      |
  | availability_zones      |                                      |
  | description             |                                      |
  | distributed             | True                                 |
  | external_gateway_info   |                                      |
  | ha                      | True                                 |
  | id                      | 3d13b85b-e999-49e3-a336-6d549253d651 |
  | name                    | test                                 |
  | routes                  |                                      |
  | status                  | ACTIVE                               |
  | tenant_id               | 5ff1da9c235c4ebcaefeecf3fff7eb11     |
  +-------------------------+--------------------------------------+

  $ neutron router-gateway-set --rate-limit 10 3d13b85b-e999-49e3-a336-6d549253d651 public
  Set gateway for router 3d13b85b-e999-49e3-a336-6d549253d651

  $ neutron router-show 3d13b85b-e999-49e3-a336-6d549253d651
  +-------------------------+------------------------------------------------------------------------------+
  | Field                   | Value                                                                        |
  +-------------------------+------------------------------------------------------------------------------+
  | admin_state_up          | True                                                                         |
  | availability_zone_hints |                                                                              |
  | availability_zones      | zone-2                                                                       |
  |                         | zone-1                                                                       |
  | description             |                                                                              |
  | distributed             | True                                                                         |
  | external_gateway_info   | {"network_id": "2cad629d-e523-4b83-90b9-c0cc0ba1250d", "enable_snat": true,  |
  |                         | "rate_limit": 10, "external_fixed_ips": [{"subnet_id":                       |
  |                         | "2a76489a-3717-44a5-8218-e0d20182ec2f", "ip_address": "172.16.6.172"}]}      |
  | ha                      | True                                                                         |
  | id                      | 3d13b85b-e999-49e3-a336-6d549253d651                                         |
  | name                    | test                                                                         |
  | routes                  |                                                                              |
  | status                  | ACTIVE                                                                       |
  | tenant_id               | 5ff1da9c235c4ebcaefeecf3fff7eb11                                             |
  +-------------------------+------------------------------------------------------------------------------+

Example L3 agent side TC rules
------------------------------
Assuming that we have a legacy router: cf6951cb-b050-4543-9742-c63a4989edae,
gateway ip: 172.16.6.167, 1Mbps, floating IP: 172.16.10.69, 1Mbps, then in
its scheduled network node you can get the flollowing rules:

::

  [root@network2 ~]# ip netns exec qrouter-cf6951cb-b050-4543-9742-c63a4989edae ip a
  1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
      link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
      inet 127.0.0.1/8 scope host lo
         valid_lft forever preferred_lft forever
      inet6 ::1/128 scope host
         valid_lft forever preferred_lft forever
  140: qr-4aba9b05-36: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN
      link/ether fa:16:3e:24:37:7c brd ff:ff:ff:ff:ff:ff
      inet 192.168.233.1/24 brd 192.168.233.255 scope global qr-4aba9b05-36
         valid_lft forever preferred_lft forever
      inet6 fe80::f816:3eff:fe24:377c/64 scope link
         valid_lft forever preferred_lft forever
  141: qr-aef0d42d-f9: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN
      link/ether fa:16:3e:4d:93:52 brd ff:ff:ff:ff:ff:ff
      inet 192.168.232.1/24 brd 192.168.232.255 scope global qr-aef0d42d-f9
         valid_lft forever preferred_lft forever
      inet6 fe80::f816:3eff:fe4d:9352/64 scope link
         valid_lft forever preferred_lft forever
  143: qg-c99a5832-7f: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc htb state UNKNOWN
      link/ether fa:16:3e:f1:2b:41 brd ff:ff:ff:ff:ff:ff
      inet 172.16.6.167/16 brd 172.16.255.255 scope global qg-c99a5832-7f
         valid_lft forever preferred_lft forever
      inet 172.16.10.69/32 brd 172.16.10.69 scope global qg-c99a5832-7f
         valid_lft forever preferred_lft forever
      inet6 fe80::f816:3eff:fef1:2b41/64 scope link
         valid_lft forever preferred_lft forever

  [root@network2 ~]# ip netns exec qrouter-cf6951cb-b050-4543-9742-c63a4989edae tc qdisc show dev qg-c99a5832-7f
  qdisc htb 801b: root refcnt 2 r2q 10 default 0 direct_packets_stat 400
  qdisc ingress ffff: parent ffff:fff1 ----------------

  [root@network2 ~]# ip netns exec qrouter-cf6951cb-b050-4543-9742-c63a4989edae tc -s -d -p filter show dev qg-c99a5832-7f parent 801b:
  filter protocol ip pref 1 u32
  filter protocol ip pref 1 u32 fh 800: ht divisor 1
  filter protocol ip pref 1 u32 fh 800::800 order 2048 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP src 172.16.6.167/32 (success 0 )
   police 0xa74 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)
  filter protocol ip pref 1 u32 fh 800::801 order 2049 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP src 172.16.10.69/32 (success 0 )
   police 0xa76 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)

  [root@network2 ~]# ip netns exec qrouter-cf6951cb-b050-4543-9742-c63a4989edae tc -s -d -p filter show dev qg-c99a5832-7f parent ffff:
  filter protocol ip pref 1 u32
  filter protocol ip pref 1 u32 fh 800: ht divisor 1
  filter protocol ip pref 1 u32 fh 800::800 order 2048 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP dst 172.16.6.167/32 (success 0 )
   police 0xa73 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)
  filter protocol ip pref 1 u32 fh 800::801 order 2049 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP dst 172.16.10.69/32 (success 0 )
   police 0xa75 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)

And DVR router 0580788c-c919-447c-aea1-87d415aa173a with floating IP
172.16.6.161 1Mbps in a compute node:

::

  [root@compute2 ~]# ip netns exec qrouter-0580788c-c919-447c-aea1-87d415aa173a ip a
  1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
      link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
      inet 127.0.0.1/8 scope host lo
         valid_lft forever preferred_lft forever
      inet6 ::1/128 scope host
         valid_lft forever preferred_lft forever
  24: rfp-0580788c-c: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc htb state UP qlen 1000
      link/ether 3e:e6:97:2e:66:c3 brd ff:ff:ff:ff:ff:ff link-netnsid 0
      inet 169.254.106.114/31 scope global rfp-0580788c-c
         valid_lft forever preferred_lft forever
      inet 172.16.6.161/32 brd 172.16.6.161 scope global rfp-0580788c-c
         valid_lft forever preferred_lft forever
      inet6 fe80::3ce6:97ff:fe2e:66c3/64 scope link
         valid_lft forever preferred_lft forever
  102: qr-43185e93-af: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN
      link/ether fa:16:3e:95:ba:81 brd ff:ff:ff:ff:ff:ff
      inet 192.168.199.1/24 brd 192.168.199.255 scope global qr-43185e93-af
         valid_lft forever preferred_lft forever
      inet6 fe80::f816:3eff:fe95:ba81/64 scope link
         valid_lft forever preferred_lft forever
  104: qr-51635a61-46: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN
      link/ether fa:16:3e:ed:b1:5b brd ff:ff:ff:ff:ff:ff
      inet 192.168.198.1/24 brd 192.168.198.255 scope global qr-51635a61-46
         valid_lft forever preferred_lft forever
      inet6 fe80::f816:3eff:feed:b15b/64 scope link
         valid_lft forever preferred_lft forever
  [root@compute2 ~]# ip netns exec qrouter-0580788c-c919-447c-aea1-87d415aa173a tc qdisc show dev rfp-0580788c-c
  qdisc htb 801e: root refcnt 2 r2q 10 default 0 direct_packets_stat 5
  qdisc ingress ffff: parent ffff:fff1 ----------------
  [root@compute2 ~]# ip netns exec qrouter-0580788c-c919-447c-aea1-87d415aa173a tc -s -d -p filter show dev rfp-0580788c-c parent 801e:
  filter protocol ip pref 1 u32
  filter protocol ip pref 1 u32 fh 800: ht divisor 1
  filter protocol ip pref 1 u32 fh 800::800 order 2048 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP src 172.16.6.161/32 (success 0 )
   police 0x68 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)
  [root@compute2 ~]# ip netns exec qrouter-0580788c-c919-447c-aea1-87d415aa173a tc -s -d -p filter show dev rfp-0580788c-c parent ffff:
  filter protocol ip pref 1 u32
  filter protocol ip pref 1 u32 fh 800: ht divisor 1
  filter protocol ip pref 1 u32 fh 800::800 order 2048 key ht 800 bkt 0 flowid :1  (rule hit 0 success 0)
    match IP dst 172.16.6.161/32 (success 0 )
   police 0x67 rate 1000Kbit burst 1Mb mtu 64Kb action drop overhead 0b
  ref 1 bind 1

   Sent 0 bytes 0 pkts (dropped 0, overlimits 0)


IPv6 Impact
-----------
IPv6 will not be considerd in this spec, rate limit for IP v6 may need some
other solutions.

Data Model Impact
-----------------
New properties will be added to floating IP model or extra attributes table,
one optional name is ``rate_limit``. And may aslo for ``routerports`` table.

REST API Impact
---------------
New API extention for floating IP ``rate_limit`` creating/updating API. System
administrator may need to set a default value of the ``rate_limit`` when user
does not supply it.

``ext-gw-mode`` extention will also be influenced to add a new param for
set_router_gateway API.


Implementation
==============

Work Items
----------

* Modify model tables and API resources.
* New TC command wrapper for layer 3 IPs rate limit.
* L3 agent side tc rule installation.
* CLI support.
* Testing.
* Documentation.

Dependencies
============

None

Testing
=======

Functionality
-------------
The bandwidth of layer 3 IPs should be restricted properly.
Use some commands, such as `scp`, to test the bandwith of ingress and egress.

Upgrading
---------
Upgrading test may need to see all the layer 3 IPs are limited to the default
bandwidth.


References
==========

.. [1] `Linux Traffic Control <http://www.tldp.org/HOWTO/Traffic-Control-HOWTO>`_

.. [2] `Linux HTB Queuing <http://www.linuxjournal.com/article/7562>`_

