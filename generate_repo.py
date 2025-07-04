#!/usr/bin/env python3

import os
import hashlib
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess

def clear_directory(directory):
    """Delete all contents of a directory, but not the directory itself."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

def remove_pycache_dirs(root_dir='.'):
    """Recursively remove all __pycache__ directories."""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '__pycache__' in dirnames:
            pycache_path = os.path.join(dirpath, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"Removed: {pycache_path}")

def create_addon_zip(addon_path, zip_path, addon_id):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(addon_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, addon_path)
                zip_entry = os.path.join(addon_id, rel_path)
                z.write(file_path, zip_entry)

def get_addon_info(addon_path):
    """Extract addon information from addon.xml"""
    addon_xml = os.path.join(addon_path, 'addon.xml')
    if not os.path.exists(addon_xml):
        return None
    tree = ET.parse(addon_xml)
    root = tree.getroot()
    addon_id = root.get('id')
    name = root.get('name')
    version = root.get('version')
    provider = root.get('provider-name')
    return {
        'id': addon_id,
        'name': name,
        'version': version,
        'provider': provider,
        'path': addon_path
    }

def generate_addons_xml(addons_info):
    """Generate addons.xml content"""
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
    for addon in addons_info:
        if addon is None:
            continue
        addon_xml_path = os.path.join(addon['path'], 'addon.xml')
        with open(addon_xml_path, 'r', encoding='utf-8') as f:
            addon_xml_content = f.read()
            addon_xml_content = addon_xml_content.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            addon_xml_content = addon_xml_content.replace('<addons>', '').replace('</addons>', '')
            addon_xml_content = addon_xml_content.strip()
            xml_content += addon_xml_content + '\n'
    xml_content += '</addons>\n'
    return xml_content

def git_commit_and_push():
    """Add, commit, and push changes to the main branch."""
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", "update"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Git add, commit, and push completed.")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")

def main():
    # Remove __pycache__ directories before proceeding
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(script_dir, 'repo')

    remove_pycache_dirs('.')
    clear_directory(repo_dir)

    zips_dir = 'repo/zips'
    os.makedirs(zips_dir, exist_ok=True)
    source_dir = 'Omega'
    addons_info = []

    if os.path.exists(source_dir):
        for addon_dir in os.listdir(source_dir):
            addon_path = os.path.join(source_dir, addon_dir)
            if os.path.isdir(addon_path):
                addon_info = get_addon_info(addon_path)
                if addon_info:
                    addons_info.append(addon_info)
                    zip_subdir = os.path.join(zips_dir, addon_info['id'])
                    os.makedirs(zip_subdir, exist_ok=True)
                    zip_filename = f"{addon_info['id']}-{addon_info['version']}.zip"
                    zip_path = os.path.join(zip_subdir, zip_filename)
                    create_addon_zip(addon_path, zip_path, addon_info['id'])
                    print(f"Created zip: {zip_path}")
                    for extra_file in ['icon.png', 'fanart.jpg', 'changelog.txt']:
                        src_file = os.path.join(addon_path, extra_file)
                        if os.path.exists(src_file):
                            shutil.copy2(src_file, zip_subdir)
                            print(f"Copied {extra_file} to {zip_subdir}")

    addons_xml_content = generate_addons_xml(addons_info)
    addons_xml_path = 'repo/addons.xml'
    with open(addons_xml_path, 'w', encoding='utf-8') as f:
        f.write(addons_xml_content)
    print(f"Generated: {addons_xml_path}")

    md5_hash = hashlib.md5(addons_xml_content.encode('utf-8')).hexdigest()
    md5_path = 'repo/addons.xml.md5'
    with open(md5_path, 'w') as f:
        f.write(md5_hash)
    print(f"Generated: {md5_path}")
    print(f"MD5: {md5_hash}")

    print(f"\nRepository generated successfully!")
    print(f"Addons included: {len(addons_info)}")

    # Perform Git operations after generation
    git_commit_and_push()

if __name__ == '__main__':
    main()

