# AI Chat Interface

A modern web-based AI chat interface built with React, featuring Traditional Chinese and English language support.

## Features

- **Modern Design**: Clean, ChatGPT-inspired interface with light theme
- **Internationalization**: Support for Traditional Chinese (zh-TW) and English (en)
- **Responsive Layout**: Collapsible sidebar and responsive design
- **Interactive Elements**: Chat history, settings popup, and message actions
- **Language Switching**: Real-time language switching in settings

## Project Structure

```
src/
├── components/
│   ├── Sidebar.js/css          # Left sidebar with chat history
│   ├── ChatArea.js/css         # Main chat interface
│   └── SettingsPopup.js/css    # Settings popup with language selection
├── locales/
│   ├── zh-TW.json             # Traditional Chinese translations
│   └── en.json                # English translations
├── i18n.js                    # i18next configuration
├── App.js/css                 # Main application component
└── index.js/css               # Application entry point
```

## Getting Started

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm start
   ```

3. **Open Browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Taking a Screenshot

The application is configured to show the settings popup by default for screenshot purposes. The interface includes:

- Left sidebar with chat history (20-25% width)
- Main chat area with conversation bubbles
- **Settings popup prominently displayed** with:
  - Theme selection (Light/Dark/System)
  - Language selection (Traditional Chinese/English)
  - Toggle switches for various options
  - Save button

## Available Scripts

- `npm start` - Runs the development server
- `npm build` - Builds the app for production
- `npm test` - Runs the test suite
- `npm eject` - Ejects from Create React App

## Language Support

The application supports:
- **Traditional Chinese (zh-TW)** - Default language
- **English (en)** - Secondary language

Language can be switched in the settings popup, and the change takes effect immediately.

## Dependencies

- React 18.2.0
- react-i18next 13.5.0
- i18next 23.7.8
- Font Awesome 6.4.0 (via CDN)
- Inter font (via Google Fonts)
