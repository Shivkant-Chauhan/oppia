# Copyright 2014 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Installation script for Oppia third-party libraries."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tarfile
import urllib
import zipfile

from core import utils
from scripts import build
from typing import Dict, Final, List, Literal, TypedDict, cast

from . import common

DEPENDENCIES_FILE_PATH: Final = os.path.join(os.getcwd(), 'dependencies.json')
TOOLS_DIR: Final = os.path.join('..', 'oppia_tools')
THIRD_PARTY_DIR: Final = os.path.join('.', 'third_party')
THIRD_PARTY_CSS_RELATIVE_FILEPATH = os.path.join('css', 'third_party.css')
THIRD_PARTY_GENERATED_DEV_DIR = os.path.join('third_party', 'generated', '')
THIRD_PARTY_JS_RELATIVE_FILEPATH = os.path.join('js', 'third_party.js')
THIRD_PARTY_STATIC_DIR: Final = os.path.join(THIRD_PARTY_DIR, 'static')

WEBFONTS_RELATIVE_DIRECTORY_PATH = os.path.join('webfonts', '')

# Place to download zip files for temporary storage.
TMP_UNZIP_PATH: Final = os.path.join('.', 'tmp_unzip.zip')


# Check that the current directory is correct.
common.require_cwd_to_be_oppia(allow_deploy_dir=True)

TARGET_DOWNLOAD_DIRS: Final = {
    'proto': THIRD_PARTY_DIR,
    'frontend': THIRD_PARTY_STATIC_DIR,
    'oppiaTools': TOOLS_DIR
}

_DOWNLOAD_FORMAT_ZIP: Final = 'zip'
_DOWNLOAD_FORMAT_TAR: Final = 'tar'
_DOWNLOAD_FORMAT_FILES: Final = 'files'

DownloadFormatType = Literal['zip', 'files', 'tar']


class DependencyBundleDict(TypedDict):
    """Dictionary that represents dependency bundle."""

    js: List[str]
    css: List[str]
    fontsPath: str


class DownloadFormatToDependenciesKeysDict(TypedDict):
    """TypeDict for download format to dependencies keys dict."""

    mandatory_keys: List[str]
    optional_key_pairs: List[List[str]]


DOWNLOAD_FORMATS_TO_DEPENDENCIES_KEYS: Dict[
    DownloadFormatType, DownloadFormatToDependenciesKeysDict
] = {
    'zip': {
        'mandatory_keys': ['version', 'url', 'downloadFormat'],
        'optional_key_pairs': [
            ['rootDir', 'rootDirPrefix'], ['targetDir', 'targetDirPrefix']]
    },
    'files': {
        'mandatory_keys': [
            'version', 'url', 'files',
            'targetDirPrefix', 'downloadFormat'],
        'optional_key_pairs': []
    },
    'tar': {
        'mandatory_keys': [
            'version', 'url', 'tarRootDirPrefix',
            'targetDirPrefix', 'downloadFormat'],
        'optional_key_pairs': []
    }
}


# Here we use total=False since some fields in this dict
# is optional/not required. There are possibilities that some fields
# can be present or not. In some cases, either one of the 2 fields
# should be present. However, we do have validation for this in code over
# here in test_dependencies_syntax() function.
class DependencyDict(TypedDict, total=False):
    """Dict representation of dependency."""

    version: str
    downloadFormat: DownloadFormatType
    url: str
    rootDirPrefix: str
    rootDir: str
    targetDirPrefix: str
    targetDir: str
    tarRootDirPrefix: str
    files: List[str]
    bundle: Dict[str, List[str]]


class DependenciesDict(TypedDict):
    """Dict representation of dependencies."""

    dependencies: Dict[str, Dict[str, DependencyDict]]


