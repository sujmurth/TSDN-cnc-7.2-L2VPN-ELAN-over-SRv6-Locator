# TSDN FP Update — SRv6 Locator under EVPN-MP (E-LAN) EVI

## Summary

For EVPN Multipoint (E-LAN) services, the TSDN Function Pack (FP) `cisco-L2vpn-fp-internal`
package doesnt support the SRv6 binding and the **per-EVI locator** under the top-level `evpn evi <id>` block.

As a result, the intended IOS-XR configuration:

```
evpn
 evi <id> segment-routing srv6
  advertise-mac
  locator <LOCATOR>
```

was rendered without `segment-routing srv6` and **without** `locator <LOCATOR>` under
`evpn evi`, so the SRv6 locator supplied in the service payload
(`te-service-mapping/srv6/locator`) was silently dropped for EVPN-MP services.

This document records the device-template change that closes that gap.

- **Product:** Cisco Crosswork Network Controller (CNC) — TSDN Function Pack 7.2
- **NSO:** 6.4.8 (`tsdn-7.2.0-source-code-nso-6.4.8.a83516ab`)
- **Service type:** L2NM EVPN Multipoint (E-LAN), `any-to-any`, SRv6 transport
- **Reference:** xrdocs — *SRv6 Transport on NCS5500, Part 6* (EVPN ELAN over SRv6) :https://xrdocs.io/ncs5500/tutorials/srv6-transport-on-ncs-part-6

---

## File Changed

In `packages/cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml`

### Node structure (IOS-XR CLI NED)

Under `evpn / evi`:
- `<segment-routing when="{srv6}">srv6</segment-routing>` is a **leaf** that renders `segment-routing srv6`.
- `<locator when="{srv6/locator!=''}">{srv6/locator}</locator>` is a **sibling leaf** under
  `<evi>` (NOT nested inside `segment-routing`), and renders `locator <LOCATOR>`.

Update xml as below. Refer to the package in this repository.

```
        <evpn xmlns="http://tail-f.com/ned/cisco-ios-xr">
          <evi>
            <id>{$EVI_ID}</id>
            <segment-routing when="{srv6}">srv6</segment-routing>
            <bgp>
              ...
            </bgp>
            <etree when="...">...</etree>
            <advertise-mac when="{advertise-mac/enable = 'true'}">
            </advertise-mac>
            <control-word-disable when="{control-word-disable = 'true'}">
            </control-word-disable>
            <locator when="{srv6/locator!=''}">{srv6/locator}</locator>
          </evi>

```

## Below modifications done on SVM eNSO . Can be done similarly on CNC Cluster setup 

The fix was applied to the running eNSO package copy and the package reloaded:

1. Login to CW using SSH and go to eNSO pod. Go to folder  /nso/run/packages/
   root@enso-5bdb6f7478-97mz7:/nso/run/packages# ls -ltr | grep L2
