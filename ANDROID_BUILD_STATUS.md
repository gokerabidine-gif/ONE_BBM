# ONE BBM Android build

The automated Android APK workflow is configured in `.github/workflows/android-apk.yml`.
It extracts the project archive, validates/builds the web game, packages it with Capacitor, forces landscape orientation, and uploads the debug APK as `ONE-BBM-debug-apk`.