def download_files(
    source_url_root: str,
    target_dir: str,
    source_filenames: List[str]
) -> None:
    """Downloads a group of files and saves them to a given directory.

    Each file is downloaded only if it does not already exist.

    Args:
        source_url_root: str. The URL to prepend to all the filenames.
        target_dir: str. The directory to save the files to.
        source_filenames: list(str). Each filename is appended to the
            end of the source_url_root in order to give the URL from which to
            download the file. The downloaded file is then placed in target_dir,
            and retains the same filename.
    """
    assert isinstance(source_filenames, list), (
        'Expected list of filenames, got \'%s\'' % source_filenames)
    common.ensure_directory_exists(target_dir)
    for filename in source_filenames:
        if not os.path.exists(os.path.join(target_dir, filename)):
            print('Downloading file %s to %s ...' % (filename, target_dir))
            common.url_retrieve(
                '%s/%s' % (source_url_root, filename),
                os.path.join(target_dir, filename))

            print('Download of %s succeeded.' % filename)


def download_and_unzip_files(
    source_url: str,
    target_parent_dir: str,
    zip_root_name: str,
    target_root_name: str
) -> None:
    """Downloads a zip file, unzips it, and saves the result in a given dir.

    The download occurs only if the target directory that the zip file unzips
    to does not exist.

    NB: This function assumes that the root level of the zip file has exactly
    one folder.

    Args:
        source_url: str. The URL from which to download the zip file.
        target_parent_dir: str. The directory to save the contents of the zip
            file to.
        zip_root_name: str. The name of the top-level folder in the zip
            directory.
        target_root_name: str. The name that the top-level folder should be
            renamed to in the local directory.
    """
    if not os.path.exists(os.path.join(target_parent_dir, target_root_name)):
        print('Downloading and unzipping file %s to %s ...' % (
            zip_root_name, target_parent_dir))
        common.ensure_directory_exists(target_parent_dir)

        common.url_retrieve(source_url, TMP_UNZIP_PATH)

        try:
            with zipfile.ZipFile(TMP_UNZIP_PATH, 'r') as zfile:
                zfile.extractall(path=target_parent_dir)
            os.remove(TMP_UNZIP_PATH)
        except Exception:
            if os.path.exists(TMP_UNZIP_PATH):
                os.remove(TMP_UNZIP_PATH)

            # Some downloads (like jqueryui-themes) may require a user-agent.
            req = urllib.request.Request(source_url, None, {})
            req.add_header('User-agent', 'python')
            # This is needed to get a seekable filestream that can be used
            # by zipfile.ZipFile.
            file_stream = io.BytesIO(utils.url_open(req).read())
            with zipfile.ZipFile(file_stream, 'r') as zfile:
                zfile.extractall(path=target_parent_dir)

        # Rename the target directory.
        os.rename(
            os.path.join(target_parent_dir, zip_root_name),
            os.path.join(target_parent_dir, target_root_name))

        print('Download of %s succeeded.' % zip_root_name)


def download_and_untar_files(
    source_url: str,
    target_parent_dir: str,
    tar_root_name: str,
    target_root_name: str
) -> None:
    """Downloads a tar file, untars it, and saves the result in a given dir.

    The download occurs only if the target directory that the tar file untars
    to does not exist.

    NB: This function assumes that the root level of the tar file has exactly
    one folder.

    Args:
        source_url: str. The URL from which to download the tar file.
        target_parent_dir: str. The directory to save the contents of the tar
            file to.
        tar_root_name: str. The name of the top-level folder in the tar
            directory.
        target_root_name: str. The name that the top-level folder should be
            renamed to in the local directory.
    """
    if not os.path.exists(os.path.join(target_parent_dir, target_root_name)):
        print('Downloading and untarring file %s to %s ...' % (
            tar_root_name, target_parent_dir))
        common.ensure_directory_exists(target_parent_dir)

        common.url_retrieve(source_url, TMP_UNZIP_PATH)
        with contextlib.closing(tarfile.open(
            name=TMP_UNZIP_PATH, mode='r:gz')) as tfile:
            tfile.extractall(target_parent_dir)
        os.remove(TMP_UNZIP_PATH)

        # Rename the target directory.
        os.rename(
            os.path.join(target_parent_dir, tar_root_name),
            os.path.join(target_parent_dir, target_root_name))

        print('Download of %s succeeded.' % tar_root_name)


