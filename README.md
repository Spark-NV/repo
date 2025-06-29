# SparkNV Kodi Repository

This is a personal Kodi repository containing customized addons for embedded use in a Kodi fork.

## Repository Structure

```
sparknv.repo/
├── repo/
│   ├── addons.xml              # Repository index file
│   ├── addons.xml.md5          # MD5 checksum for addons.xml
│   ├── zips/                   # Addon zip files
│   │   ├── plugin.video.umbrella.sparknv-6.7.46.zip
│   │   ├── service.subtitles.a4ksubtitles.sparknv-3.21.1.zip
│   │   └── skin.aeon.nox.sparknv-8.1.0.zip
│   └── sparknv.repo/
│       ├── addon.xml           # Repository addon definition
│       ├── icon.png
│       └── fanart.jpg
├── Matrix/                     # Source addons
│   ├── plugin.video.umbrella.sparknv/
│   ├── service.subtitles.a4ksubtitles.sparknv/
│   └── skin.aeon.nox.sparknv/
└── generate_repo.py            # Script to regenerate repository
```

## Addons Included

1. **plugin.video.umbrella.sparknv** (v6.7.46) - Video streaming addon
2. **service.subtitles.a4ksubtitles.sparknv** (v3.21.1) - Multi-source subtitle service
3. **skin.aeon.nox.sparknv** (v8.1.0) - Customized Aeon Nox skin

## Usage

This repository is designed for embedded use in a Kodi fork and is not intended for end-user installation.

### Regenerating the Repository

To update the repository after making changes to the addons:

```bash
python3 generate_repo.py
```

This will:
- Create zip files for all addons in the `Matrix/` directory
- Generate the `addons.xml` file
- Generate the `addons.xml.md5` checksum file

### GitLab Hosting

The repository is configured to be hosted on GitLab with the following URL structure:
- Repository info: `https://gitlab.com/spark-nv/sparknv.repo/-/raw/main/repo/addons.xml`
- Checksum: `https://gitlab.com/spark-nv/sparknv.repo/-/raw/main/repo/addons.xml.md5`
- Addon downloads: `https://gitlab.com/spark-nv/sparknv.repo/-/raw/main/repo/zips/`

## Notes

- The repository addon itself (`sparknv.repo`) is not included in the `addons.xml` as it's not meant to be installable
- All addons have been customized with the `sparknv` provider name
- The repository is optimized for Kodi Matrix (v19+) compatibility 