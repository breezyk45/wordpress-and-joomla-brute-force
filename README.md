# 🚀 CMS BruteForce PRO - Ultimate Security Scanner

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![License](https://img.shields.io/badge/License-MIT-orange)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)

<p align="center">
  <img src="https://i.postimg.cc/prRDmq4P/hack.jpg" alt="CMS BruteForce PRO" width="600"/>
</p>

## 🌟 Overview

**CMS BruteForce PRO** is an advanced cybersecurity tool designed for penetration testers and security researchers. This powerful application automatically detects whether a target website uses **Joomla** or **WordPress** and then launches the appropriate brute-force attack with sophisticated enumeration capabilities.

Developed by **HackFutSec**, this tool combines cutting-edge techniques with a sleek cyberpunk-themed interface for the ultimate security assessment experience.

## 🎯 Features

### 🔍 Smart CMS Detection
- **Automatic CMS Identification** - Detects Joomla vs WordPress with version checking
- **Mass Target Processing** - Scan multiple URLs with automatic CMS classification
- **Version Fingerprinting** - Identifies CMS versions for vulnerability assessment

### ⚡ Advanced Attack Vectors
#### For Joomla:
- User enumeration via multiple methods (JSON API, HTML parsing, metadata)
- Administrator path detection and exploitation
- CSRF token handling and session management
- Advanced response analysis for login validation

#### For WordPress:
- REST API user enumeration
- Author sitemap and feed analysis
- User existence testing through login responses
- WP-JSON endpoint exploitation

### 🎨 Cyberpunk GUI
- **Transparent glass-morphism design** with animated backgrounds
- **Real-time logging** with color-coded output
- **Progress tracking** with animated progress bars
- **Multi-tab interface** for single and mass target operations

### 🔧 Technical Capabilities
- **Multi-threaded attacks** (configurable thread count)
- **Proxy support** with rotation capabilities
- **Custom delay settings** between requests
- **Auto-password generation** based on usernames and domains
- **Comprehensive wordlist management**

## 🛠️ Installation

### Prerequisites
```bash
# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install python3-pip python3-tk

# For Windows
# Install Python 3.8+ from python.org
```

### Install Dependencies
```bash
pip install requests beautifulsoup4 tqdm pyqt5
```

### Clone & Run
```bash
git clone https://github.com/HackFutSec/CMS-BruteForce-PRO.git
cd CMS-BruteForce-PRO
python3 cms_bruteforce.py
```

## 🎮 Usage

### Single Target Mode
1. Enter the target URL in the "Target URL" field
2. Configure username options:
   - Manual username input
   - User list file import
   - Auto user discovery (recommended)
3. Set password options:
   - Default password list
   - Custom wordlist
   - Auto-password generation with domain
4. Adjust advanced settings (proxy, delay, threads)
5. Click "Start Attack"

### Mass Target Mode
1. Load a list of URLs from a text file
2. Configure global attack parameters
3. Set user enumeration preferences
4. Start mass scan - tool will automatically:
   - Detect CMS for each URL
   - Apply appropriate attack method
   - Save results separately

### Settings Configuration
- **Proxy Setup**: Configure HTTP proxies for anonymity
- **User Agents**: Rotate user agents to avoid detection
- **Timeout Settings**: Adjust request timeouts
- **Thread Management**: Control concurrent connections

## 📊 Output & Results

### Success Indicators
- ✅ **Full Access**: Administrator privileges obtained
- 🔓 **Limited Access**: User profile access only
- 📝 **Credentials Saved**: Automatically exported to files

### Export Files
- `joooAccess.txt` - Joomla administrator credentials
- `fullaccess.txt` - Full access credentials (both CMS)
- `limitaccess.txt` - Limited access credentials
- `password_reset_success.txt` - Successful password resets

## ⚡ Advanced Features

### Smart Password Generation
```python
# Generates passwords based on:
- Username variations (admin, admin123, Admin123!, etc.)
- Domain patterns (example, example123, example2023)
- Common password patterns with special characters
- Sequential numbers and years
- Custom character combinations
```

### User Enumeration Techniques
```python
# Joomla:
- com_users component exploitation
- JSON API endpoint analysis
- Metadata extraction
- Author information parsing

# WordPress:
- WP-JSON API user discovery
- Author sitemap analysis
- RSS feed extraction
- Login response analysis
```

## 🛡️ Legal & Ethical Use

**⚠️ Important Disclaimer:** 
This tool is designed for:
- Authorized penetration testing
- Security research and education
- Vulnerability assessment with permission
- Cybersecurity training exercises

**🚫 Illegal use of this tool is strictly prohibited.** The developer assumes no liability for misuse of this software. Always obtain proper authorization before testing any system.

## 🌐 Connect with HackFutSec

<p align="center">
  <a href="https://github.com/HackFutSec">
    <img src="https://img.shields.io/badge/GitHub-HackFutSec-181717?style=for-the-badge&logo=github" alt="GitHub"/>
  </a>
  <a href="https://t.me/H3CKfutS3c">
    <img src="https://img.shields.io/badge/Telegram-@H3CKfutS3c-26A5E4?style=for-the-badge&logo=telegram" alt="Telegram"/>
  </a>
  <a href="mailto:hackfutsec@protonmail.com">
    <img src="https://img.shields.io/badge/Email-hackfutsec@protonmail.com-8B89CC?style=for-the-badge&logo=protonmail" alt="Email"/>
  </a>
</p>

## 📝 Changelog

### v2.0 - Current Release
- ✅ Combined Joomla & WordPress capabilities
- ✅ Automatic CMS detection system
- ✅ Enhanced cyberpunk GUI theme
- ✅ Improved user enumeration algorithms
- ✅ Advanced password generation engine
- ✅ Multi-threading optimization

### v1.5 - Previous Version
- ✅ Initial Joomla brute force implementation
- ✅ Basic GUI interface
- ✅ User discovery features
- ✅ Wordlist management

## 🐛 Bug Reports & Feature Requests

Found a bug or have a feature idea? Please open an issue on GitHub:

1. Check existing issues to avoid duplicates
2. Provide detailed description of the problem
3. Include steps to reproduce
4. Add screenshots if applicable
5. Specify your environment (OS, Python version)

## 🤝 Contributing

We welcome contributions from the security community! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgments

- Cybersecurity community for continuous research
- Open-source projects that inspired this tool
- Beta testers who helped refine the functionality
- Contributors who submitted improvements

---

<p align="center">
  <em>"Knowledge is power. Use it responsibly."</em> - HackFutSec
</p>

<p align="center">
  ⭐ Don't forget to star this repository if you find it useful! ⭐
</p>

---

**🔒 Remember:** Always conduct security testing ethically and with proper authorization. The goal is to improve security, not compromise it.
