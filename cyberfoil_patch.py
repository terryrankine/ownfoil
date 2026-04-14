"""
CyberFoil client implementation.
"""
from flask import Request, Response, jsonify
from typing import Tuple, Optional, Dict, Any
import json
import sqlite3
import os

from .client import BaseClient
from settings import set_shop_settings
from constants import APP_TYPE_FILTERS

CYBERFOIL_HEADERS = [
    'Theme',
    'Uid',
    'Version',
    'Revision',
    'Language',
    'Hauth',
    'Uauth'
]

class CyberFoilClient(BaseClient):
    """CyberFoil client with header-based identification, Hauth verification."""

    CLIENT_NAME = "CyberFoil"

    @classmethod
    def identify_client(cls, request: Request) -> bool:
        """Identify CyberFoil client by checking for required headers."""
        return all(header in request.headers for header in CYBERFOIL_HEADERS) and request.headers.get('User-Agent') == 'cyberfoil'

    def error_response(self, error_message: str) -> Response:
        return jsonify({'error': error_message})

    def info_response(self, info_message: str) -> Response:
        return jsonify({'success': info_message})

    @BaseClient.authenticate
    @BaseClient.verify_shop_access
    def _handle_get(self, request: Request) -> Response:
        if not request.client_auth_success:
            return self.error_response(request.client_auth_error)
        client_settings = self.app_settings['shop']['clients']['cyberfoil']
        paths = request.path.strip('/').split('/')
        content_filter = paths[0] if paths and paths[0] in APP_TYPE_FILTERS else None
        shop = {"success": self.app_settings['shop']['motd']}
        shop["files"] = self._generate_shop_files(content_filter)
        verified_host = request.auth_data.get('verified_host')
        if verified_host:
            shop["referrer"] = f"https://{verified_host}"
        return jsonify(shop)

    def _client_authenticate(self, request: Request) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        success = True
        error = None
        verified_host = None
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            success, error, verified_host = self._verify_host(request)
        auth_data = {'verified_host': verified_host}
        return success, error, auth_data

    def _verify_host(self, request: Request) -> Tuple[bool, Optional[str], Optional[str]]:
        request_host = request.host
        request_hauth = request.headers.get('Hauth')
        shop_host = self.app_settings["shop"].get("host")
        client_settings = self.app_settings["shop"]["clients"]["cyberfoil"]
        hauth_dict = client_settings.get("hauth", {})
        shop_hauth = hauth_dict.get(request_host)
        self.log_info(f"Secure request from remote host {request_host}, proceeding with host verification.")
        if not shop_host:
            self.log_error("Missing shop host configuration, Host verification is disabled.")
            return True, None, None
        if not shop_hauth:
            return self._handle_missing_hauth(request, request_host, request_hauth)
        if request_hauth != shop_hauth:
            self.log_warning(f"Incorrect Hauth detected for host: {request_host}.")
            return False, f"Incorrect Hauth for URL `{request_host}`.", None
        return True, None, shop_host

    def _handle_missing_hauth(self, request: Request, request_host: str, request_hauth: str) -> Tuple[bool, Optional[str], Optional[str]]:
        basic_auth_success = request.basic_auth_success
        user_is_admin = request.user.has_admin_access() if request.user else False
        if basic_auth_success and user_is_admin:
            shop_settings = self.app_settings['shop']
            hauth_dict = shop_settings['clients']['cyberfoil'].get('hauth', {})
            hauth_dict[request_host] = request_hauth
            shop_settings['clients']['cyberfoil']['hauth'] = hauth_dict
            set_shop_settings(shop_settings)
            self.log_info(f"Successfully set Hauth value for host {request_host}.")
            return True, None, request_host
        self.log_warning(
            f"Hauth value not set for host {request_host}, Host verification is disabled. "
            f"Connect to the shop from Cyberfoil with an admin account to set it."
        )
        return True, None, None

    def _generate_shop_files(self, content_filter=None) -> list:
        """Generate files list with title ID in filename and structured metadata."""
        files = self.get_filtered_files(content_filter)

        conn = sqlite3.connect('/app/config/ownfoil.db')
        c = conn.cursor()
        c.execute(
            "SELECT f.id, a.app_id, a.app_version, a.app_type, t.title_id "
            "FROM files f "
            "JOIN app_files af ON f.id = af.file_id "
            "JOIN apps a ON af.app_id = a.id "
            "JOIN titles t ON a.title_id = t.id"
        )
        file_app_map = {}
        for fid, app_id, app_ver, app_type, title_id in c.fetchall():
            if fid not in file_app_map or app_type == 'BASE':
                file_app_map[fid] = {
                    'app_id': app_id,
                    'app_version': app_ver or '0',
                    'app_type': (app_type or 'base').lower(),
                    'title_id': title_id,
                }
        conn.close()

        try:
            with open('/app/data/titledb/titles.US.en.json') as f:
                tdb = json.load(f)
        except Exception:
            tdb = {}

        result = []
        for f in files:
            meta = file_app_map.get(f.id)
            if meta:
                app_id = meta['app_id']
                app_ver = meta['app_version']
                title_id = meta['title_id']
                name_base, ext = os.path.splitext(f.filename)
                new_name = f'{name_base} [{app_id}][v{app_ver}]{ext}'
                entry = {
                    'url': f'/api/get_game/{f.id}#{new_name}',
                    'size': f.size,
                    'title_id': title_id,
                    'app_id': app_id,
                    'app_version': app_ver,
                    'app_type': meta['app_type'],
                }
                tdb_entry = tdb.get(title_id) or tdb.get(app_id) or {}
                if tdb_entry.get('name'):
                    name = tdb_entry['name']
                    if meta['app_type'] == 'update':
                        name = f'{name} (Update) [v{app_ver}]'
                    elif meta['app_type'] == 'dlc':
                        name = f'{name} (DLC) [v{app_ver}]'
                    else:
                        name = f'{name} [v{app_ver}]'
                    entry['name'] = name
                if tdb_entry.get('iconUrl'):
                    entry['icon_url'] = tdb_entry['iconUrl']
            else:
                entry = {
                    'url': f'/api/get_game/{f.id}#{f.filename}',
                    'size': f.size,
                }
            result.append(entry)
        return result