-rw------- 1 root root    170582 Mar 19 21:10 ncs-6.4.11-cisco-L2vpn-fp-internal-7.2.1.tar.gz
2. Untar this package root@enso-5bdb6f7478-97mz7:/nso/run/packages# tar -zxvf ncs-6.4.11-cisco-L2vpn-fp-internal-7.2.1.tar.gz
   ```
cisco-L2vpn-fp-internal/
cisco-L2vpn-fp-internal/CHANGES
cisco-L2vpn-fp-internal/README.md
cisco-L2vpn-fp-internal/package-meta-data.xml
cisco-L2vpn-fp-internal/python/
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/IosXR.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/__init__.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_actions.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_local_site_nano_services.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_remote_site_nano_services.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_rr_parent_route_policy.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_services.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/flat_L2vpn_site_nano_services.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/main.py
cisco-L2vpn-fp-internal/python/cisco_flat_L2vpn_fp_internal/utils.py
cisco-L2vpn-fp-internal/src/
cisco-L2vpn-fp-internal/src/yang/
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-internal-common.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-internal-local-site.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-internal-remote-site.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-internal-site.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-local-site-nano-services.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-remote-site-nano-services.yang
cisco-L2vpn-fp-internal/src/yang/cisco-flat-L2vpn-fp-site-nano-services.yang
cisco-L2vpn-fp-internal/templates/
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-vpws-template.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-p2p-template.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-routing-policy-template.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-no-shutdown-iosxr-cli.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-parent-route-policy-iosxr-cli.xml
cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-rr-parent-route-policy.xml
cisco-L2vpn-fp-internal/templates/ietf-l2nm-copy-cfp-configurations.xml
cisco-L2vpn-fp-internal/templates/ietf-l2nm-l2vpn-evpn-mp-template.xml
cisco-L2vpn-fp-internal/templates/ietf-l2nm-l2vpn-local-site-template.xml
cisco-L2vpn-fp-internal/templates/ietf-l2nm-l2vpn-macros.xml
cisco-L2vpn-fp-internal/templates/ietf-l2nm-l2vpn-remote-site-template.xml
cisco-L2vpn-fp-internal/load-dir/
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-internal-site.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-local-site-nano-services.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-internal-common.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-internal-remote-site.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-internal-local-site.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-site-nano-services.fxs
cisco-L2vpn-fp-internal/load-dir/cisco-flat-L2vpn-fp-remote-site-nano-services.fxs
cisco-L2vpn-fp-internal/build-meta-data.xml
```

3. Backup ncs-6.4.11-cisco-L2vpn-fp-internal-7.2.1.tar.gz in a tmp folder and delete the tar.gz package .As we will be modifying the untar package and reload NSO.
4. Apply the changes to this file
   `/nso/run/packages/cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml`.
5. Reloaded packages:
   ```
   echo "packages reload" | ncs_cli -u admin -C
   ```
   Result: `result true`; package `cisco-L2vpn-fp-internal` `oper-status up`.

---

## Service Payload (example)

L2NM EVPN-MP (E-LAN) over SRv6, `any-to-any`, locator `MAIN`, EVI `10165`:

```json
{
  "ietf-l2vpn-ntw:l2vpn-ntw": {
    "vpn-services": {
      "vpn-service": [
        {
          "vpn-id": "L2NM-EVPN-MP-ELAN-SRv6",
          "vpn-type": "ietf-vpn-common:mpls-evpn",
          "vpn-service-topology": "ietf-vpn-common:any-to-any",
          "vpn-nodes": {
            "vpn-node": [
              {
                "vpn-node-id": "node-10",
                "signaling-option": {
                  "evpn-policies": {
                    "mac-learning-mode": "ietf-l2vpn-ntw:control-plane"
                  }
                },
                "vpn-network-accesses": {
                  "vpn-network-access": [
                    {
                      "id": "a3",
                      "interface-id": "TenGigE0/0/0/20",
                      "connection": {
                        "encapsulation": {
                          "encap-type": "ietf-vpn-common:dot1q",
                          "dot1q": {
                            "cvlan-id": 3111,
                            "tag-operations": {
                              "pop": "1",
                              "cisco-l2vpn-ntw:mode": "symmetric"
                            }
                          }
                        }
                      }
                    }
                  ]
                },
                "cisco-l2vpn-ntw:te-service-mapping": {
                  "srv6": {
                    "locator": "MAIN"
                  }
                }
              },
              {
                "vpn-node-id": "node-16",
                "signaling-option": {
                  "evpn-policies": {
                    "mac-learning-mode": "ietf-l2vpn-ntw:control-plane"
                  }
                },
                "vpn-network-accesses": {
                  "vpn-network-access": [
                    {
                      "id": "a2",
                      "interface-id": "TenGigE0/0/0/30",
                      "connection": {
                        "encapsulation": {
                          "encap-type": "ietf-vpn-common:dot1q",
                          "dot1q": {
                            "cvlan-id": 3111,
                            "tag-operations": {
                              "pop": "1",
                              "cisco-l2vpn-ntw:mode": "symmetric"
                            }
                          }
                        }
                      }
                    }
                  ]
                },
                "cisco-l2vpn-ntw:te-service-mapping": {
                  "srv6": {
                    "locator": "MAIN"
                  }
                }
              },
              {
                "vpn-node-id": "node-5",
                "signaling-option": {
                  "evpn-policies": {
                    "mac-learning-mode": "ietf-l2vpn-ntw:control-plane"
                  }
                },
                "vpn-network-accesses": {
                  "vpn-network-access": [
                    {
                      "id": "a4",
                      "interface-id": "HundredGigE0/0/0/30",
                      "connection": {
                        "encapsulation": {
                          "encap-type": "ietf-vpn-common:dot1q",
                          "dot1q": {
                            "cvlan-id": 3110,
                            "tag-operations": {
                              "pop": "1",
                              "cisco-l2vpn-ntw:mode": "symmetric"
                            }
                          }
                        }
                      }
                    }
                  ]
                },
                "cisco-l2vpn-ntw:te-service-mapping": {
                  "srv6": {
                    "locator": "MAIN"
                  }
                }
              }
            ]
          },
          "cisco-l2vpn-ntw:evi-id": 10165,
          "cisco-l2vpn-ntw:bridge-group": "BRIDGE"
        }
      ]
    }
  }
}
```

