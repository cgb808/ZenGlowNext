# 📱 ZenGlow Mobile Setup Guide

## Getting ZenGlow on Your Phone

### 📥 Step 1: Install Expo Go App

- **iOS**: Download from App Store: [Expo Go](https://apps.apple.com/app/expo-go/id982107779)
- **Android**: Download from Google Play: [Expo Go](https://play.google.com/store/apps/details?id=host.exp.exponent)

### 🔗 Step 2: Connect to Development Server

1. **Make sure your phone and computer are on the same WiFi network**
2. **Open Expo Go app on your phone**
3. **Scan the QR code** that appears in your terminal/browser
   - On iOS: Use the built-in QR scanner in Expo Go
   - On Android: Use the QR scanner in Expo Go

### 🌐 Alternative Connection Methods

If QR code doesn't work:

- **Open the Expo development URL** in your phone's browser
- **Use the "exp://" URL** shown in the terminal
- **Type the IP address manually** in Expo Go

### 🔧 Troubleshooting

- **Firewall**: Make sure Windows Firewall allows Expo connections
- **Network**: Ensure both devices are on same WiFi
- **Expo Go**: Update to latest version if having issues
- **Metro**: If build fails, try clearing cache with `npx expo start -c`
- **Syntax Errors**: Check that all `.jsx/.js` files contain React components, not JSON data
- **Missing Semicolons**: Watch for JSON in JSX files causing syntax errors

### ⚠️ **Common Error Fixes**

**"Missing semicolon" errors**: Usually means JSON data in a `.jsx` file

- ✅ **Fixed**: Converted `foodhydration.jsx` from JSON to React component
- 🔍 **Check**: Other `.jsx` files should export React components, not contain raw JSON

**MSSQL syntax errors in PostgreSQL files**: VS Code using wrong SQL parser

- ✅ **Fixed**: Updated `.vscode/settings.json` to use PostgreSQL for Supabase files
- 🔍 **Files**: `supabase/migrations/*.sql` now properly recognized as PostgreSQL
- 💡 **Tip**: Install PostgreSQL extension instead of MSSQL for Supabase development

### 🐛 **VS Code Debugging with Expo Tools**

1. **Start Expo manually first**:

   ```bash
   npx expo start --clear
   ```

2. **Wait for Expo to fully load** (you'll see QR code and "Metro waiting on...")
3. **Press F5 in VS Code** or go to Run & Debug panel
4. **Select "Attach to Expo"** configuration
5. **Debugger will connect** to the running Expo server

**Debug Commands Available:**

- `Ctrl+Shift+P` → `Expo: Preview Config` - Check app.json issues
- `Ctrl+Shift+P` → `Expo: Preview Modifier` - See prebuild output  
- `Ctrl+Shift+P` → `Expo: Open DevTools` - Enhanced debugging interface

### 📊 Development URLs

- **Expo DevTools**: <http://localhost:19002>
- **Supabase Studio**: <http://localhost:54323>
- **Metro Bundler**: <http://localhost:8081>

### 🚀 Live Reload Features

- **Fast Refresh**: Changes appear instantly on your phone
- **Hot Reload**: State is preserved during code changes
- **Error Overlay**: See errors directly on your phone screen
- **Remote Debugging**: Use Chrome DevTools for debugging

### 🎯 ZenGlow Features to Test

1. **ZenMoon Avatar**: Interactive mood-responsive avatar
2. **Sound System**: Guided meditations and ambient sounds
3. **Mood Tracker**: Daily mood logging with visual feedback
4. **Exercise Library**: Breathing exercises and mindfulness activities
5. **Real-time Sync**: Database updates across devices
6. **Offline Support**: Core features work without internet

### 📱 **Mobile Connection Issues**

**If app works in browser but not on phone:**

1. **Try Tunnel Mode** (bypasses network issues):

   ```bash
   npx expo start --tunnel
   ```

   - This creates a secure tunnel through Expo's servers
   - Works even if phone/computer are on different networks
   - Look for `exp://` URL instead of local IP

2. **Check Expo Go App**:
   - ✅ **Latest version**: Update Expo Go from app store
   - ✅ **Account**: Sign in to same Expo account (if using one)
   - ✅ **Camera permissions**: Allow camera access for QR scanning

3. **Network Troubleshooting**:
   - 🔍 **Same WiFi**: Ensure phone and computer on same network
   - 🔍 **Corporate WiFi**: May block device-to-device communication
   - 🔍 **VPN**: Disable VPN on computer or phone
   - 🔍 **Firewall**: Windows Firewall may block Expo ports

4. **Alternative Connection Methods**:
   - **Manual URL**: Type the `exp://` URL directly in Expo Go
   - **Development Build**: For persistent testing
   - **Web Preview**: Continue testing in browser during development

5. **Port Check**:

   ```bash
   netstat -an | findstr "19000\|19001\|19002"
   ```

   Should show Expo ports are listening

Enjoy testing ZenGlow on your phone! 📱✨
