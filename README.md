# PS4 PKG Streamer — Android preview

Source project, NOT a compiled APK. Build has not been run or tested on Android.
Uses Kivy and Python standard-library HTTP/FTP. No Windows desktop app needed during transfers.

## Build without installing Android tools on your PC
1. Create a GitHub repository.
2. Upload the extracted project contents to its root (main.py and buildozer.spec at root).
3. Ensure .github/workflows/android.yml is included; hidden folders can be missed.
4. Go to Actions -> Build Android APK -> Run workflow.
5. When the run succeeds, open the run and download its APK artifact.
6. Extract the artifact ZIP and copy the .apk to your Android phone.
7. Allow installation from that source only if you trust the build, then install.

Actions requires an account and available build allowance. Builds download large Android SDK/NDK
components. A first build can take a long time. If it fails, inspect logs; this is an unverified
starting configuration, not a guaranteed build service. No signing secrets are required for
a debug APK. Do not put private game links or tokens in the repository.

## Local build alternative
Use Linux or WSL2 on Windows. Install Buildozer prerequisites from its official documentation,
then run `buildozer -v android debug` from the extracted project directory.
APK output is in bin/. Build on the Linux filesystem, not a Windows-mounted directory.

## Use
- Enable PS4 GoldHEN FTP on your trusted home LAN.
- Enter the PS4 local IP and port (typically 2121).
- Leave the destination as /data/pkg unless you know otherwise.
- Paste a direct HTTP(S) package link. Blank filename auto-detects from URL.
- Tap Start transfer and confirm the replacement warning.
- Keep the app visible, phone awake and connected until Finished appears.
- Only after completion, install the package through GoldHEN Package Installer.

## Features
- Dark touch interface; saved IP/port/folder (URL not saved).
- Bounded ~4 MiB data queue; separate download/upload threads.
- No full package stored on phone disk.
- Progress, average transfer speed, ETA when Content-Length is available.
- Cancellation; temporary .part file renamed after upload completes.

## Important limitations
- Early preview: syntax checked only; no Android runtime or real-network testing here.
- Foreground transfers only. No Android foreground service, wake lock acquisition, or guaranteed
  background downloading. WAKE_LOCK permission alone does NOT keep the phone awake.
- HTTP/network operations can take up to their timeout before cancellation completes.
- Anonymous FTP only. FTP is unencrypted; never expose it to the public internet.
- No resume, retries, checksum verification, free-space check, or PKG format validation.
- Existing .part is overwritten; existing final package is replaced after completed upload.
- Rename failure after deletion can leave only the completed .part file.
- Uses an arm64 debug build. Older 32-bit phones need a different architecture setting.
- Expired links, login pages, archives and anti-bot protected downloads are not supported.
- Android/OEM networking and power policies may require additional testing or changes.
- Faster than desktop version is NOT guaranteed.
- Only use files you are authorized to download. No game catalog or links included.

Before public release: device-test cancellation, disconnections, duplicate files, storage full,
large downloads and sleep behavior. Select your own package ID and license. Debug builds are
for testing; publishing requires release signing and relevant store requirements.