---

## CNC  Verification (nodes node-10, node-16, node-5)




### `show evpn evi vpn-id 10165 detail`

```
## Node-10:

VPN-ID     Encap      Bridge Domain                Type               
---------- ---------- ---------------------------- -------------------
10165      SRv6       BRIDGE_evi_10165             EVPN               
   Stitching: Regular
   Unicast SID:  fcbb:0:10:e006::                       
   Multicast SID:  fcbb:0:10:e007::                       
   E-Tree: Root
   Forward-class: 0
   Advertise MACs: Yes
   Advertise BVI MACs: No
   Aliasing: Enabled
   UUF: Enabled
   Re-origination: Enabled
   Multicast:
     IGMP-Snooping Proxy: No
     MLD-Snooping Proxy : No
   BGP Implicit Import: Enabled
   VRF Name: 
   SRv6 Locator Name: MAIN
   SRv6 SID Function Length: 16 bits
   Preferred Nexthop Mode: Off
   BVI Coupled Mode: No
   BVI Subnet Withheld: ipv4 No, ipv6 No
   L3VRF Label Mode: Per-VRF
   RD Config: none
   RD Auto  : (auto) 198.19.1.10:10165
   RT Auto  : 65000:10165
   Route Targets in Use           Type                 
   ------------------------------ ---------------------
   65000:10165                    Import               
   65000:10165                    Export            

   RP/0/RP0/CPU0:node-10#

```
```
## Node-16: 

VPN-ID     Encap      Bridge Domain                Type               
---------- ---------- ---------------------------- -------------------
10165      SRv6       BRIDGE_evi_10165             EVPN               
   Stitching: Regular
   Unicast SID:  fcbb:0:16:e007::                       
   Multicast SID:  fcbb:0:16:e008::                       
   E-Tree: Root
   Forward-class: 0
   Advertise MACs: Yes
   Advertise BVI MACs: No
   Aliasing: Enabled
   UUF: Enabled
   Re-origination: Enabled
   Multicast:
     IGMP-Snooping Proxy: No
     MLD-Snooping Proxy : No
   BGP Implicit Import: Enabled
   VRF Name: 
   SRv6 Locator Name: MAIN
   SRv6 SID Function Length: 16 bits
   Preferred Nexthop Mode: Off
   BVI Coupled Mode: No
   BVI Subnet Withheld: ipv4 No, ipv6 No
   L3VRF Label Mode: Per-VRF
   RD Config: none
   RD Auto  : (auto) 198.19.1.16:10165
   RT Auto  : 65000:10165
   Route Targets in Use           Type                 
   ------------------------------ ---------------------
   65000:10165                    Import               
   65000:10165                    Export               

RP/0/RP0/CPU0:node-16#
```
```
## Node-5 

VPN-ID     Encap      Bridge Domain                Type               
---------- ---------- ---------------------------- -------------------
10165      SRv6       BRIDGE_evi_10165             EVPN               
   Stitching: Regular
   Unicast SID:  fcbb:0:5:e00b::                        
   Multicast SID:  fcbb:0:5:e00c::                        
   E-Tree: Root
   Forward-class: 0
   Advertise MACs: Yes
   Advertise BVI MACs: No
   Aliasing: Enabled
   UUF: Enabled
   Re-origination: Enabled
   Multicast:
     IGMP-Snooping Proxy: No
     MLD-Snooping Proxy : No
   BGP Implicit Import: Enabled
   VRF Name: 
   SRv6 Locator Name: MAIN
   SRv6 SID Function Length: 16 bits
   Preferred Nexthop Mode: Off
   BVI Coupled Mode: No
   BVI Subnet Withheld: ipv4 No, ipv6 No
   RD Config: none
   RD Auto  : (auto) 198.19.1.5:10165
   RT Auto  : 65000:10165
   Route Targets in Use           Type                 
   ------------------------------ ---------------------
   65000:10165                    Import               
   65000:10165                    Export 

   RP/0/RP0/CPU0:node-5#
```

