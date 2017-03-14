#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
import io
import csv
import os
import platform
import subprocess
import json
import shutil
import sys
import tempfile
import getpass

import sh
import humanfriendly
import requests
from path import Path as P
from django.db.models import QuerySet
from django.conf import settings

from hamed.exports.pdf.social_survey import gen_social_survey_pdf
from hamed.exports.pdf.indigence_certificate import \
    gen_indigence_certificate_pdf
from hamed.exports.pdf.residence_certificate import \
    gen_residence_certificate_pdf
from hamed.models.settings import Settings
from hamed.ona import (download_media, download_xlsx_export,
                       download_json_export, XLSX_MIME,
                       add_role_to_form, DATAENTRY_ROLE, READONLY_ROLE)
from hamed.exceptions import MultipleUSBDisksPlugged, NoUSBDiskPlugged

logger = logging.getLogger(__name__)

PERSONAL_FILES = "Dossiers"
PRINTS = "Impressions"
SURVEYS = "Enquetes"
INDIGENCES = "Certificats indigence"
RESIDENCES = "Certificats residence"
MIMES = {
    'json': "application/json",
    'xlsx': XLSX_MIME,
}


def gen_targets_csv(targets):
    csvfile = io.StringIO()
    fieldnames = ['ident', 'nom', 'age', 'sexe']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for target in targets:
        writer.writerow({'ident': target.identifier,
                         'nom': target.name(),
                         'age': target.age,
                         'sexe': target.verbose_sex})
    # write complete, reset pointer
    csvfile.seek(0)
    return csvfile


def check_targets_documents_folder(collect):

    # collect-root
    croot = collect.get_documents_path()
    P(croot).makedirs_p()

    # static folders for collect
    for folder_name in (PRINTS, PERSONAL_FILES):
        P(os.path.join(croot, folder_name)).makedirs_p()


def get_document_fname(kind, target):
    templates = {
        'survey': "{id}_enquete-sociale.pdf",
        'indigence': "{id}_certificat-indigence-vierge.pdf",
        'residence': "{id}_certificat-residence-vierge.pdf",
    }
    return templates.get(kind).format(id=target.identifier)


def get_export_fname(kind, collect):
    templates = {
        'xlsx': "{ona_id}.xlsx",
        'json': "{ona_id}.json",
    }
    return templates.get(kind).format(ona_id=collect.ona_form_id())


def gen_targets_documents(targets):
    from hamed.models.collects import Collect
    # ensure we have destinations folder
    if isinstance(targets, QuerySet):
        collects = set([Collect.get_or_none(t['collect'])
                        for t in targets.values('collect')])
    else:
        collects = set([t.collect for t in targets])

    for collect in collects:
        check_targets_documents_folder(collect)
        prints_folder = os.path.join(collect.get_documents_path(), PRINTS)
        P(prints_folder).makedirs_p()

        for prints_subfolder in (SURVEYS, INDIGENCES, RESIDENCES):
            P(os.path.join(prints_folder, prints_subfolder)).makedirs_p()

        survey_links_folder = os.path.join(prints_folder, SURVEYS)
        P(survey_links_folder).makedirs_p()

    for target in targets:

        # social survey
        P(target.get_folder_path()).makedirs_p()  # ensure personnal folder OK
        survey = gen_social_survey_pdf(target)
        survey_fname = get_document_fname('survey', target)
        survey_fpath = os.path.join(
            target.get_folder_path(),
            survey_fname)
        with open(survey_fpath, 'wb') as f:
            f.write(survey.read())

        # indigence certificate and residence certificate goes to print folder
        for kind, subfolder, gen_func in (
                ('indigence', INDIGENCES, gen_indigence_certificate_pdf),
                ('residence', RESIDENCES, gen_residence_certificate_pdf)):
            document = gen_func(target)
            document_fpath = os.path.join(
                prints_folder,
                subfolder,
                get_document_fname(kind, target))
            with open(document_fpath, 'wb') as f:
                f.write(document.read())

        # survey is also copied (not synlinked --printer issue--) in prints
        survey_link_fpath = os.path.join(survey_links_folder, survey_fname)
        P(survey_fpath).copy2(survey_link_fpath)


