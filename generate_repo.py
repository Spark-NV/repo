#!/usr/bin/env python3
import os
import hashlib
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

def create_addon_zip(addon_path, zip_path):
    """Create a zip file for an addon"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(addon_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, addon_path)
                zipf.write(file_path, arcname)
                

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
    xml_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml_content += '<addons>\n'
    
    for addon in addons_info:
        if addon is None:
            continue
            
        addon_xml_path = os.path.join(addon['path'], 'addon.xml')
        with open(addon_xml_path, 'r', encoding='utf-8') as f:
            addon_xml_content = f.read()
        
        addon_xml_content = addon_xml_content.replace('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '')
        addon_xml_content = addon_xml_content.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        addon_xml_content = addon_xml_content.strip()
        
        xml_content += addon_xml_content + '\n'
    
    xml_content += '</addons>'
    return xml_content

def main():
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
                    create_addon_zip(addon_path, zip_path)
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

if __name__ == '__main__':
    main() 
