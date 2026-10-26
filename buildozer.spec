[app]
title = PS4 PKG Streamer
package.name = ps4pkgstreamer
package.domain = org.communitytools
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1.0
requirements = python3,kivy,openssl
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WAKE_LOCK
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