### `show segment-routing srv6 sid` (Locator: MAIN)

All three PEs allocate both EVPN SIDs from the `MAIN` locator block, owner `l2vpn_srv6`,
context `10165:0`, state `InUse` (uDT2U + uDT2M).

```
## Node-10

*** Locator: 'MAIN' *** 

fcbb:0:10::                 uN (PSP/USD)      'default':16                      sidmgr              InUse  Y 
fcbb:0:10:e000::            uDT2U             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:10:e001::            uDT2M             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:10:e002::            uA (PSP/USD)      [BE101, Link-Local]:0             isis-1              InUse  Y 
fcbb:0:10:e003::            uA (PSP/USD)      [BE105, Link-Local]:0             isis-1              InUse  Y 
fcbb:0:10:e004::            uB6 (PSP/USD Insert.Red)  'srte_c_2112_ep_2010::5' (2112, 2010::5)  xtc_srv6            InUse  Y 
fcbb:0:10:e005::            uB6 (PSP/USD Insert.Red)  'srte_c_2112_ep_2010::16' (2112, 2010::16)  xtc_srv6            InUse  Y 
fcbb:0:10:e006::            uDT2U             10165:0                           l2vpn_srv6          InUse  Y 
fcbb:0:10:e007::            uDT2M             10165:0                           l2vpn_srv6          InUse  Y 
```
```
## Node-16

*** Locator: 'MAIN' *** 

fcbb:0:16::                 uN (PSP/USD)      'default':22                      sidmgr              InUse  Y 
fcbb:0:16:e000::            uDT2U             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:16:e001::            uDT2M             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:16:e002::            uA (PSP/USD)      [Hu0/0/0/37, Link-Local]:0        isis-1              InUse  Y 
fcbb:0:16:e003::            uA (PSP/USD)      [Te0/0/0/4, Link-Local]:0         isis-1              InUse  Y 
fcbb:0:16:e004::            uA (PSP/USD)      [Te0/0/0/5, Link-Local]:0         isis-1              InUse  Y 
fcbb:0:16:e005::            uB6 (Insert.Red)  'srte_c_2112_ep_2010::5' (2112, 2010::5)  xtc_srv6            InUse  Y 
fcbb:0:16:e006::            uB6 (Insert.Red)  'srte_c_2112_ep_2010::10' (2112, 2010::10)  xtc_srv6            InUse  Y 
fcbb:0:16:e007::            uDT2U             10165:0                           l2vpn_srv6          InUse  Y 
fcbb:0:16:e008::            uDT2M             10165:0                           l2vpn_srv6          InUse  Y 
```
```
## Node-5 

*** Locator: 'MAIN' *** 

fcbb:0:5::                  uN (PSP/USD)      'default':5                       sidmgr              InUse  Y 
fcbb:0:5:e000::             uDT2U             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:5:e001::             uDT2M             12346:0                           l2vpn_srv6          InUse  Y 
fcbb:0:5:e002::             uA (PSP/USD)      [Hu0/0/0/18, Link-Local]:0        isis-1              InUse  Y 
fcbb:0:5:e003::             uA (PSP/USD)      [Hu0/0/0/16, Link-Local]:0        isis-1              InUse  Y 
fcbb:0:5:e004::             uA (PSP/USD)      [Hu0/0/0/14, Link-Local]:0        isis-1              InUse  Y 
fcbb:0:5:e005::             uA (PSP/USD)      [BE45, Link-Local]:0              isis-1              InUse  Y 
fcbb:0:5:e006::             uA (PSP/USD)      [BE57, Link-Local]:0              isis-1              InUse  Y 
fcbb:0:5:e007::             uA (PSP/USD)      [BE105, Link-Local]:0             isis-1              InUse  Y 
fcbb:0:5:e008::             uB6 (Insert.Red)  'srte_c_2112_ep_2010::10' (2112, 2010::10)  xtc_srv6            InUse  Y 
fcbb:0:5:e009::             uA (PSP/USD)      [Hu0/0/0/8, Link-Local]:0         isis-1              InUse  Y 
fcbb:0:5:e00a::             uB6 (Insert.Red)  'srte_c_2112_ep_2010::16' (2112, 2010::16)  xtc_srv6            InUse  Y 
fcbb:0:5:e00b::             uDT2U             10165:0                           l2vpn_srv6          InUse  Y 
fcbb:0:5:e00c::             uDT2M             10165:0                           l2vpn_srv6          InUse  Y 
```

