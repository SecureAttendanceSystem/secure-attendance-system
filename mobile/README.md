# Mobile

React Native, Expo SDK 57, and TypeScript blank starter. Install Node.js 24.3 or
newer and follow the [repository setup](../README.md).

## Run

From the repository root:

```bash
cd mobile
npm ci
npm start
```

Install [Expo Go compatible with SDK 57](https://expo.dev/go), connect your phone
and computer to the same network, and scan the QR code. The app currently shows
the blank starter message. Stop Metro with Ctrl+C.

For an Android emulator, install [Android Studio and configure a virtual device](https://docs.expo.dev/workflow/android-studio-emulator/),
start it, and press **a** in the Expo terminal. For an iOS simulator, use macOS
with [Xcode](https://docs.expo.dev/workflow/ios-simulator/) and press **i**.
If Metro cannot connect over the network, try `npm start -- --tunnel`.
For a stale cache, use `npm start -- --clear`.

## Checks and structure

From `mobile/`:

```bash
npm run lint
npx --no-install tsc --noEmit
```

`App.tsx` is the current screen; `index.ts` registers it. `app.json` contains
Expo configuration and `assets/` holds app icons and splash assets.
Navigation and API integration are future work. No API environment variables
are consumed yet. Future `EXPO_PUBLIC_` values are included in the app and must
not contain secrets.

For future device API testing, use a backend address reachable by the phone:
`localhost` refers to the phone, and the current Docker API binds to the
computer's loopback interface. Metro tunneling does not expose FastAPI.