def remove_targets_documents(targets):
    from hamed.models.collects import Collect
    if isinstance(targets, QuerySet):
        collects = set([Collect.get_or_none(t['collect'])
                        for t in targets.values('collect')])
    else:
        collects = set([t.collect for t in targets])

    for target in targets:

        # remove social survey in personnal folder
        survey_fname = get_document_fname('survey', target)
        survey_fpath = os.path.join(
            target.get_folder_path(),
            survey_fname)
        P(survey_fpath).remove_p()

        # prints folder contains certificates and a copy of survey
        prints_folder = os.path.join(
            target.collect.get_documents_path(), PRINTS)
        for kind, subfolder in (
                ('indigence', INDIGENCES),
                ('residence', RESIDENCES),
                ('survey', SURVEYS)):
            document_fpath = os.path.join(
                prints_folder,
                subfolder,
                get_document_fname(kind, target))
            P(document_fpath).remove_p()
        # attempt to remove empty personnal folder
        P(target.get_folder_path()).removedirs_p()

    for collect in collects:
        cleanup_empty_folders(collect)


def cleanup_empty_folders(collect):

    # remove target's folders
    for target in collect.targets.all():
        if P(target.get_folder_path()).exists():
            P(target.get_folder_path()).removedirs_p()

    # try to remove folders if empty
    empty_folders = [
        os.path.join(collect.get_documents_path(), PRINTS, subfolder)
        for subfolder in (INDIGENCES, RESIDENCES, SURVEYS)
    ]
    empty_folders += [
        os.path.join(collect.get_documents_path(), PRINTS),
        os.path.join(collect.get_documents_path(), PERSONAL_FILES),
        collect.get_documents_path()
    ]
    for folder in empty_folders:
        if P(folder).exists():
            P(folder).removedirs_p()


def export_collect_medias(collect):
    # ensure folder is ready
    check_targets_documents_folder(collect)

    for target in collect.targets.all():
        export_target_medias(target)


def export_target_medias(target):
    # ensure personnal folder OK
    P(target.get_folder_path()).makedirs_p()

    def export_media(attachment):
        try:
            output_fpath = os.path.join(target.get_folder_path(),
                                        attachment['export_fname'])
            with open(output_fpath, 'wb') as f:
                f.write(download_media(attachment['download_url']).read())
        except Exception as exp:
            logger.exception(exp)
            raise

    for attachment in target.list_attachments():
        export_media(attachment)


def remove_collect_medias(collect):
    # medias are tied to targets
    for target in collect.targets.all():
        # delete each media
        for attachment in target.list_attachments():
            fpath = os.path.join(target.get_folder_path(),
                                 attachment['export_fname'])
            P(fpath).remove_p()

    cleanup_empty_folders(collect)


def export_collect_data(collect):
    check_targets_documents_folder(collect)

    export_collect_data_as_xlsx(collect)
    export_collect_data_as_json(collect)


def export_collect_data_as_onajson(collect):
    fpath = os.path.join(collect.get_documents_path(),
                         get_export_fname('json', collect))
    with open(fpath, 'wb') as f:
        f.write(download_json_export(collect))


def export_collect_data_as_json(collect):
    fpath = os.path.join(collect.get_documents_path(),
                         get_export_fname('json', collect))
    with open(fpath, 'w', encoding="UTF-8") as f:
        json.dump(collect.export_data(), f, indent=4)


def export_collect_data_as_xlsx(collect):
    fpath = os.path.join(collect.get_documents_path(),
                         get_export_fname('xlsx', collect))
    with open(fpath, 'wb') as f:
        f.write(download_xlsx_export(collect))


def remove_exported_collect_data(collect):
    for format in ('json', 'xlsx'):
        fpath = os.path.join(collect.get_documents_path(),
                             get_export_fname(format, collect))
        P(fpath).remove_p()

    cleanup_empty_folders(collect)


def get_attachment(dataset, question_value, main_key='_attachments'):
    ''' retrieve a specific attachment dict for a question value '''
    if question_value is not None:
        for attachment in dataset.get(main_key, []):
            if attachment.get('filename', "").endswith(question_value):
                return attachment
    return None