def get_file_contents(filepath: str, mode: utils.TextModeTypes = 'r') -> str:
    """Gets the contents of a file, given a relative filepath from oppia/."""
    with utils.open_file(filepath, mode) as f:
        return f.read()


def return_json(filepath: str) -> DependenciesDict:
    """Return json object when provided url

    Args:
        filepath: str. The path to the json file.

    Returns:
        *. A parsed json object. Actual conversion is different based on input
        to json.loads. More details can be found here:
            https://docs.python.org/3/library/json.html#encoders-and-decoders.
    """
    response = get_file_contents(filepath)
    # Here we use cast because we are narrowing down the type from to
    # DependenciesDict since we know the type of dependencies
    # as it is the content of the file dependencies.json.
    return cast(
        DependenciesDict,
        json.loads(response)
    )


def test_dependencies_syntax(
    dependency_type: DownloadFormatType,
    dependency_dict: DependencyDict
) -> None:
    """This checks syntax of the dependencies.json dependencies.
    Display warning message when there is an error and terminate the program.

    Args:
        dependency_type: DownloadFormatType. Dependency download format.
        dependency_dict: dict. A dependencies.json dependency dict.
    """
    keys = list(dependency_dict.keys())
    mandatory_keys = DOWNLOAD_FORMATS_TO_DEPENDENCIES_KEYS[
        dependency_type]['mandatory_keys']
    # Optional keys requires exactly one member of the pair
    # to be available as a key in the dependency_dict.
    optional_key_pairs = DOWNLOAD_FORMATS_TO_DEPENDENCIES_KEYS[
        dependency_type]['optional_key_pairs']
    for key in mandatory_keys:
        if key not in keys:
            print('------------------------------------------')
            print('There is syntax error in this dependency')
            print(dependency_dict)
            print('This key is missing or misspelled: "%s".' % key)
            print('Exiting')
            sys.exit(1)
    if optional_key_pairs:
        for optional_keys in optional_key_pairs:
            optional_keys_in_dict = [
                key for key in optional_keys if key in keys]
            if len(optional_keys_in_dict) != 1:
                print('------------------------------------------')
                print('There is syntax error in this dependency')
                print(dependency_dict)
                print(
                    'Only one of these keys pair must be used: "%s".'
                    % ', '.join(optional_keys))
                print('Exiting')
                sys.exit(1)

    # Checks the validity of the URL corresponding to the file format.
    dependency_url = dependency_dict['url']
    if '#' in dependency_url:
        dependency_url = dependency_url.rpartition('#')[0]
    is_zip_file_format = dependency_type == _DOWNLOAD_FORMAT_ZIP
    is_tar_file_format = dependency_type == _DOWNLOAD_FORMAT_TAR
    if (dependency_url.endswith('.zip') and not is_zip_file_format or
            is_zip_file_format and not dependency_url.endswith('.zip') or
            dependency_url.endswith('.tar.gz') and not is_tar_file_format or
            is_tar_file_format and not dependency_url.endswith('.tar.gz')):
        print('------------------------------------------')
        print('There is syntax error in this dependency')
        print(dependency_dict)
        print('This url %s is invalid for %s file format.' % (
            dependency_url, dependency_type))
        print('Exiting.')
        sys.exit(1)


def validate_dependencies(filepath: str) -> None:
    """This validates syntax of the dependencies.json

    Args:
        filepath: str. The path to the json file.

    Raises:
        Exception. The 'downloadFormat' not specified.
    """
    dependencies_data = return_json(filepath)
    dependencies = dependencies_data['dependencies']
    for _, dependency in dependencies.items():
        for _, dependency_contents in dependency.items():
            if 'downloadFormat' not in dependency_contents:
                raise Exception(
                    'downloadFormat not specified in %s' %
                    dependency_contents)
            download_format = dependency_contents['downloadFormat']
            test_dependencies_syntax(download_format, dependency_contents)


