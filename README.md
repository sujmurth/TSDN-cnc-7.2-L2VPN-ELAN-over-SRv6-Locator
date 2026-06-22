# TSDN FP Fix — SRv6 Locator under EVPN-MP (E-LAN) EVI

## Summary

For EVPN Multipoint (E-LAN) services, the TSDN Function Pack (FP) `cisco-L2vpn-fp-internal`
package generated the SRv6 binding **only** under the L2VPN bridge-domain EVI
(`l2vpn ... bridge-domain ... evi <id> segment-routing srv6`), but **omitted** the
SRv6 binding and the **per-EVI locator** under the top-level `evpn evi <id>` block.

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
- **Reference:** xrdocs — *SRv6 Transport on NCS5500, Part 6* (EVPN ELAN over SRv6)

---

## Root Cause

The data model and the L2NM → internal mapping were already complete:

- `cisco-flat-L2vpn-fp-internal-common.yang` — `grouping srv6-grp` → `container srv6 { presence; leaf locator ... }`
- `ietf-l2nm-l2vpn-macros.xml` — `srv6` macro maps `te-service-mapping/srv6/locator` → `srv6/locator`
- `ietf-l2nm-l2vpn-evpn-mp-template.xml` — expands `srv6` into the internal service

The gap was purely in the **device output template** for the IOS-XR CLI NED:
`cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml`. The top-level `<evpn><evi>`
block did not emit the `segment-routing srv6` leaf nor the `locator` leaf, even though
the analogous structure was already proven in
`cisco-flat-L2vpn-fp-cli-routing-policy-template.xml` (applied only for ODN services).

---

## File Changed

`packages/cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml`

### Node structure (IOS-XR CLI NED)

Under `evpn / evi`:
- `<segment-routing when="{srv6}">srv6</segment-routing>` is a **leaf** that renders `segment-routing srv6`.
- `<locator when="{srv6/locator!=''}">{srv6/locator}</locator>` is a **sibling leaf** under
  `<evi>` (NOT nested inside `segment-routing`), and renders `locator <LOCATOR>`.

### Before (stock)

```xml
        <evpn xmlns="http://tail-f.com/ned/cisco-ios-xr">
          <evi>
            <id>{$EVI_ID}</id>
            <bgp>
              ...
            </bgp>
            <etree when="...">...</etree>
            <advertise-mac when="{advertise-mac/enable = 'true'}">
            </advertise-mac>
            <control-word-disable when="{control-word-disable = 'true'}">
            </control-word-disable>
          </evi>
```

### After (fixed)

```xml
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

### Step-by-step edit

1. In the top-level `<evpn>` → `<evi>` block, **after** the line
   `<id>{$EVI_ID}</id>`, insert:
   ```xml
   <segment-routing when="{srv6}">srv6</segment-routing>
   ```
2. In the same `<evi>` block, **after** the closing `</control-word-disable>` and
   **before** `</evi>`, insert:
   ```xml
   <locator when="{srv6/locator!=''}">{srv6/locator}</locator>
   ```

> Note: the bridge-domain EVI binding (`<segment-routing when="{srv6}">srv6</segment-routing>`
> under `l2vpn ... bridge-domain ... evi`) was already present in stock and is unchanged.

---

## Deployment (applied on live CNC controller 172.20.163.27)

The fix was applied to the running eNSO package copy and the package reloaded:

1. Backed up the live template (`...template.xml.bak`).
2. Applied the two inserts above to
   `/nso/run/packages/cisco-L2vpn-fp-internal/templates/cisco-flat-L2vpn-fp-cli-evpn-multipoint-template.xml`.
3. Reloaded packages:
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
              { "vpn-node-id": "node-10",
                "cisco-l2vpn-ntw:te-service-mapping": { "srv6": { "locator": "MAIN" } } },
              { "vpn-node-id": "node-16",
                "cisco-l2vpn-ntw:te-service-mapping": { "srv6": { "locator": "MAIN" } } },
              { "vpn-node-id": "node-5",
                "cisco-l2vpn-ntw:te-service-mapping": { "srv6": { "locator": "MAIN" } } }
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

## Verification (nodes node-10, node-16, node-5)

### `show evpn evi vpn-id 10165 detail`

| Field | node-10 | node-16 | node-5 |
|---|---|---|---|
| Encap | SRv6 | SRv6 | SRv6 |
| Type | EVPN | EVPN | EVPN |
| Bridge Domain | BRIDGE_evi_10165 | BRIDGE_evi_10165 | BRIDGE_evi_10165 |
| Unicast SID (uDT2U) | fcbb:0:10:e006:: | fcbb:0:16:e007:: | fcbb:0:5:e00b:: |
| Multicast SID (uDT2M) | fcbb:0:10:e007:: | fcbb:0:16:e008:: | fcbb:0:5:e00c:: |
| Advertise MACs | Yes | Yes | Yes |
| **SRv6 Locator Name** | **MAIN** | **MAIN** | **MAIN** |
| RT Auto | 65000:10165 | 65000:10165 | 65000:10165 |

### `show segment-routing srv6 sid` (Locator: MAIN)

All three PEs allocate both EVPN SIDs from the `MAIN` locator block, owner `l2vpn_srv6`,
context `10165:0`, state `InUse` (uDT2U + uDT2M).

### `show l2vpn bridge-domain bd-name BRIDGE_evi_10165`

All three PEs: bridge-domain `state: up`, EVPN `state: up`.

> The attachment circuits (ACs) show `down` because the physical AC ports are down at
> Layer 1 (no CE/optic/peer in the lab). This is independent of the SRv6 locator fix —
> the EVPN/SRv6 control plane and data-plane SID allocation are fully programmed.

---

## Related templates (change only if those NEDs are used)

- UM NED: `packages/l2vpn-multi-vendors/templates/cisco-flat-L2vpn-fp-um-evpn-multipoint-template.xml`
  (has bridge-domain `segment-routing-srv6-evis` but no `locator` under `evis/evi`).
- Native NC NED: `packages/l2vpn-multi-vendors/templates/cisco-flat-L2vpn-fp-native-evpn-multipoint-template.xml`
  (no srv6/locator at all).

The fix above applies to the **IOS-XR CLI NED** path, which is the one in use for these nodes.