def open_finder_at(abs_path):
    os.environ['DISPLAY'] = ':0'
    if platform.system() == "Windows":
        os.startfile(abs_path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", abs_path])
    else:
        # TODO: fix this static sh*t
        # subprocess.Popen(["xdg-open", abs_path])
        subprocess.Popen(["sudo", "-H", "-u", "sldses", "xdg-open", abs_path])


def share_form(form_pk):
    return add_role_to_form(form_pk,
                            usernames=Settings.dataentry_username(),
                            role=DATAENTRY_ROLE)


def unshare_form(form_pk):
    return add_role_to_form(form_pk,
                            usernames=Settings.dataentry_username(),
                            role=READONLY_ROLE)


def upload_export_data(collect):
    url = "/".join([Settings.upload_server(), "upload"])
    req = requests.post(url=url, json=collect.export_data())
    assert req.status_code == 200
    assert req.json()['status'] == 'success'
    collect.mark_uploaded(req.json())
    return req.json()


def list_files(folder):
    all_files = []
    for root, folders, filenames in os.walk(folder):
        for filename in filter(lambda x: not x.startswith('.'), filenames):
            full_path = os.path.join(root, filename)
            rel_path = P(full_path).relpath(folder)
            all_files.append(rel_path)
    return all_files


def get_us_env():
    env = os.environ.copy()
    for k, v in env.items():
        if v == 'fr_FR.UTF-8':
            env[k] = 'en_US.UTF-8'
    return env


def parse_parted_info(device_path):
    if not sys.platform.startswith('linux'):
        if settings.DEBUG:
            return ('/dev/sdd', '32.0GB', 32000000000, 'msdos', "Virtual USB")
        else:
            raise NotImplemented("USB exports is Linux-only")

    pcmd = sh.sudo.parted("-s", "-m", device_path, "print",
                          _env=get_us_env())
    assert pcmd.exit_code == 0
    line = str(pcmd).splitlines()[1]
    path, size, driver, sector, block, mbr, name, _ = line.split(":")
    sizeInBytes = humanfriendly.parse_size(size)
    return (path, size, sizeInBytes, mbr, name)


def find_export_disk():
    if not sys.platform.startswith('linux'):
        if settings.DEBUG:
            return '/dev/sdd'
        else:
            raise NotImplemented("USB exports is Linux-only")

    max_size = 40 * 1e+9

    # list devices (usb only)
    disks = []
    basedir = '/dev/disk/by-path/'
    if P(basedir).exists():
        for fname in os.listdir(basedir):
            # USB-only, whole disks only
            if 'usb' in fname and 'part' not in fname:
                path = os.path.join(basedir, fname)
                link = os.readlink(path)
                disks.append(
                    os.path.normpath(
                        os.path.join(os.path.dirname(path), link)))

    # check size and exclude anything > 40GB
    for disk in set(disks):
        # device = parted.getDevice(disk)
        device_info = parse_parted_info(disk)
        sizeInBytes = device_info[2]
        if sizeInBytes > max_size:
            disks.remove(disk)

    # assert only one remaining
    try:
        assert len(disks) == 1
    except AssertionError:
        if len(disks) == 0:
            raise NoUSBDiskPlugged("Il n'y a aucun disque USB branché.")
        else:
            raise MultipleUSBDisksPlugged(
                "Il y a {nb} disques USB branchés.".format(nb=len(disks)))

    # return it
    return disks[0]


def unmount_device(device_path):
    if not sys.platform.startswith('linux'):
        if settings.DEBUG:
            logger.debug("(virtually) unmounting {}".format(device_path))
            return
        else:
            raise NotImplemented("USB exports is Linux-only")

    dev_root, dev_name = device_path.rsplit("/", 1)
    partitions = [os.path.join(dev_root, fname)
                  for fname in os.listdir(dev_root)
                  if fname.startswith(dev_name) and fname != dev_name]

    with sh.sudo:
        for device_partition in partitions:
            logger.debug("unmounting {}".format(device_partition))
            try:
                sh.umount(device_partition)
            except sh.ErrorReturnCode_32:
                pass


def prepare_disk(device_path):
    partition_path = "{dev}1".format(dev=device_path)
    mount_point = tempfile.mkdtemp(suffix=partition_path.rsplit("/", 1)[-1])

    if not sys.platform.startswith('linux'):
        if settings.DEBUG:
            logger.debug("(virtually) formatting disk {}".format(device_path))
            logger.debug("(virtual) mount point: {}".format(mount_point))
            return mount_point
        else:
            raise NotImplemented("USB exports is Linux-only")

    logger.debug("unmounting {}".format(device_path))
    unmount_device(device_path)

    us_environ = get_us_env()
    uid = os.getuid()
    gid = os.getgid()

    with sh.sudo:
        logger.debug("resetting partition table for {}".format(device_path))
        sh.parted("-s", "-a", "optimal",
                  device_path,
                  "--",
                  "mklabel",  "msdos",
                  "mkpart", "primary", "fat32", "64s", "-1s",
                  _env=us_environ)

        logger.debug("formatting {}".format(partition_path))
        sh.mkfs("-t", "vfat", "-F", "32", "-n", "SLDSES", partition_path,
                _env=us_environ)

        logger.debug("mounting {} to {}".format(partition_path, mount_point))
        sh.mount("-o", "umask=0,dmask=000,fmask=111,uid={uid},gid={gid},utf8"
                       .format(uid=uid, gid=gid),
                 partition_path, mount_point)

    return mount_point
