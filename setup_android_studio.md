# Setup Android Studio Flow

Dokumen ini menjelaskan cara menjalankan flow `GoogleOneAutomation` versi lokal memakai Android Studio emulator/device + Appium, tanpa Firebase Test Lab, Firestore, Telegram Bot, atau Device Manager.

## 1. Perbandingan flow utama vs flow Android Studio

Flow utama Encore:

```text
Telegram Bot
  -> Firestore jobs queue
  -> Device Manager
  -> Firebase Test Lab device
  -> Device Automation
  -> GmailLogin
  -> GoogleOneAutomation
  -> offer link dikirim ke Telegram
```

Flow Android Studio lokal:

```text
Android Studio emulator / physical device
  -> Appium server lokal
  -> script_android_studio.py
  -> GoogleOneAutomation
  -> offer link muncul di terminal
```

Yang tetap dipakai:

- `services/device_automation/google_one_automation.py`
- Package Google One: `com.google.android.apps.subscriptions.red`
- Appium + UiAutomator2
- Strategi pencarian link `https://one.google.com/partner-eft-onboard/...`

Yang tidak dipakai:

- Telegram Bot
- Firestore
- Device Manager
- Firebase Test Lab
- Cloud Run
- Enkripsi credential
- Queue/retry cloud

## 2. Prasyarat

Install di laptop/PC:

- Android Studio
- Android SDK Platform Tools (`adb`)
- Python 3.11+
- Node.js + npm
- Appium 2

Install Appium:

```bash
npm install -g appium
appium driver install uiautomator2
```

Pastikan command ini tersedia:

```bash
adb version
python --version
appium --version
```

## 3. Siapkan emulator/device

Opsi A — Android Studio emulator:

1. Buka Android Studio.
2. Buka Device Manager.
3. Start emulator Android.
4. Pastikan device terbaca:

```bash
adb devices
```

Contoh output:

```text
List of devices attached
emulator-5554	device
```

Opsi B — HP fisik:

1. Aktifkan Developer Options.
2. Aktifkan USB debugging.
3. Sambungkan via USB.
4. Izinkan prompt debugging di HP.
5. Cek:

```bash
adb devices
```

## 4. Pastikan Google One sudah ada

Kode ini membuka Google One dengan package:

```text
com.google.android.apps.subscriptions.red
```

Cek apakah sudah terinstall:

```bash
adb shell pm list packages | grep com.google.android.apps.subscriptions.red
```

Kalau muncul:

```text
package:com.google.android.apps.subscriptions.red
```

berarti bisa dibuka oleh script.

Tes buka manual via ADB:

```bash
adb shell monkey -p com.google.android.apps.subscriptions.red -c android.intent.category.LAUNCHER 1
```

Kalau package tidak muncul, install Google One dulu di emulator/device. `activate_app()` hanya membuka app yang sudah ada, bukan menginstall app.

## 5. Login akun Google

Versi Android Studio ini tidak otomatis mengambil credential dari Telegram/Firestore.

Paling sederhana:

1. Login akun Google manual di emulator/device.
2. Pastikan Google One bisa dibuka.
3. Pastikan offer memang muncul untuk akun tersebut.

Kalau akun belum punya offer, script tidak bisa “membuat” offer. Script hanya mengambil link offer yang memang sudah ditampilkan Google One.

## 6. Setup Python environment

Dari root repo:

```bash
cd encorepvt
python -m venv .venv
source .venv/bin/activate
pip install -r services/device_automation/requirements.txt
```

Di Windows PowerShell:

```powershell
cd encorepvt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r services/device_automation/requirements.txt
```

## 7. Jalankan Appium

Buka terminal pertama:

```bash
appium
```

Biarkan terminal ini tetap hidup.

Default script memakai Appium server:

```text
http://127.0.0.1:4723
```

## 8. Jalankan script Android Studio

Buka terminal kedua:

```bash
source .venv/bin/activate
python script_android_studio.py
```

Kalau ada lebih dari satu device:

```bash
adb devices
python script_android_studio.py --udid emulator-5554
```

Kalau Appium server beda URL:

```bash
python script_android_studio.py --appium-server http://127.0.0.1:4723
```

Kalau ingin melewati pengecekan package Google One:

```bash
python script_android_studio.py --skip-install-check
```

## 9. Flow internal saat script berjalan

`script_android_studio.py` melakukan ini:

1. Menjalankan `adb devices`.
2. Memilih device pertama, atau device dari `--udid`.
3. Mengecek package Google One:

```text
com.google.android.apps.subscriptions.red
```

4. Membuat Appium driver dengan UiAutomator2.
5. Memanggil:

```python
automation = GoogleOneAutomation(driver)
offer_link = automation.get_offer_link()
```

6. `GoogleOneAutomation` membuka Google One:

```python
self.driver.activate_app(GOOGLE_ONE_PACKAGE)
```

7. Script mencari offer link.
8. Kalau berhasil, terminal menampilkan:

```text
OFFER LINK:
https://one.google.com/partner-eft-onboard/...
```

## 10. Cara kerja `GoogleOneAutomation`

File utama:

```text
services/device_automation/google_one_automation.py
```

Urutan kerjanya:

1. Buka Google One.
2. Tutup dialog umum seperti:
   - `Not now`
   - `Skip`
   - `Maybe later`
   - `No thanks`
   - `Got it`
3. Cari URL offer langsung di element Android.
4. Cari URL offer di `page_source`.
5. Coba pindah ke tab:
   - `Upgrade`
   - `Benefits`
   - `Plans`
   - `Get more storage`
6. Cari banner/teks:
   - `Gemini Pro`
   - `Gemini Advanced`
   - `Try Gemini`
   - `AI Premium`
   - `Claim offer`
   - `Get offer`
   - `Free trial`
7. Tap banner jika ketemu.
8. Cek apakah WebView/Chrome terbuka.
9. Ambil URL aktif jika cocok dengan prefix:

```text
https://one.google.com/partner-eft-onboard/
```

10. Kalau masih gagal, ambil screenshot dan OCR pakai Tesseract.
11. Kalau tetap tidak ketemu, script error:

```text
Could not find Gemini Pro offer link in Google One app
```

## 11. Troubleshooting

### `No Android device/emulator found`

Emulator belum jalan atau `adb` belum mendeteksi device.

```bash
adb devices
```

Kalau kosong, start emulator dari Android Studio.

### `Google One is not installed`

Package ini belum ada:

```text
com.google.android.apps.subscriptions.red
```

Install/buka Google One dulu di emulator/device.

### Appium connection gagal

Pastikan Appium hidup:

```bash
appium
```

Pastikan driver UiAutomator2 sudah terinstall:

```bash
appium driver list --installed
```

Kalau belum:

```bash
appium driver install uiautomator2
```

### Google One terbuka tapi link tidak ketemu

Kemungkinan:

- Akun tidak punya offer.
- Offer tidak tampil di region/device tersebut.
- UI Google One berubah.
- Banner perlu scroll, tapi script belum punya logic scroll mendalam.
- Link tidak muncul sebagai text/page source sehingga OCR juga gagal.

### Banyak device terhubung

Pilih manual:

```bash
python script_android_studio.py --udid emulator-5554
```

## 12. Ringkasan

Versi cloud memakai Firebase untuk membuat device dan queue otomatis. Versi Android Studio memakai device lokal milikmu sendiri. Selama emulator/device sudah login Google, Google One sudah terinstall, dan Appium aktif, `script_android_studio.py` bisa menjalankan logic offer extraction yang sama tanpa cloud.