def download_all_dependencies(filepath: str) -> None:
    """This download all files to the required folders.

    Args:
        filepath: str. The path to the json file.
    """
    validate_dependencies(filepath)
    dependencies_data = return_json(filepath)
    dependencies = dependencies_data['dependencies']
    for data, dependency in dependencies.items():
        for _, dependency_contents in dependency.items():
            dependency_rev = dependency_contents['version']
            dependency_url = dependency_contents['url']
            download_format = dependency_contents['downloadFormat']
            if download_format == _DOWNLOAD_FORMAT_FILES:
                dependency_files = dependency_contents['files']
                target_dirname = (
                    dependency_contents['targetDirPrefix'] + dependency_rev)
                dependency_dst = os.path.join(
                    TARGET_DOWNLOAD_DIRS[data], target_dirname)
                download_files(dependency_url, dependency_dst, dependency_files)

            elif download_format == _DOWNLOAD_FORMAT_ZIP:
                if 'rootDir' in dependency_contents:
                    dependency_zip_root_name = dependency_contents['rootDir']
                else:
                    dependency_zip_root_name = (
                        dependency_contents['rootDirPrefix'] + dependency_rev)

                if 'targetDir' in dependency_contents:
                    dependency_target_root_name = (
                        dependency_contents['targetDir'])
                else:
                    dependency_target_root_name = (
                        dependency_contents['targetDirPrefix'] + dependency_rev)
                download_and_unzip_files(
                    dependency_url, TARGET_DOWNLOAD_DIRS[data],
                    dependency_zip_root_name, dependency_target_root_name)

            elif download_format == _DOWNLOAD_FORMAT_TAR:
                dependency_tar_root_name = (
                    dependency_contents['tarRootDirPrefix'] + dependency_rev)

                dependency_target_root_name = (
                    dependency_contents['targetDirPrefix'] + dependency_rev)
                download_and_untar_files(
                    dependency_url, TARGET_DOWNLOAD_DIRS[data],
                    dependency_tar_root_name, dependency_target_root_name)
 
def build_third_party_libs(third_party_directory_path: str) -> None:
    """Joins all third party css files into single css file and js files into
    single js file. Copies both files and all fonts into third party folder.
    """

    print('Building third party libs at %s' % third_party_directory_path)

    third_party_js_filepath = os.path.join(
        third_party_directory_path, THIRD_PARTY_JS_RELATIVE_FILEPATH)
    third_party_css_filepath = os.path.join(
        third_party_directory_path, THIRD_PARTY_CSS_RELATIVE_FILEPATH)
    webfonts_dir = os.path.join(
        third_party_directory_path, WEBFONTS_RELATIVE_DIRECTORY_PATH)

    dependency_filepaths = build.get_dependencies_filepaths()
    build.ensure_directory_exists(third_party_js_filepath)
    with utils.open_file(
        third_party_js_filepath, 'w+') as third_party_js_file:
        build._join_files(dependency_filepaths['js'], third_party_js_file)

    build.ensure_directory_exists(third_party_css_filepath)
    with utils.open_file(
        third_party_css_filepath, 'w+') as third_party_css_file:
        build._join_files(dependency_filepaths['css'], third_party_css_file)

    build.ensure_directory_exists(webfonts_dir)
    build._execute_tasks(
        build._generate_copy_tasks_for_fonts(
            dependency_filepaths['fonts'], webfonts_dir))


def main() -> None:
    """Installs all the packages from the dependencies.json file."""

    download_all_dependencies(DEPENDENCIES_FILE_PATH)
    build_third_party_libs(THIRD_PARTY_GENERATED_DEV_DIR)


# The 'no coverage' pragma is used as this line is un-testable. This is because
# it will only be called when install_third_party.py is used as a script.
if __name__ == '__main__': # pragma: no cover
    main()