### `show l2vpn bridge-domain bd-name BRIDGE_evi_10165`

All three PEs: bridge-domain `state: up`, EVPN `state: up`.

```
## Node-10

Tue Jun 23 00:55:34.832 UTC
Legend: pp = Partially Programmed.
Bridge group: BRIDGE, bridge-domain: BRIDGE_evi_10165, id: 1, state: up, ShgId: 0, MSTi: 0
  Aging: 300 s, MAC limit: 64000, Action: none, Notification: syslog
  Filter MAC addresses: 0
  ACs: 1 (1 up), VFIs: 0, PWs: 0 (0 up), PBBs: 0 (0 up), VNIs: 0 (0 up)
  List of EVPNs:
    EVPN, state: up
  List of ACs:
    Te0/0/0/20.3111, state: up, Static MAC addresses: 0, MSTi: 2
  List of Access PWs:
  List of VFIs:
  List of Access VFIs:
RP/0/RP0/CPU0:node-10#

```
```
## Node-16

Tue Jun 23 00:55:36.471 UTC
Legend: pp = Partially Programmed.
Bridge group: BRIDGE, bridge-domain: BRIDGE_evi_10165, id: 1, state: up, ShgId: 0, MSTi: 0
  Aging: 300 s, MAC limit: 4000, Action: none, Notification: syslog
  Filter MAC addresses: 0
  ACs: 1 (1 up), VFIs: 0, PWs: 0 (0 up), PBBs: 0 (0 up), VNIs: 0 (0 up)
  List of EVPNs:
    EVPN, state: up
  List of ACs:
    Te0/0/0/30.3111, state: up, Static MAC addresses: 0, MSTi: 2
  List of Access PWs:
  List of VFIs:
  List of Access VFIs:

  ```
  ```
  ## Node-5 

  Tue Jun 23 00:55:38.028 UTC
Legend: pp = Partially Programmed.
Bridge group: BRIDGE, bridge-domain: BRIDGE_evi_10165, id: 1, state: up, ShgId: 0, MSTi: 0
  Aging: 300 s, MAC limit: 64000, Action: none, Notification: syslog
  Filter MAC addresses: 0
  ACs: 1 (1 up), VFIs: 0, PWs: 0 (0 up), PBBs: 0 (0 up), VNIs: 0 (0 up)
  List of EVPNs:
    EVPN, state: up
  List of ACs:
    Hu0/0/0/30.3110, state: up, Static MAC addresses: 0, MSTi: 2
  List of Access PWs:
  List of VFIs:
  List of Access VFIs:
RP/0/RP0/CPU0:node-5#
```

The fix above applies to the **IOS-XR CLI NED** path, which is the one in use for these nodes.
