# DnsCollector patch

Target class: `com.agy.net.DnsCollector`
Target DEX: `classes.dex` from the reference `com.agy` APK (2.28.2 / core 2.4.1)

## Problem

`collectDnsServers(Context)` merges IPv4 servers (`arrayList`) and IPv6 servers
(`arrayList2`) into a new list (`p0` / `arrayList3`). On some Android/VPN
configurations the IPv6 list contains `::1`. The list is then non-empty, so the
fallback block (`1.1.1.1`, `77.88.8.8`, `8.8.8.8`) is skipped. The shell writes
that loopback address into `<filesDir>/etc/resolv.conf`, and the bundled Go
language server sends DNS queries to `[::1]:53`.

## Change

After the two `addAll` calls and before the `isEmpty()` check, remove loopback
entries:

```smali
    invoke-interface {p0, v2}, Ljava/util/List;->addAll(Ljava/util/Collection;)Z

    const-string v0, "::1"

    invoke-interface {p0, v0}, Ljava/util/List;->remove(Ljava/lang/Object;)Z

    const-string v0, "127.0.0.1"

    invoke-interface {p0, v0}, Ljava/util/List;->remove(Ljava/lang/Object;)Z

    .line 50
    invoke-interface {p0}, Ljava/util/List;->isEmpty()Z
```

If no real resolver remains, the existing fallback block adds valid public DNS
servers. The patch is applied automatically by `scripts/patch_dns_collector.py`;
the script is idempotent and aborts if the anchor is not found exactly once.
