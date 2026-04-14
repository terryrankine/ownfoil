from constants import *
from utils import *
import time, os
from types import SimpleNamespace
import logging

# Retrieve main logger
logger = logging.getLogger('main')


class _NoOpEventHandler:
    """Stub so library.py references to watcher.event_handler don't crash."""
    def __init__(self):
        self.ignored_events_lock = __import__('threading').Lock()
        self.ignored_events_tuples = set()


class Watcher:
    """File watcher stub — polling disabled to avoid CPU waste on NFS mounts.
    Library changes are detected via the scheduled scan instead."""

    def __init__(self, callback):
        self.directories = set()
        self.callback = callback
        self.scheduler_map = {}
        self.event_handler = _NoOpEventHandler()

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

    def remove_directory(self, directory):
        if directory in self.directories:
            self.directories.remove(directory)
            logger.info(f'Removed {directory}.')
            return True
        return False

