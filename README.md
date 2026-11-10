# Antigravity Android ARM64 Port

Antigravity **2.29.1** (Electron 44.5.1, Linux x64) için topluluk tarafından hazırlanmış,
Android **ARM64** üzerinde çalışan deneysel bir port/repack aracı.

Bu depo **yalnızca özgün build ve yama kodlarını** içerir. Antigravity'nin kendi ikili
dosyaları, web bundle'ı, dil sunucusu (language server), APK ve imza anahtarı telif
nedeniyle **depoda yoktur**. Build için bu bileşenleri resmî kaynaktan kendiniz sağlamalısınız.

> **Durum:** deneysel. Google/Antigravity ile bağlantılı değildir. Kendi sorumluluğunuzda
> kullanın. Antigravity'nin lisans/EULA koşullarına uymak kullanıcının sorumluluğundadır.

## Ne yapar?

- `com.agy` Android kabuğunu (referans APK) yeni **2.29.1 ARM64** language server ve
  **2.29.1 web bundle** ile yeniden paketler.
- Yeni language server'ın Android'de DNS çözümlemesini düzeltir.
- `DnsCollector` içindeki loopback (`::1`, `127.0.0.1`) DNS girdilerini temizler; böylece
  yalnızca loopback varsa geçerli fallback DNS (`1.1.1.1`, `77.88.8.8`, `8.8.8.8`) yazılır.
- `resources.arsc` dosyasını sıkıştırmadan (stored) hizalar ve APK'yı v2/v3 ile imzalar.

## Neden bu yamalar?

Android'de oturum açma sırasında şu hata alınıyordu:

```text
Post "https://oauth2.googleapis.com/token":
dial tcp: lookup oauth2.googleapis.com on [::1]:53:
read udp [::1]:...->[::1]:53: read: connection refused
```

Kök neden:

- 2.28.2 language server göreli `etc//resolv.conf` yolunu kullanıyordu. Uygulamanın çalışma
  dizini `filesDir` olduğu için bu, uygulamanın yazdığı `filesDir/etc/resolv.conf` dosyasına
  denk geliyordu.
- 2.29.1 language server mutlak `/etc/resolv.conf` yolunu kullanmaya başladı. Android'de bu
  dosya uygulama tarafından yazılamaz ve cihazın ağ yapılandırmasına göre `::1` (loopback)
  içerebilir. Go çözümleyicisi bu adresi kullanınca DNS isteği başarısız oluyor.

Yapılan düzeltmeler:

1. **Language server:** İkili dosyadaki iki `/etc/resolv.conf` stringi, aynı uzunlukta
   `etc//resolv.conf` ile değiştirilir. Böylece sunucu yine çalışma dizinine göre
   `filesDir/etc/resolv.conf` dosyasını okur.
2. **DnsCollector:** Son DNS listesinden `::1` ve `127.0.0.1` çıkarılır. Liste boş kalırsa
   uygulamanın kendi fallback DNS sunucuları yazılır.

## Depoda olmayanlar

Aşağıdakiler **bilerek** dahil edilmemiştir:

- Antigravity `language_server-linux-arm64` ikilisi
- Antigravity web bundle'ı (`main.js`, `page_*.js`, ikonlar, tema, sesler vb.)
- Referans `com.agy` kabuk APK'sı
- Derlenmiş APK / `.idsig`
- Keystore / private key

Bunları kendiniz temin edin ve **asla** bir Git deposuna keystore eklemeyin.

## Gereksinimler

- Linux (aarch64 veya x86_64) / Termux-chroot
- Python 3
- Java 17+ (`java`, `keytool`)
- `zip`, `unzip`
- Android SDK **build-tools 34.0.0** (`apksigner`, `zipalign`)
- `baksmali.jar` ve `smali.jar` (Debian/Ubuntu'da `apt install apktool` ile
  `/usr/share/java/` altına kurulur; sürüm 2.5.x test edildi)
- aarch64'te `zipalign` x86_64 ikilisi olduğu için doğrudan çalışmaz. Script otomatik olarak
  `qemu-x86_64` denerse de en pratik yol, APK'yı x86_64 bir makinede hizalamak veya
  `qemu-user` + amd64 `libc6` kurmaktır. Hizalama yapılamazsa script uyarı verir; hedef
  `targetSdk 28` olduğu için çoğu cihazda kurulum yine de çalışabilir.

## Girdiler

Aşağıdaki dosyaları `input/` altına koyun (veya `config.env` içinde yollarını belirtin):

| Değişken | Açıklama |
|---|---|
| `REFERENCE_APK` | `com.agy` kabuk APK'sı (2.28.2 tabanlı referans; depoda yok) |
| `LS_BIN` | Antigravity 2.29.1 ARM64 language server |
| `WEB_DIR` | 2.29.1 web bundle dizini (`index.html`, `generated/main.js`, `page_agent_bundle.js`, `page_facade_bundle.js`, `symbols-icons/`, `workers/` ...) |

Resmî ARM64 language server (test edilen):

