# Trade-Lens Android app

A small Kotlin Android WebView wrapper for the deployed Trade-Lens website:
https://trade-journal-f8lp.onrender.com/

## Build APK in Android Studio

1. Open Android Studio.
2. Choose **Open** and select the `android-app` folder.
3. Use JDK 17 and allow Gradle sync to finish.
4. Select **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. Android Studio shows the generated APK location, usually `app/build/outputs/apk/debug/app-debug.apk`.

## Notes

- Requires internet access; this is a WebView wrapper, not an offline copy of the website.
- Back button navigates within WebView history.
- JavaScript and DOM storage are enabled for the web app.
- The Render free instance may sleep when idle, so first load can be slow.
- The website currently has no login and its SQLite data is not persistent on Render Free. Do not store sensitive or irreplaceable journal data there until authentication and persistent storage are added.
