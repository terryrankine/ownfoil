from constants import *
from utils import *
import os
import logging

# Retrieve main logger
logger = logging.getLogger('main')


class Watcher:
    """File watcher stub — polling disabled to avoid CPU waste on NFS mounts.
    Library changes are detected via the scheduled scan instead.
    Settings file changes are detected via mtime check on access."""

    def __init__(self, callback):
        self.directories = set()
        self.callback = callback
        self.scheduler_map = {}
        self.event_handler = type('Handler', (), {})()

    def run(self):
        logger.info('File watcher disabled (polling observer removed).')

    def stop(self):
        pass

    def add_directory(self, directory):
        if directory not in self.directories:
            if not os.path.exists(directory):
                logger.warning(f'Directory {directory} does not exist.')
                return False
            logger.info(f'Registered directory {directory} (watcher disabled, scan-only mode).')
            self.directories.add(directory)
            return True
        return False

    def add_file_callback(self, filepath, callback):
        """No-op — settings reload handled by mtime-cached get_settings()."""
        logger.info(f'File callback for {filepath} registered but watcher is disabled.')

    def remove_directory(self, directory):
        if directory in self.directories:
            self.directories.remove(directory)
            logger.info(f'Removed {directory}.')
            return True
        return False
