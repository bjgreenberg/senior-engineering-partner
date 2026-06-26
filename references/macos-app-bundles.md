# macOS App Bundle Standards

Companion reference for the senior-engineering-partner skill.


When building macOS automation tools that run as LaunchAgents or appear in Login Items & Extensions, always produce a proper `.app` bundle — never invoke a bare script or interpreter directly from a plist.

## Bundle structure

```
MyTool.app/
└── Contents/
    ├── Info.plist          ← required; controls display name, bundle ID, behavior
    └── MacOS/
        └── MyTool          ← executable (chmod +x); see note below
```

### The bundle executable must be a COMPILED, SIGNED binary if the tool needs Full Disk Access

A shell-script bundle executable (`#!/bin/bash …`) is **inert for TCC/FDA**. macOS
attributes Full Disk Access to the *running Mach-O binary's code signature*, not
to the `.app` folder. With a script shim, the kernel honors the shebang and the
real running binary is `/bin/bash` — so TCC checks `/bin/bash` (which must never
have FDA), and the grant on the `.app` does nothing. Symptom: the LaunchAgent
logs `Operation not permitted` (exit 126) reading files in Documents/Desktop/
Downloads even though FDA is toggled on for the app.

- **Tool needs FDA / protected paths** → the bundle executable **must** be a
  compiled Mach-O binary, ad-hoc signed (`codesign --force --deep --sign -`), so
  TCC has a stable cdhash to pin the grant to. Use a tiny C launcher that
  `exec`s the real script. Build universal (`cc -O2 -arch arm64 -arch x86_64`)
  if the bundle syncs across Apple Silicon and Intel machines. Re-grant FDA
  after any rebuild — changing the bytes changes the cdhash.

  ```c
  /* updateall_launcher.c — exec the real script from a compiled, signable binary */
  #include <unistd.h>
  #include <stdlib.h>
  int main(void) {
      const char *home = getenv("HOME");
      char script[1200];
      snprintf(script, sizeof(script), "%s/path/to/actual/script.sh", home ? home : "");
      execl("/bin/bash", "bash", script, (char *)NULL);
      return 127; /* exec failed */
  }
  ```

- **Tool never touches protected paths** (writes only to `~/.local/share/...`,
  `/tmp`, etc.) → a shell-script shim is fine, since no FDA grant is involved:

  ```bash
  #!/bin/bash
  exec "$HOME/path/to/actual/script.sh"
  ```

Also point the plist's `WorkingDirectory` at `$HOME`, never a TCC-protected path:
launchd `chdir`s into it *before* the process starts, producing `getcwd:
Operation not permitted` noise on every run.

## Required Info.plist keys

Every bundle must have a complete `Info.plist`. Omitting it causes the app to appear as "unknown" in Login Items and Privacy panels.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>             <string>Human Readable Name</string>
  <key>CFBundleDisplayName</key>      <string>Human Readable Name</string>
  <key>CFBundleIdentifier</key>       <string>com.example.tool-name</string>
  <key>CFBundleExecutable</key>       <string>MyTool</string>
  <key>CFBundleVersion</key>          <string>1</string>
  <key>CFBundleShortVersionString</key> <string>1.0</string>
  <key>CFBundlePackageType</key>      <string>APPL</string>
  <key>NSHumanReadableCopyright</key> <string>Your Name</string>
  <key>LSUIElement</key>              <true/>   <!-- no Dock icon for background tools -->
  <key>LSMinimumSystemVersion</key>   <string>13.0</string>
</dict>
</plist>
```

`CFBundleIdentifier` must be unique and match the LaunchAgent label (e.g. `com.example.update-all`).

## Code signing options

| Option | Cost | Shows in Login Items | Gatekeeper trust |
|---|---|---|---|
| Unsigned | Free | "Unidentified Developer" | None |
| Ad-hoc (`codesign --sign -`) | Free | "Unidentified Developer" | Minimal |
| Self-signed cert (Keychain Access) | Free | Name from cert | None |
| Apple Developer ID | $99/yr | Verified name | Full |

For personal tools that never leave the machine, unsigned + proper `Info.plist` is acceptable. For anything distributed or run on other machines, require Apple Developer ID.

**A Developer ID signature alone is not enough for a distributed app — it also needs the hardened runtime, correct entitlements, and notarization+stapling.** (1) Build with the **hardened runtime** and declare only the **entitlements** the tool actually uses (network, specific files, a capability) — an over-broad entitlement set is the same least-privilege violation as an over-broad TCC grant. (2) **Notarize** the signed app (submit to Apple's notary service) and **staple** the returned ticket to the bundle, so Gatekeeper can validate it offline on first launch — an un-stapled notarized app still fails for an offline/first-run user. *Verify the current `notarytool`/`stapler` invocation and the entitlement keys against current Apple docs; the requirement (sign → hardened-runtime + entitlements → notarize → staple) is durable, the CLI surface is version-specific.* Ad-hoc and self-signed bundles **cannot** be notarized and cannot be verified off the build machine — they are local-only by definition.

**To sign with an existing Developer ID:**
```bash
codesign --sign "Developer ID Application: Your Name (TEAMID)" \
  --deep --force ~/Applications/MyTool.app
codesign --verify --verbose ~/Applications/MyTool.app
```

## TCC & Full Disk Access for LaunchAgents

macOS TCC (Transparency, Consent, and Control) governs file and folder access. LaunchAgents running in the user's graphical session CAN display TCC dialogs — and will, for every binary that hasn't been individually approved.

**The correct pattern:** wrap the script in a `.app` bundle, grant the bundle Full Disk Access once, and all child processes inherit it.

**Never** invoke interpreters directly in a plist — this forces TCC to prompt individually for every tool the script spawns, and the only way to suppress it would be granting FDA to `/bin/bash` or `/usr/bin/python3`, which grants FDA to every script they execute on the system (a critical security misconfiguration):

```xml
<!-- WRONG — TCC prompts for bash, then for every child binary -->
<key>ProgramArguments</key>
<array>
  <string>/bin/bash</string>
  <string>/path/to/script.sh</string>
</array>

<!-- CORRECT — one FDA grant to the .app covers all children -->
<key>ProgramArguments</key>
<array>
  <string>/Users/you/Applications/MyTool.app/Contents/MacOS/MyTool</string>
</array>
```

After creating or modifying a bundle, register it with Launch Services so the Privacy panels recognize it immediately:

```bash
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  ~/Applications/MyTool.app
```

Then reload the LaunchAgent and grant FDA in **System Settings → Privacy & Security → Full Disk Access**.
