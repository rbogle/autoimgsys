# -*- coding: utf-8 -*-
from flask import redirect, abort, send_file
from flask.ext.admin._compat import urljoin
from flask.ext.admin.contrib.fileadmin import FileAdmin
from flask.ext.admin.base import expose
import shutil
import os.path as op
import logging


# subclass FileAdmin and overload download to add the
# option to zip a directory up and download it. 
# is it better to redirect to the parent or send_file the zip.
# both wait till make_archive finishes, but the client may timeout
# TODO should it be lauched as thread with callback?
class AisFileAdmin(FileAdmin):
    
    @expose('/download/<path:path>')
    def download(self, path=None):
        """
            Download view method.

            :param path:
                File path.
        """
        if not self.can_download:
            abort(404)
        logger = logging.getLogger(self.__class__.__name__)  
        base_path, directory, path = self._normalize_path(path)

        # backward compatibility with base_url
        base_url = self.get_base_url()
        if base_url:
            base_url = urljoin(self.get_url('.index'), base_url)
            return redirect(urljoin(base_url, path))
        if op.isdir(directory):
            logger.debug("Directory download asked for: %s" %path)
            shutil.make_archive(directory,'zip',directory)
            return redirect(self._get_dir_url('.index', op.dirname(path)))
        return send_file(directory)