```text
https://storage.googleapis.com/antigravity-public/antigravity-hub/2.29.1-5241471524274176/unsigned/language_server-linux-arm64
SHA-256: 79c885734bd7aa10ce116ad7bd5117ca6e552501d9f412ba42c33cbca8610784
Boyut:   188567928 bayt
```

Web bundle bu depoda yoktur; resmî Antigravity 2.29.1 kurulumundan çıkarılan web
varlıklarını `WEB_DIR` olarak verin. Build sırasında `WEB_DIR/generated/main.js` varsa ve
kök `main.js` yoksa otomatik olarak kopyalanır (kabuk `filesDir/web/main.js` bekler).

## Hızlı başlangıç

```bash
git clone <repo-url> antigravity-android-port
cd antigravity-android-port

cp config.example.env config.env
# config.env içindeki yolları düzenleyin

chmod +x build.sh
./build.sh
# Dosya sistemi çalıştırma bitini desteklemiyorsa (ör. /sdcard):
# bash build.sh
```

Çıktı: `out/antigravity-2.29.1-arm64.apk`

İlk çalıştırmada `keys/antigravity.keystore` yoksa `keytool` ile üretilir. Bu dosyayı
commit etmeyin; güncellemeler için saklayın. Dağıtımdan önce `config.env` içindeki
`KS_ALIAS` ve `KS_PASS` değerlerini değiştirin.

## Build adımları (özet)

1. Referans APK `build/apk/` altına açılır; `META-INF` silinir.
2. `classes.dex` → `baksmali` → `com/agy/net/DnsCollector.smali` yamalanır → `smali` ile
   yeniden derlenir.
3. `LS_BIN` üzerinde `/etc/resolv.conf` → `etc//resolv.conf` yaması uygulanır.
4. Yeni LS `assets/runtime/bin/liblanguage_server.so` olarak yerleştirilir; 
   `assets/runtime/manifest.json` içindeki `bin/liblanguage_server.so` SHA-256 değeri güncellenir.
5. `WEB_DIR` → `assets/web` kopyalanır; gerekirse kök `main.js` eklenir.
6. APK yeniden paketlenir; `resources.arsc` stored olarak eklenir; `zipalign -p 4` uygulanır.
7. `apksigner` ile v2/v3 imzalanır; `apksigner verify` ve `zipalign -c` ile doğrulanır.

## Doğrulama

Referans derlemede:

- APK boyutu: `110716549` bayt
- SHA-256: `a3430ae91e3ec7b1bb63ce13edf0da7bae1159bca8acb4ec0efd7c45e7dcc170`
- İmza: v1 `false`, v2 `true`, v3 `true`
- `resources.arsc`: stored + 4-byte hizalı
- Yamalı language server başlatıldı; `/` isteği `200` ve `3384` bayt döndü
- `strace` çıktısında `openat(AT_FDCWD, "etc//resolv.conf", ...)` görüldü; yani göreli yol
  gerçekten kullanılıyor

Bu hash yalnızca referans derleme içindir. `smali`/`dexlib2` çıktısı deterministik
değildir; aynı girdilerle her DEX derlemesi farklı byte sırası üretebilir. Bu yüzden
tekrar derlemelerde `classes.dex` ve dolayısıyla APK SHA-256 değişebilir. İşlevsel
içerik (yamalı language server, web bundle, manifest hash'i) aynı kalır. Farklı imza
anahtarı veya farklı `zip` sürümü de hash'i değiştirir.

## Kurulum notları

- APK, orijinal `com.agy` uygulamasından **farklı bir anahtarla** imzalanır. Orijinal uygulama
  kuruluysa önce kaldırılmalıdır (uygulama verileri silinir).
- Bu deponun kendi anahtarıyla üretilen önceki/sonraki build'ler birbirinin üzerine kurulabilir;
  aynı keystore'u saklayın.
- Yalnızca ARM64 cihazlar içindir.
- Android System WebView ve dosya erişimi gerektirir; her ROM'da test edilmedi.

## Bilinen sınırlamalar

- Deneysel; kararlılık/uyumluluk garantisi yok.
- Antigravity güncellemeleri web bundle/LS sözleşmesini değiştirebilir; yamalar kırılabilir.
- Uygulama içi oturum açma, Google OAuth ve ağ erişimi cihaz/ROM'a bağlıdır.
- `zipalign` aarch64'te doğrudan çalışmaz; hizalama atlanırsa bazı Android sürümleri APK'yı
  reddedebilir.

## Lisans

Bu depodaki **özgün scriptler, yamalar ve dokümantasyon** MIT lisansı altındadır
(`LICENSE`). Antigravity, Electron, Chromium ve üçüncü taraf bileşenler kendi lisanslarına
tabidir; bu depo onları yeniden dağıtmaz. "Antigravity" ve ilgili markalar sahiplerine aittir.

## Katkı

Issue/PR açabilirsiniz. Lütfen üçüncü taraf ikili dosyaları, APK'ları veya keystore'ları
commit etmeyin. Yama önerilerinde Android sürümü, cihaz/ROM ve hata logunu belirtin.

## Teşekkür

- Antigravity ekibi (uygulama)
- Electron/Chromium ve açık kaynak toplulukları
- Bu portun build/patch araç zinciri için katkıda bulunanlar
